"""Real stdio protocol integration; synthetic corpus is a labelled test fixture."""
import json
from pathlib import Path
import sys
import anyio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from test_corpus import ROOT, module, write_chunks, chunk


def test_mcp_stdio_is_read_only_and_exercises_real_tools(tmp_path):
    server = ROOT / 'scripts/corpus_mcp.py'
    assert server.exists(), 'Read-only corpus MCP server missing'
    write_chunks(tmp_path, [chunk()])
    module().build_index(tmp_path)
    async def scenario():
        params = StdioServerParameters(command=sys.executable,args=[str(server),'--root',str(tmp_path)])
        async with stdio_client(params) as (reader, writer):
            async with ClientSession(reader, writer) as session:
                init = await session.initialize()
                assert init.serverInfo.name == 'openmodelica-corpus'
                tools = (await session.list_tools()).tools
                assert {t.name for t in tools} == {'search_corpus','lookup_class','generation_bundle'}
                assert all(t.annotations.readOnlyHint and not t.annotations.destructiveHint and not t.annotations.openWorldHint for t in tools)
                found = await session.call_tool('search_corpus',{'query':'connector'})
                assert not found.isError
                assert 'fixture-a' in str(found)
                invalid = await session.call_tool('lookup_class',{'class_name':'Modelica.X);system("id")'})
                assert invalid.isError
                lookup = await session.call_tool('lookup_class',{'class_name':'Modelica.Electrical.Analog.Basic.Resistor'})
                assert not lookup.isError, lookup
                assert 'compiler-loadable' in str(lookup)
                bundle = await session.call_tool('generation_bundle',{'query':'RL circuit'})
                assert bundle.isError
                assert 'Missing required' in str(bundle)
    anyio.run(scenario)
