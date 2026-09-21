"""Stdio transport adapter to the OFFICIAL OMEdit MCP in a networkless container.

No replacement modeling implementation: schemas/results come from OMEdit.
No host HTTP listener, Docker socket mount, model API, or credential forwarding.
"""
import argparse
import asyncio
import itertools
import json
from pathlib import Path

from mcp import types
from mcp.server.lowlevel import Server
from mcp.server.stdio import stdio_server

ROOT = Path(__file__).resolve().parents[1]
CONTAINER = 'openmodelica-ai-omedit'
LAUNCHER = ROOT/'bin/omedit-mcp'
ALLOW = frozenset({
    'getClassNames', 'getSourceCode', 'setSourceCode', 'createClass', 'activeModel',
    'classDiagram', 'iconDiagram', 'getSimulationResultVariables', 'simulate',
    'resimulate', 'showPlot', 'plot', 'addComponent', 'setComponentPlacement',
    'addConnection', 'listConnections', 'listConnectors', 'setElementModifierValue',
    'listComponentParameters', 'listComponents', 'checkModel', 'loadModel',
    'loadFile', 'getSimulationResultPath',
})
HTTP = """import sys, urllib.request
payload=sys.stdin.buffer.read()
r=urllib.request.Request('http://127.0.0.1:3000/mcp/admin',data=payload,headers={
'Content-Type':'application/json','Accept':'application/json, text/event-stream'})
with urllib.request.urlopen(r,timeout=240) as response:
    sys.stdout.buffer.write(response.read())
"""
IDS = itertools.count(1)
LOCK = asyncio.Lock()
app = Server('omedit-isolated', version='1.0.0', instructions=(
    'Official OpenModelica 1.27.1 OMEdit tools through a local stdio adapter. '
    'All execution is in a networkless, non-root container scoped to the project. '
    'Compiler success is not physical validation. Query source before changing it. '
    'Save final models and verify analytic/reference behavior through the project smoke workflow.'))

async def rpc(method, params=None):
    payload = {'jsonrpc':'2.0','id':next(IDS),'method':method,'params':params or {}}
    async with LOCK:
        process = await asyncio.create_subprocess_exec(
            'docker','exec','-i',CONTAINER,'python3','-c',HTTP,
            stdin=asyncio.subprocess.PIPE,stdout=asyncio.subprocess.PIPE,stderr=asyncio.subprocess.PIPE)
        try:
            stdout, stderr = await asyncio.wait_for(process.communicate(json.dumps(payload).encode()), 250)
        except asyncio.TimeoutError:
            process.kill()
            await process.wait()
            raise RuntimeError('OMEdit request timed out; execution state unknown; inspect before retry')
        if process.returncode:
            raise RuntimeError(f'Official OMEdit transport failed: {stderr.decode(errors="replace")}')
        response = json.loads(stdout)
        if 'error' in response:
            raise RuntimeError(f'Official OMEdit JSON-RPC error: {response["error"]}')
        return response['result']

@app.list_tools()
async def list_tools():
    result = await rpc('tools/list')
    return [types.Tool.model_validate(t) for t in result['tools'] if t['name'] in ALLOW]

@app.call_tool()
async def call_tool(name, arguments):
    if name not in ALLOW:
        raise ValueError('Tool is not in the project allowlist')
    if name == 'loadFile':
        path = Path(arguments['fileName']).resolve(strict=True)
        if not path.is_relative_to(ROOT) or path.suffix != '.mo':
            raise ValueError('loadFile requires an existing .mo file inside the OpenModelica project')
        arguments = dict(arguments, fileName=str(path))
    result = types.CallToolResult.model_validate(await rpc('tools/call', {'name':name,'arguments':arguments}))
    if name == 'checkModel':
        # OMEdit 1.27.1 may return a text error as an RPC-success result.
        text = '\n'.join(c.text for c in result.content if isinstance(c,types.TextContent))
        if 'completed successfully' not in text:
            result.isError = True
    return result

async def main():
    process = await asyncio.create_subprocess_exec(str(LAUNCHER),'start',
        stdout=asyncio.subprocess.PIPE,stderr=asyncio.subprocess.PIPE)
    stdout,stderr = await process.communicate()
    if process.returncode:
        raise RuntimeError((stdout+stderr).decode(errors='replace'))
    await rpc('initialize', {'protocolVersion':'2025-11-25','capabilities':{},
                             'clientInfo':{'name':'hermes-local-adapter','version':'1.0'}})
    async with stdio_server() as (read,write):
        await app.run(read,write,app.create_initialization_options())

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--desktop',action='store_true',help='Target the desktop-visible isolated instance')
    options = parser.parse_args()
    if options.desktop:
        CONTAINER = 'openmodelica-ai-omedit-desktop'
        LAUNCHER = ROOT/'bin/omedit-desktop'
        app.name = 'omedit-desktop'
        app.instructions += ' This instance has a visible Wayland desktop window shared with the user.'
    asyncio.run(main())
