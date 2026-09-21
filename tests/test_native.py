import os
import subprocess
import unittest
from pathlib import Path

class NativeOpenModelicaTests(unittest.TestCase):
    def test_native_bouncing_ball_simulates(self):
        import csv
        import math
        import tempfile
        root = Path('/home/nathan/openmodelica-ai')
        base = root/'artifacts/native-smoke'
        base.mkdir(exist_ok=True)
        output = Path(tempfile.mkdtemp(prefix='run-',dir=base))
        source = Path.home()/'.local/opt/openmodelica-1.27.1/usr/share/doc/omc/testmodels/BouncingBall.mo'
        script = output/'run.mos'
        script.write_text(f'loadFile("{source}");\ngetErrorString();\ncheckModel(BouncingBall);\ngetErrorString();\nsimulate(BouncingBall,stopTime=1,numberOfIntervals=500,tolerance=1e-8,outputFormat="csv");\ngetErrorString();\n')
        result = subprocess.run([str(Path.home()/'.local/bin/omc-native'),str(script)],cwd=output,text=True,capture_output=True,timeout=120)
        (output/'compiler.log').write_text(result.stdout+'\nSTDERR\n'+result.stderr)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertIn('Check of BouncingBall completed successfully.',result.stdout)
        self.assertIn('simulation finished successfully',result.stdout.lower())
        data = output/'BouncingBall_res.csv'
        self.assertTrue(data.exists(),result.stdout)
        with data.open() as stream:
            rows = list(csv.DictReader(stream))
        self.assertGreater(len(rows),500)
        errors=[]
        for row in rows:
            t,h=float(row['time']),float(row['h'])
            self.assertTrue(math.isfinite(h))
            if t<0.4:
                errors.append(abs(h-(1-0.5*9.81*t*t)))
        self.assertLess(max(errors),1e-5)
        print(f'Native simulation PASS: {data}; ballistic maximum error={max(errors):.3g}')

    def test_native_compiler_and_gui_are_available(self):
        root = Path.home()/'.local/opt/openmodelica-1.27.1'
        self.assertTrue((root/'usr/bin/OMEdit').exists(), 'Native OMEdit not installed')
        command = Path.home()/'.local/bin/omc-native'
        self.assertTrue(command.exists(), 'Native compiler launcher missing')
        result = subprocess.run([str(command),'--version'],text=True,capture_output=True,timeout=30)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(result.stdout.strip(),'OpenModelica 1.27.1')
        gui = subprocess.run([str(Path.home()/'.local/bin/OMEdit'),'--help'],text=True,capture_output=True,timeout=30)
        self.assertEqual(gui.returncode,0,gui.stderr)
        self.assertIn('OMEdit [options]', gui.stdout + gui.stderr)
        launcher = Path.home()/'.local/share/applications/openmodelica-omedit.desktop'
        self.assertTrue(launcher.is_file())
        result = subprocess.run(['desktop-file-validate',str(launcher)],capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)

if __name__ == '__main__':
    unittest.main()
