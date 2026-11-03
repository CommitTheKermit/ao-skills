#!/usr/bin/env python3
"""FIFO local mobile execution queue. One heavy job per host/user."""
# usage-stats: harness mobile-validation-queue
import argparse
import fcntl
import json
import os
from pathlib import Path
import signal
import sqlite3
import subprocess
import sys
import time
import uuid


def record_usage():
    if os.environ.get('AGENT_COORDINATION_DIR'):
        return
    recorder = Path.home() / '.agents/skills/usage-stats/scripts/usage_stats.py'
    if recorder.exists():
        subprocess.run([sys.executable, str(recorder), 'record', 'harness', 'mobile-validation-queue'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)


def root_dir():
    root = Path(os.environ.get('AGENT_COORDINATION_DIR', '~/.local/state/agent-coordination')).expanduser()
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    return root


def connect():
    db = sqlite3.connect(root_dir() / 'mobile.sqlite3', timeout=30, isolation_level=None)
    db.row_factory = sqlite3.Row
    db.execute('CREATE TABLE IF NOT EXISTS jobs (seq INTEGER PRIMARY KEY AUTOINCREMENT, id TEXT UNIQUE, owner TEXT, label TEXT, state TEXT, pid INTEGER, birth TEXT, pgid INTEGER, exit_code INTEGER)')
    return db


def process_birth(pid):
    result = subprocess.run(['ps', '-p', str(pid), '-o', 'lstart='], capture_output=True, text=True)
    return result.stdout.strip()


def group_alive(pgid):
    if not pgid:
        return False
    # macOS may return EPERM for a group whose last member just exited.
    result = subprocess.run(['ps', '-axo', 'pgid=,stat='], capture_output=True, text=True, check=True)
    return any(int(parts[0]) == pgid and not parts[1].startswith('Z')
               for line in result.stdout.splitlines() if len(parts := line.split()) == 2)


def active_context(db):
    token = os.environ.get('MOBILE_VALIDATION_JOB')
    if not token:
        return False
    row = db.execute("SELECT * FROM jobs WHERE id=? AND state='running'", (token,)).fetchone()
    if not row or process_birth(row['pid']) != row['birth']:
        raise ValueError('유효하지 않은 상위 대기열 작업입니다.')
    pid = os.getpid()
    while pid > 1:
        if pid == row['pid']:
            return True
        result = subprocess.run(['ps', '-p', str(pid), '-o', 'ppid='], capture_output=True, text=True)
        pid = int(result.stdout.strip() or '0')
    raise ValueError('다른 프로세스의 대기열 토큰은 재사용할 수 없습니다.')


def stop_child(child):
    try:
        os.killpg(child.pid, signal.SIGTERM)
    except ProcessLookupError:
        pass
    deadline = time.monotonic() + 5
    while group_alive(child.pid) and time.monotonic() < deadline:
        child.poll()
        time.sleep(.1)
    if group_alive(child.pid):
        try:
            os.killpg(child.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    child.wait()


def run_job(db, args):
    command = args.command
    if command[:1] == ['--']:
        command = command[1:]
    if not command:
        raise ValueError('실행 명령이 필요합니다.')
    # Nested wrappers stay inside the parent's slot; never enqueue behind themselves.
    if active_context(db):
        return subprocess.call(command)
    owner = args.owner or os.environ.get('AGENT_SESSION_ID') or os.environ.get('CODEX_THREAD_ID') or os.environ.get('CODEX_SESSION_ID')
    if not owner:
        raise ValueError('--owner 또는 AGENT_SESSION_ID가 필요합니다.')
    job = uuid.uuid4().hex
    birth = process_birth(os.getpid())
    db.execute("INSERT INTO jobs(id,owner,label,state,pid,birth) VALUES (?,?,?,'waiting',?,?)", (job, owner, args.label, os.getpid(), birth))
    print(json.dumps({'job': job, 'state': 'waiting'}), file=sys.stderr, flush=True)
    cancelled = False
    def request_stop(signum, frame):
        nonlocal cancelled
        cancelled = True
    for sig in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP):
        signal.signal(sig, request_stop)
    child = None
    acquired = False
    with (root_dir() / 'mobile.lock').open('a') as lock:
        try:
            while not acquired:
                db.execute('BEGIN IMMEDIATE')
                try:
                    for row in db.execute("SELECT * FROM jobs WHERE state='waiting'").fetchall():
                        if process_birth(row['pid']) != row['birth']:
                            db.execute("UPDATE jobs SET state='abandoned' WHERE id=?", (row['id'],))
                    state = db.execute('SELECT state FROM jobs WHERE id=?', (job,)).fetchone()[0]
                    if cancelled or state == 'cancelled':
                        db.execute("UPDATE jobs SET state='cancelled' WHERE id=?", (job,))
                        return 130
                    first = db.execute("SELECT id FROM jobs WHERE state IN ('waiting','running','cancelling','blocked') ORDER BY seq LIMIT 1").fetchone()
                    if first and first[0] == job:
                        try:
                            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                            acquired = True
                            db.execute("UPDATE jobs SET state='running' WHERE id=?", (job,))
                        except BlockingIOError:
                            pass
                finally:
                    db.commit()
                if not acquired:
                    time.sleep(.25)
            env = dict(os.environ, MOBILE_VALIDATION_JOB=job)
            # The child also holds the lock if this supervisor is killed.
            child = subprocess.Popen(command, env=env, start_new_session=True, pass_fds=(lock.fileno(),))
            db.execute('UPDATE jobs SET pgid=? WHERE id=?', (child.pid, job))
            print(json.dumps({'job': job, 'state': 'running'}), file=sys.stderr, flush=True)
            while child.poll() is None:
                state = db.execute('SELECT state FROM jobs WHERE id=?', (job,)).fetchone()[0]
                if cancelled or state == 'cancelling':
                    cancelled = True
                    stop_child(child)
                    break
                time.sleep(.2)
            result = 130 if cancelled else child.returncode
            # Detached/background descendants must not silently overlap the next job.
            state = 'blocked' if group_alive(child.pid) else ('cancelled' if cancelled else 'finished')
            db.execute('UPDATE jobs SET state=?, exit_code=? WHERE id=?', (state, result, job))
            return result if state != 'blocked' else 2
        except BaseException:
            if child is not None and child.poll() is None:
                stop_child(child)
            db.execute("UPDATE jobs SET state=? WHERE id=?", ('blocked' if child and group_alive(child.pid) else 'failed', job))
            raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='action', required=True)
    run = sub.add_parser('run')
    run.add_argument('--owner')
    run.add_argument('--label', required=True)
    run.add_argument('command', nargs=argparse.REMAINDER)
    sub.add_parser('status')
    sub.add_parser('check')
    cancel = sub.add_parser('cancel')
    cancel.add_argument('job')
    cancel.add_argument('--owner', required=True)
    recover = sub.add_parser('recover')
    recover.add_argument('job')
    recover.add_argument('--confirmed-stopped', action='store_true', required=True)
    args = parser.parse_args()
    with connect() as db:
        if args.action == 'run':
            return run_job(db, args)
        if args.action == 'check':
            return 0 if active_context(db) else 1
        if args.action == 'status':
            print(json.dumps([dict(r) for r in db.execute("SELECT * FROM jobs WHERE state NOT IN ('finished','cancelled','failed','abandoned') ORDER BY seq")], ensure_ascii=False))
            return 0
        row = db.execute('SELECT * FROM jobs WHERE id=?', (args.job,)).fetchone()
        if not row:
            raise ValueError('없는 작업입니다.')
        if args.action == 'cancel':
            if row['owner'] != args.owner:
                raise ValueError('다른 소유자의 작업을 취소할 수 없습니다.')
            db.execute("UPDATE jobs SET state=CASE WHEN state='waiting' THEN 'cancelled' WHEN state='running' THEN 'cancelling' ELSE state END WHERE id=?", (args.job,))
        else:
            # Never steal a live slot based on age. Explicit recovery only after inspection.
            with (root_dir() / 'mobile.lock').open('a') as lock:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                db.execute('BEGIN IMMEDIATE')
                if process_birth(row['pid']) == row['birth'] or group_alive(row['pgid']):
                    raise ValueError('관련 프로세스가 살아 있어 복구할 수 없습니다.')
                db.execute("UPDATE jobs SET state='abandoned' WHERE id=?", (args.job,))
                db.commit()
    return 0


if __name__ == '__main__':
    try:
        record_usage()
        sys.exit(main())
    except (ValueError, OSError, sqlite3.Error) as error:
        print(str(error), file=sys.stderr)
        sys.exit(2)
