import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_visible_mcp_omedit_is_networkless_and_healthy():
    launcher = ROOT/'bin/omedit-desktop'
    assert launcher.exists(), 'Missing desktop-visible MCP OMEdit launcher'
    run = subprocess.run([str(launcher),'start'],capture_output=True,text=True,timeout=100)
    assert run.returncode == 0,run.stdout+run.stderr
    run = subprocess.run([str(launcher),'health'],capture_output=True,text=True,timeout=15)
    assert run.returncode == 0 and 'OK' in run.stdout,run.stdout+run.stderr
    info = json.loads(subprocess.check_output(['docker','inspect','openmodelica-ai-omedit-desktop']))[0]
    assert info['HostConfig']['NetworkMode'] == 'none'
    assert not info['HostConfig']['PortBindings']
    assert info['HostConfig']['ReadonlyRootfs']
    assert any('wayland' in m['Source'] for m in info['Mounts'])
    assert all(m['Source'] != '/home/nathan' for m in info['Mounts'])
    # Match the visible Wayland client to the actual container process, not any OMEdit.
    processes = subprocess.check_output(['docker','top','openmodelica-ai-omedit-desktop','-eo','pid,comm'],text=True)
    pids = {int(line.split()[0]) for line in processes.splitlines()[1:] if line.split()[-1]=='OMEdit'}
    clients = json.loads(subprocess.check_output(['hyprctl','clients','-j']))
    assert any(c['pid'] in pids and c['mapped'] for c in clients), 'MCP process has no visible desktop window'


async def _probe_desktop_bridge():
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
    params = StdioServerParameters(command=str(ROOT/'.venv/bin/python'),
        args=[str(ROOT/'scripts/omedit_bridge.py'),'--desktop'])
    async with stdio_client(params) as (read,write):
        async with ClientSession(read,write) as session:
            init = await session.initialize()
            assert init.serverInfo.name == 'omedit-desktop'
            tools = await session.list_tools()
            assert {'loadFile','checkModel','simulate','plot'} <= {t.name for t in tools.tools}
            result = await session.call_tool('getClassNames',{})
            assert not result.isError
            assert 'Modelica' in str(result)


def test_desktop_stdio_targets_visible_instance():
    import asyncio
    asyncio.run(_probe_desktop_bridge())
