#!/usr/bin/env python3
"""Register one implementation owner per repository and feature."""
# usage-stats: harness task-coordination
import argparse
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import time


def record_usage():
    if os.environ.get('AGENT_COORDINATION_DIR'):
        return
    recorder = Path.home() / '.agents/skills/usage-stats/scripts/usage_stats.py'
    if recorder.exists():
        subprocess.run([sys.executable, str(recorder), 'record', 'harness', 'task-coordination'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)


def owner_id(explicit=None):
    owner = explicit or os.environ.get('AGENT_SESSION_ID') or os.environ.get('CODEX_THREAD_ID') or os.environ.get('CODEX_SESSION_ID')
    if not owner:
        raise ValueError('안정적인 세션 ID를 --owner 또는 AGENT_SESSION_ID로 지정하세요.')
    return owner


def repository_id(path):
    return subprocess.check_output(['git', '-C', str(path), 'rev-parse', '--path-format=absolute', '--git-common-dir'], text=True).strip()


def connect():
    root = Path(os.environ.get('AGENT_COORDINATION_DIR', '~/.local/state/agent-coordination')).expanduser()
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    db = sqlite3.connect(root / 'tasks.sqlite3', timeout=30, isolation_level=None)
    db.row_factory = sqlite3.Row
    db.execute('CREATE TABLE IF NOT EXISTS tasks (repo TEXT, feature TEXT, owner TEXT, workspace TEXT, branch TEXT, scope TEXT, updated REAL, PRIMARY KEY(repo, feature))')
    return db


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['list', 'claim', 'release', 'handoff'])
    parser.add_argument('--repo', default='.')
    parser.add_argument('--feature')
    parser.add_argument('--owner')
    parser.add_argument('--scope', default='')
    parser.add_argument('--to-owner')
    args = parser.parse_args()
    repo = repository_id(args.repo)
    with connect() as db:
        if args.action == 'list':
            print(json.dumps([dict(r) for r in db.execute('SELECT * FROM tasks WHERE repo=?', (repo,))], ensure_ascii=False))
            return
        if not args.feature or not args.feature.strip():
            parser.error('--feature가 필요합니다.')
        owner = owner_id(args.owner)
        db.execute('BEGIN IMMEDIATE')
        row = db.execute('SELECT * FROM tasks WHERE repo=? AND feature=?', (repo, args.feature)).fetchone()
        if row and row['owner'] != owner:
            raise ValueError(f"이미 담당자가 있습니다: {row['owner']} ({row['workspace']}). 인계 없이 중복 구현하지 마세요.")
        if args.action == 'claim':
            if not args.scope.strip():
                parser.error('claim에는 --scope가 필요합니다.')
            branch = subprocess.check_output(['git', '-C', args.repo, 'branch', '--show-current'], text=True).strip()
            db.execute('INSERT OR REPLACE INTO tasks VALUES (?,?,?,?,?,?,?)', (repo, args.feature, owner, str(Path(args.repo).resolve()), branch, args.scope, time.time()))
        elif not row:
            raise ValueError('등록된 담당 작업이 없습니다.')
        elif args.action == 'release':
            db.execute('DELETE FROM tasks WHERE repo=? AND feature=?', (repo, args.feature))
        else:
            if not args.to_owner:
                parser.error('handoff에는 --to-owner가 필요합니다.')
            db.execute('UPDATE tasks SET owner=?, updated=? WHERE repo=? AND feature=?', (args.to_owner, time.time(), repo, args.feature))
        db.commit()
        print(json.dumps({'action': args.action, 'feature': args.feature, 'owner': args.to_owner or owner}))


if __name__ == '__main__':
    try:
        record_usage()
        main()
    except (ValueError, sqlite3.Error, subprocess.CalledProcessError) as error:
        print(str(error), file=sys.stderr)
        sys.exit(2)
