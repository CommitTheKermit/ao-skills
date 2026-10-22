import json
import os
from pathlib import Path
import signal
import sqlite3
import subprocess
import sys
import tempfile
import time
import unittest

HERE = Path(__file__).parent
QUEUE = HERE / 'validation_queue.py'
TASK = HERE.parents[1] / 'task-coordination/scripts/task_registry.py'


class CoordinationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.env = dict(os.environ, AGENT_COORDINATION_DIR=str(self.root / 'state'), AGENT_SESSION_ID='test-owner')
        self.env.pop('MOBILE_VALIDATION_JOB', None)
        self.processes = []

    def tearDown(self):
        for p in self.processes:
            if p.poll() is None:
                p.terminate()
                try:
                    p.wait(timeout=8)
                except subprocess.TimeoutExpired:
                    p.kill()
                    p.wait()
            if p.stdout: p.stdout.close()
            if p.stderr: p.stderr.close()
        self.tmp.cleanup()

    def call(self, tool, *args, **kwargs):
        return subprocess.run([sys.executable, str(tool), *args], env=self.env, capture_output=True, text=True, **kwargs)

    def job(self, code, owner='test-owner'):
        p = subprocess.Popen([sys.executable, str(QUEUE), 'run', '--owner', owner, '--label', 'test', '--', sys.executable, '-c', code], env=self.env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        self.processes.append(p)
        return p

    def rows(self):
        out = self.call(QUEUE, 'status')
        self.assertEqual(out.returncode, 0, out.stderr)
        return json.loads(out.stdout)

    def wait_state(self, count=1, state='running'):
        deadline = time.monotonic() + 8
        while time.monotonic() < deadline:
            rows = self.rows()
            found = [r for r in rows if r['state'] == state]
            if len(found) >= count: return found
            time.sleep(.05)
        self.fail(f'No state {state}: {rows}')

    def test_concurrent_jobs_never_overlap_and_keep_fifo(self):
        log = self.root / 'events'
        def code(n):
            return f"import time; p={str(log)!r}; f=open(p,'a'); f.write('{n} start\\n'); f.flush(); time.sleep(.4); f.write('{n} end\\n'); f.close()"
        first = self.job(code(1))
        self.wait_state()
        second = self.job(code(2))
        self.wait_state(state='waiting')
        third = self.job(code(3))
        for p in (first, second, third): self.assertEqual(p.wait(timeout=10), 0, p.stderr.read())
        self.assertEqual(log.read_text().splitlines(), ['1 start','1 end','2 start','2 end','3 start','3 end'])

    def test_nested_wrapper_reuses_parent_slot(self):
        p = self.job(f"import subprocess,sys; sys.exit(subprocess.call([sys.executable,{str(QUEUE)!r},'run','--label','nested','--',sys.executable,'-c','print(123)']))")
        self.assertEqual(p.wait(timeout=8), 0, p.stderr.read())
        self.assertEqual(p.stdout.read().strip(), '123')

    def test_cancel_waiter_does_not_execute(self):
        first = self.job('import time; time.sleep(1)')
        self.wait_state()
        marker = self.root / 'bad'
        second = self.job(f"from pathlib import Path; Path({str(marker)!r}).touch()")
        row = self.wait_state(state='waiting')[0]
        self.assertEqual(self.call(QUEUE,'cancel',row['id'],'--owner','test-owner').returncode, 0)
        self.assertEqual(second.wait(timeout=8), 130)
        self.assertEqual(first.wait(timeout=8), 0)
        self.assertFalse(marker.exists())

    def test_cancel_running_stops_child_before_next_job(self):
        first = self.job('import time; time.sleep(30)')
        row = self.wait_state()[0]
        self.assertNotEqual(self.call(QUEUE,'cancel',row['id'],'--owner','stranger').returncode, 0)
        self.assertEqual(self.call(QUEUE,'cancel',row['id'],'--owner','test-owner').returncode, 0)
        self.assertEqual(first.wait(timeout=8), 130, first.stderr.read())
        self.assertEqual(self.job('pass').wait(timeout=8), 0)

    def test_failed_command_releases_slot(self):
        self.assertEqual(self.job('raise SystemExit(7)').wait(timeout=8), 7)
        self.assertEqual(self.job('pass').wait(timeout=8), 0)

    def test_crashed_supervisor_does_not_allow_overlap(self):
        first = self.job('import time; time.sleep(1.5)')
        row = self.wait_state()[0]
        first.kill(); first.wait()
        second = self.job('pass')
        self.wait_state(state='waiting')
        self.assertIsNone(second.poll())
        out = self.call(QUEUE,'recover',row['id'],'--confirmed-stopped')
        self.assertNotEqual(out.returncode,0)
        # Orphan process detection is intentionally fail-closed, even after timeout.
        time.sleep(1.7)
        self.assertIsNone(second.poll())
        recovered = self.call(QUEUE,'recover',row['id'],'--confirmed-stopped')
        self.assertEqual(recovered.returncode,0,recovered.stderr)
        self.assertEqual(second.wait(timeout=8),0,second.stderr.read())

    def test_fake_nested_token_rejected(self):
        self.env['MOBILE_VALIDATION_JOB'] = 'fake'
        self.assertNotEqual(self.call(QUEUE,'run','--label','test','--',sys.executable,'-c','pass').returncode,0)

    def repo(self):
        repo = self.root/'repo'; repo.mkdir()
        subprocess.run(['git','init','-q',str(repo)],check=True)
        subprocess.run(['git','-C',str(repo),'-c','user.name=Test','-c','user.email=test@example.invalid','commit','--allow-empty','-qm','init'],check=True)
        return repo

    def test_same_feature_atomic_claim_and_worktree_identity(self):
        repo=self.repo(); wt=self.root/'wt'
        subprocess.run(['git','-C',str(repo),'worktree','add','-qb','other',str(wt)],check=True)
        ps=[]
        for owner,path in [('one',repo),('two',wt)]:
            p=subprocess.Popen([sys.executable,str(TASK),'claim','--repo',str(path),'--feature','issue:1','--scope','same feature','--owner',owner],env=self.env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
            ps.append(p); self.processes.append(p)
        self.assertEqual(sorted(p.wait(timeout=8) for p in ps),[0,2])
        rows=json.loads(self.call(TASK,'list','--repo',str(wt)).stdout)
        self.assertEqual(len(rows),1)
        self.assertNotEqual(self.call(TASK,'release','--repo',str(repo),'--feature','issue:1','--owner','stranger').returncode,0)

    def test_handoff_and_release_require_owner(self):
        repo=self.repo()
        args=['--repo',str(repo),'--feature','feature:queue']
        self.assertEqual(self.call(TASK,'claim',*args,'--scope','queue','--owner','one').returncode,0)
        self.assertEqual(self.call(TASK,'handoff',*args,'--owner','one','--to-owner','two').returncode,0)
        self.assertEqual(self.call(TASK,'release',*args,'--owner','two').returncode,0)
        self.assertEqual(json.loads(self.call(TASK,'list','--repo',str(repo)).stdout),[])


if __name__ == '__main__': unittest.main()
