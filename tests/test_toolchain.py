"""Runtime acceptance uses the real compiler, not mocked output."""
import json
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

class ToolchainTests(unittest.TestCase):
    def test_host_omc_shim(self):
        import shutil
        shim = ROOT / 'bin' / 'omc'
        self.assertTrue(shim.exists(), 'Missing omc compatibility command')
        self.assertEqual(Path(shutil.which('omc') or '/missing').resolve(), shim.resolve())
        result = subprocess.run(['omc','--version'],text=True,capture_output=True,timeout=30)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(result.stdout.strip(),'OpenModelica 1.27.1')

    def test_container_cannot_modify_project_code(self):
        code = ('from pathlib import Path; '
                f'p=Path({str(ROOT)!r}); '
                'assert (p/"repos/ModelicaStandardLibrary/Modelica/package.mo").is_file(); '
                'blocked=False; '
                '\ntry: (p/"bin/sandbox-must-not-create").write_text("unsafe")'
                '\nexcept OSError: blocked=True'
                '\nassert blocked, "container can modify host-executed project code"'
                '\n(p/"artifacts/sandbox-write-proof.txt").write_text("writable output only")')
        result = subprocess.run([str(ROOT/'bin/om'),'python3','-c',code],text=True,capture_output=True,timeout=30)
        self.assertEqual(result.returncode,0,result.stderr)

    def test_pinned_compiler_and_ompython(self):
        runner = ROOT / 'bin' / 'om'
        self.assertTrue(runner.exists(), 'Missing isolated OpenModelica runner')
        version = subprocess.run([str(runner), 'omc', '--version'], text=True, capture_output=True, timeout=40)
        self.assertEqual(version.returncode, 0, version.stderr)
        self.assertIn('OpenModelica 1.27.1', version.stdout)
        code = ('import json; from OMPython import OMCSessionLocal; o=OMCSessionLocal(); '
                'r={"version":o.sendExpression("getVersion()"), '
                '"loaded":o.sendExpression(\'loadModel(Modelica, {"4.1.0"})\'), '
                '"msl":o.sendExpression("getVersion(Modelica)")}; '
                'print(json.dumps(r)); o.sendExpression("quit()")')
        result = subprocess.run([str(runner), 'python3', '-c', code], text=True, capture_output=True, timeout=90)
        self.assertEqual(result.returncode, 0, result.stderr)
        data = json.loads(result.stdout)
        self.assertIs(data['loaded'], True)
        self.assertEqual(data['msl'], '4.1.0')
        self.assertEqual(data['version'], 'OpenModelica 1.27.1')

if __name__ == '__main__':
    unittest.main()
