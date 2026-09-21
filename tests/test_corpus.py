"""Synthetic, explicitly labelled unit-test fixtures; not corpus evidence."""
import hashlib
import importlib.util
import json
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[1]

def module():
    path = ROOT / 'scripts/corpus.py'
    assert path.exists(), 'Corpus implementation does not exist yet'
    spec = importlib.util.spec_from_file_location('corpus', path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

def chunk(id='fixture-a', content='Connector equations with flow variables', **kw):
    return dict(id=id, collection='A', source_id='A1', title='SYNTHETIC UNIT TEST FIXTURE',
                url='https://example.invalid/fixture', locator='fixture section', content=content,
                sha256=hashlib.sha256(content.encode()).hexdigest(), rights_note='Synthetic unit test fixture',
                type='spec', task=['generate-component'], domain=['general'], audience=['methods'],
                must_compile=False, **kw)

def write_chunks(root, records):
    directory = root / 'corpus/chunks'
    directory.mkdir(parents=True, exist_ok=True)
    (directory / 'fixtures.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in records))

def test_build_validates_provenance_and_search_is_literal(tmp_path):
    c = module()
    write_chunks(tmp_path, [chunk(), chunk('fixture-b', 'voltage resistor current')])
    result = c.build_index(tmp_path)
    assert result['chunks'] == 2
    assert c.search(tmp_path, 'connector " OR * --')[0]['id'] == 'fixture-a'
    assert c.search(tmp_path, 'nonexistentword') == []
    assert c.status(tmp_path)['collections'] == {'A': 2}
    records = [chunk()]
    records[0]['sha256'] = '0'*64
    write_chunks(tmp_path, records)
    with pytest.raises(ValueError, match='sha256'):
        c.build_index(tmp_path)
    assert c.status(tmp_path)['chunks'] == 2  # failed rebuild preserves old index


def test_lookup_real_compiler_includes_inherited_connectors():
    c = module()
    assert hasattr(c, 'lookup_class'), 'Exact compiler lookup not implemented'
    for name in ('Modelica.X);system("id")', 'Modelica..X', 'Modelica.X\n', '../X'):
        with pytest.raises(ValueError, match='class name'):
            c.lookup_class(ROOT, name)
    found = c.lookup_class(ROOT, 'Modelica.Electrical.Analog.Basic.Resistor')
    assert found['fqn'] == 'Modelica.Electrical.Analog.Basic.Resistor'
    assert found['library_version'] == '4.1.0'
    assert found['availability'] == 'compiler-loadable'
    assert {x['name'] for x in found['connectors']} >= {'p', 'n'}
    assert 'R' in {x['name'] for x in found['parameters']}
    assert found['source']['line_start'] > 0
    assert len(found['source']['sha256']) == 64
    assert '+maint.om' in found['library_source_path']
    assert found['verification'] == 'OMC reflection; not a simulation pass'
    with pytest.raises(ValueError, match='not found'):
        c.lookup_class(ROOT, 'Modelica.Electrical.Analog.Basic.NotARealModel')


def test_inventory_uses_pinned_source_interfaces_without_equation_bodies():
    c = module()
    assert hasattr(c, 'run_inventory'), 'Library inventory is not implemented'
    result = c.run_inventory('Modelica', 'Modelica.Electrical.Analog.Basic')
    records = result['classes']
    r = next(x for x in records if x['fqn'] == 'Modelica.Electrical.Analog.Basic.Resistor')
    assert r['source']['path'].startswith(str(ROOT / 'repos/ModelicaStandardLibrary'))
    assert r['restriction'] == 'model'
    assert r['extends'] == ['Modelica.Electrical.Analog.Interfaces.OnePort', 'Modelica.Electrical.Analog.Interfaces.ConditionalHeatPort']
    assert 'R' in {x['name'] for x in r['parameters']}
    assert 'equation' not in r
    assert result['errors'] == []
    assert len(records) > 10
    assert len(result['commit']) == 40


def test_document_chunking_preserves_text_and_source_hash():
    c = module()
    assert hasattr(c, 'document_records'), 'Traceable document chunking missing'
    text = ('SYNTHETIC UNIT TEST FIXTURE: equation connector when.\n'*500)
    records = c.document_records('A', 'A1', 'fixture', 'Synthetic test', 'https://example.invalid/test',
                                 text, 'fixture.txt', 'a'*64, 'Synthetic fixture', max_chars=2000)
    assert ''.join(r['content'] for r in records) == text
    assert len(records) > 1
    for r in records:
        c.validate(r)
        assert r['id'].startswith('technical-')
        assert r['source_sha256'] == 'a'*64
        assert 'chars' in r['locator']


@pytest.mark.skipif(__import__('os').environ.get('CORPUS_ACQUIRE') != '1', reason='Explicit network acquisition integration')
def test_acquire_real_pinned_technical_sources():
    c = module()
    assert hasattr(c, 'acquire_technical'), 'Source acquisition missing'
    result = c.acquire_technical()
    assert result['mls_version'] == '3.7'
    assert result['mcp_version'] == '2025-11-25'
    records = [json.loads(l) for l in (ROOT/'corpus/chunks/technical.jsonl').read_text().splitlines()]
    for r in records:
        c.validate(r)
    assert {r['source_id'] for r in records} >= {'A1', 'C1', 'C2', 'C3', 'C4', 'C5', 'C6', 'C7'}
    assert any(r['source_id']=='C2' and 'getErrorString' in r['content'] and 'checkModel' in r['content'] for r in records)
    assert any(r['source_id']=='A1' and 'when' in r['content'] for r in records)
    assert any(r['source_id']=='C5' and 'MCP' in r['content'] for r in records)
    assert not any('master' in r['url'] or '/draft/' in r['url'] for r in records)


def test_generation_bundle_fails_closed_and_uses_exact_interfaces(tmp_path):
    c = module()
    assert hasattr(c, 'generation_bundle'), 'Generation bundle missing'
    a = chunk('fixture-spec', 'Connector equations connect flow electrical', chapter='connectors-and-connections')
    d = chunk('fixture-paper', 'Compiler error feedback loop repairs Modelica models')
    d.update(collection='D', source_id='D2', type='llm-paper')
    api = chunk('fixture-api', 'Use checkModel and getErrorString for diagnostics')
    api.update(collection='C', source_id='C2', type='tool-api')
    fqns = ['Modelica.Electrical.Analog.Basic.Resistor','Modelica.Electrical.Analog.Basic.Inductor','Modelica.Electrical.Analog.Sources.StepVoltage']
    libs = []
    for i, fqn in enumerate(fqns):
        r = chunk('fixture-library-'+str(i), 'SYNTHETIC TEST ONLY '+fqn, fqn=fqn)
        r.update(source_id='A2', type='library-class')
        libs.append(r)
    all_records = [a,d,api,*libs]
    for missing in (a,d,api,libs[0]):
        write_chunks(tmp_path, [r for r in all_records if r is not missing])
        c.build_index(tmp_path)
        with pytest.raises(ValueError, match='Missing required'):
            c.generation_bundle(tmp_path, 'step driven RL circuit')
    write_chunks(tmp_path, all_records)
    c.build_index(tmp_path)
    bundle = c.generation_bundle(tmp_path, 'step driven RL circuit')
    assert bundle['paper']['source_id'] == 'D2'
    assert bundle['specification']['source_id'] == 'A1'
    assert bundle['compiler_diagnostics']['source_id'] == 'C2'
    assert [r['fqn'] for r in bundle['library_interfaces']] == fqns
    assert all(r['connectors'] for r in bundle['library_interfaces'])
    assert all(r['runtime_source']['sha256'] and 'not claimed bit-identical' in r['version_note'] for r in bundle['library_interfaces'])
    assert len(bundle['library_interfaces']) in (2,3)
    assert bundle['must_compile'] is True


def test_symbolic_dimensions_do_not_break_reflected_interfaces():
    c = module()
    indexed = c.run_inventory('Modelica', 'Modelica.Blocks.Continuous.Filter')
    assert indexed['errors'] == [], indexed['errors']
    record = indexed['classes'][0]
    assert 'low pass' in record['documentation']
    parameter = next(x for x in record['parameters'] if x['name']=='x_start')
    assert parameter['dimensions'] == '{nx}'
    found = c.lookup_class(ROOT, 'Modelica.Blocks.Continuous.Filter')
    assert {'u','y'} <= {x['name'] for x in found['connectors']}
    assert all(type(x['flow']) is bool for x in found['connectors'])


def test_cli_build_status_search_and_fail_closed_bundle(tmp_path):
    import subprocess
    import sys
    write_chunks(tmp_path, [chunk()])
    def run(*args):
        return subprocess.run([sys.executable,str(ROOT/'scripts/corpus.py'),'--root',str(tmp_path),*args],text=True,capture_output=True)
    built = run('build')
    assert built.stdout.strip(), 'CLI emitted no result'
    assert built.returncode == 0, built.stderr
    assert json.loads(built.stdout)['chunks'] == 1
    assert json.loads(run('status').stdout)['sources'] == {'A1':1}
    assert json.loads(run('search','connector').stdout)[0]['id']=='fixture-a'
    failed = run('bundle','RL circuit')
    assert failed.returncode != 0
    assert 'Missing required' in json.loads(failed.stdout)['error']
    bad = run('lookup','Modelica.X);system("id")')
    assert bad.returncode != 0
    assert 'class name' in json.loads(bad.stdout)['error']


def test_archived_diagnostics_adapter_actually_checks_and_simulates():
    import subprocess
    import tempfile
    path = ROOT/'corpus/raw/C/C2-compiler-diagnostics-adapter.txt'
    assert path.exists(), 'Run acquire before adapter integration test'
    text = path.read_text()
    code = text[text.index('from OMPython import OMCSessionLocal'):text.index('The caller must also verify')]
    with tempfile.TemporaryDirectory(prefix='corpus-adapter-',dir=ROOT/'runtime/tmp') as directory:
        p = subprocess.run([str(ROOT/'bin/om'),'python3','-c',code],cwd=directory,text=True,capture_output=True,timeout=120)
        assert p.returncode == 0, p.stderr
        results = list(Path(directory).glob('*_res.mat'))
        assert len(results) == 1
        assert results[0].stat().st_size > 1000
        assert 'completed successfully' in p.stdout


def test_research_source_hash_schema_verifies_extracted_text_offsets(tmp_path):
    c = module()
    extracted = tmp_path/'corpus/raw/D/fixture.txt'
    extracted.parent.mkdir(parents=True)
    text = 'SYNTHETIC UNIT TEST FIXTURE compiler feedback loop text'
    extracted.write_text(text)
    r = chunk('fixture-research', text[10:40])
    r.update(collection='D',source_id='D1',type='llm-paper',sha256='a'*64,
             text_sha256=c.digest(text), extracted_path='corpus/raw/D/fixture.txt',
             source_start_char=10,source_end_char=40)
    write_chunks(tmp_path,[r])
    assert c.build_index(tmp_path)['chunks']==1
    found = c.search(tmp_path,'compiler')[0]
    assert found['sha256']=='a'*64  # preserve source checksum exactly
    assert found['content_sha256']==c.digest(r['content'])
    extracted.write_text(text+'tampered')
    with pytest.raises(ValueError,match='text_sha256'):
        c.build_index(tmp_path)
