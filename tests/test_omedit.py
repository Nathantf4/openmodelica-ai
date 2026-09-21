import base64
import json
import subprocess
import unittest
import uuid
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

class OMEditTests(unittest.TestCase):
    def test_isolated_official_mcp_health(self):
        launcher = ROOT / 'bin' / 'omedit-mcp'
        self.assertTrue(launcher.exists(), 'Missing isolated OMEdit MCP launcher')
        result = subprocess.run([str(launcher), 'start'], capture_output=True, text=True, timeout=100)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        result = subprocess.run([str(launcher), 'health'], capture_output=True, text=True, timeout=20)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('OK', result.stdout)
        settings = json.loads(subprocess.check_output(['docker','inspect','openmodelica-ai-omedit']))[0]
        self.assertEqual(settings['HostConfig']['NetworkMode'], 'none')
        self.assertFalse(settings['HostConfig']['PortBindings'])
        self.assertEqual(settings['Config']['User'], '1000:1000')
        self.assertTrue(settings['HostConfig']['ReadonlyRootfs'])

class BridgeTests(unittest.IsolatedAsyncioTestCase):
    async def test_official_mcp_tools_check_simulate_and_errors(self):
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client
        bridge = ROOT / 'scripts/omedit_bridge.py'
        self.assertTrue(bridge.exists(), 'Missing stdio-to-isolated-official-MCP bridge')
        name = 'OMEditVerification_' + uuid.uuid4().hex[:10]
        out = ROOT/'artifacts/omedit'/name
        out.mkdir(parents=True)
        transcript = {'timestamp':datetime.now(timezone.utc).isoformat(), 'class':name, 'calls':[]}
        params = StdioServerParameters(command=str(ROOT/'.venv/bin/python'), args=[str(bridge)])
        async with stdio_client(params) as (reader, writer):
            async with ClientSession(reader, writer) as session:
                async def call(tool, args):
                    result = await session.call_tool(tool, args)
                    record = result.model_dump(mode='json')
                    for i, content in enumerate(record['content']):
                        if content['type'] == 'image':
                            image = out/f'{tool}-{i}.png'
                            image.write_bytes(base64.b64decode(content.pop('data')))
                            content['saved_image'] = str(image)
                    transcript['calls'].append({'tool':tool, 'arguments':args, 'result':record})
                    (out/'protocol.json').write_text(json.dumps(transcript,indent=2))
                    return result
                transcript['initialize'] = (await session.initialize()).model_dump(mode='json')
                tools = await session.list_tools()
                names = {t.name for t in tools.tools}
                transcript['tools'] = sorted(names)
                self.assertTrue({'checkModel','simulate','loadModel','setSourceCode','plot'} <= names)
                self.assertNotIn('resetEnvironment', names)
                loaded = await call('getClassNames', {})
                self.assertFalse(loaded.isError, str(loaded))
                if 'Modelica' not in ' '.join(c.text for c in loaded.content if c.type=='text'):
                    result = await call('loadModel', {'library':'Modelica','version':'4.1.0'})
                    self.assertFalse(result.isError, str(result))
                result = await call('createClass', {'className':name,'specialization':'model'})
                self.assertFalse(result.isError, str(result))
                code = (f'model {name} Real x(start=1,fixed=true); equation der(x)=-x; '
                        f'annotation(experiment(StartTime=0,StopTime=1,Interval=0.01,Tolerance=1e-8)); end {name};')
                result = await call('setSourceCode', {'className':name,'code':code})
                self.assertFalse(result.isError, str(result))
                result = await call('checkModel', {'className':name})
                self.assertFalse(result.isError, str(result))
                self.assertIn('completed successfully', str(result))
                result = await call('simulate', {'className':name})
                self.assertFalse(result.isError, str(result))
                result = await call('getSimulationResultPath', {'className':name})
                self.assertFalse(result.isError, str(result))
                self.assertTrue((out/f'{name}_res.mat').is_file(), str(result))
                result = await call('plot', {'className':name,'variables':['x']})
                self.assertFalse(result.isError, str(result))
                self.assertTrue(any(c.type == 'image' for c in result.content))
                result = await call('checkModel', {'className':'DefinitelyMissingClass'})
                self.assertTrue(result.isError, str(result))
                result = await call('loadFile', {'fileName':'/etc/passwd'})
                self.assertTrue(result.isError, str(result))
                transcript['verdict'] = 'PASS'
                (out/'protocol.json').write_text(json.dumps(transcript,indent=2))

if __name__ == '__main__':
    unittest.main()
