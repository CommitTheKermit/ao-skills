import contextlib
import io
import json
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import patch
import run


class RuntimeTests(unittest.TestCase):
    def setup_runtime(self, root):
        runtime = Path(root)/'release'
        runtime.mkdir()
        (runtime/'runtime.json').write_text(json.dumps(dict(source_sha='a'*40,package_version='0.2.0')))
        probe = dict(version='0.2.0',module=str(runtime/'lib/jev_mobile_use/__init__.py'),prefix=str(runtime))
        return runtime, probe

    def test_guarded_isolated_runtime_ignores_old_caller_modes(self):
        with tempfile.TemporaryDirectory() as root:
            runtime, probe = self.setup_runtime(root)
            with patch.object(run.subprocess,'run',return_value=SimpleNamespace(stdout=json.dumps(probe))) as query, \
                 patch.object(run.os,'execv') as execute:
                self.assertEqual(run.main(['--backend','adb','--coordination','standalone'],runtime),0)
                argv=execute.call_args.args[1]
                self.assertEqual(argv[1:4],['-I','-m','jev_mobile_use'])
                self.assertEqual(argv[-4:],['--backend','droidrun','--coordination','agent'])
                self.assertIn('-I',query.call_args.args[0])

    def test_runtime_info_reports_exact_commit_without_execution(self):
        with tempfile.TemporaryDirectory() as root:
            runtime,probe=self.setup_runtime(root)
            with patch.object(run.subprocess,'run',return_value=SimpleNamespace(stdout=json.dumps(probe))), \
                 patch.object(run.os,'execv') as execute, contextlib.redirect_stdout(io.StringIO()) as out:
                self.assertEqual(run.main(['--runtime-info'],runtime),0)
                self.assertEqual(json.loads(out.getvalue())['source_sha'],'a'*40)
                execute.assert_not_called()

    def test_missing_receipt_foreign_import_or_old_version_never_falls_back(self):
        for case in ['missing','foreign','version','prefix']:
            with self.subTest(case=case),tempfile.TemporaryDirectory() as root:
                runtime,probe=self.setup_runtime(root)
                if case=='missing':(runtime/'runtime.json').unlink()
                if case=='foreign':probe['module']='/old-checkout/src/jev_mobile_use/__init__.py'
                if case=='version':probe['version']='0.1.0'
                if case=='prefix':probe['prefix']='/old-venv'
                with patch.object(run.subprocess,'run',return_value=SimpleNamespace(stdout=json.dumps(probe))), \
                     patch.object(run.os,'execv') as execute,contextlib.redirect_stderr(io.StringIO()):
                    self.assertEqual(run.main([],runtime),2)
                    execute.assert_not_called()


if __name__=='__main__':unittest.main()
