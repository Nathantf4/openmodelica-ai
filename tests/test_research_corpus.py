"""Offline acceptance checks for independently acquired B/D/E/F sources."""
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
import importlib.util

ROOT = Path(__file__).resolve().parents[1]
M = json.loads((ROOT / 'corpus/manifests/research.json').read_text())
C = [json.loads(line) for line in (ROOT / M['chunk_file']).read_text().splitlines()]
S = {s['source_id']: s for s in M['sources']}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_required_sources_and_honest_gaps():
    assert {'D1', 'D2', 'D3', 'D4', 'D5', 'D6', 'B1', 'B2', 'B3', 'B4', 'E1', 'E2', 'E3', 'E4'} <= S.keys()
    assert S['D4']['status'] == 'metadata-only-blocked'
    assert '2.1' in S['B2']['title'] and '3.3' in S['B2']['briefing_mismatch']
    assert not ({'D4', 'B3', 'B4'} & {c['source_id'] for c in C})
    assert all(S[s]['chunk_count'] == 0 for s in ['D4', 'B3', 'B4'])


def test_schema_and_enum_tags():
    required = {'id', 'collection', 'source_id', 'title', 'url', 'locator', 'content', 'sha256', 'type', 'task', 'domain', 'audience', 'must_compile'}
    tasks = {'generate-component', 'generate-test', 'simulate', 'edit-diagram', 'search-library', 'mcp-tool', 'export-fmu'}
    domains = {'electrical-power', 'machines-drives', 'control', 'thermal', 'general'}
    audiences = {'methods', 'corporate-ee', 'interoperability'}
    for c in C:
        assert required <= c.keys()
        assert c.get('license') or c.get('rights_note')
        assert c['id'].startswith('research-')
        assert c['collection'] in {'B', 'D', 'E', 'F'}
        assert c['source_id'] in S
        assert c['type'] in {'spec', 'textbook', 'example-mo', 'tool-api', 'llm-paper', 'library-class'}
        assert isinstance(c['must_compile'], bool)
        assert isinstance(c['task'], list) and c['task'] and set(c['task']) <= tasks
        assert isinstance(c['domain'], list) and c['domain'] and set(c['domain']) <= domains
        assert isinstance(c['audience'], list) and c['audience'] and set(c['audience']) <= audiences
        assert c['content'].strip() and 0 < len(c['content']) <= 4000
        assert len(c['sha256']) == 64
        assert c['untrusted_source'] is True


def test_counts_dedup_and_manifest_checksum():
    assert len(C) == M['chunk_count']
    assert len(S) == len(M['sources']) == M['source_count']
    assert len({c['id'] for c in C}) == len(C)
    assert dict(Counter(c['collection'] for c in C)) == M['chunk_counts_by_collection']
    assert dict(Counter(c['source_id'] for c in C)) == M['chunk_counts_by_source']
    assert digest(ROOT/M['chunk_file']) == M['chunk_file_sha256']
    assert all(s['chunk_count'] == sum(c['source_id'] == s['source_id'] for c in C) for s in S.values())


def test_every_chunk_is_exact_source_text_with_live_checksums():
    cache = {}
    for c in C:
        path = ROOT/c['extracted_path']
        if path not in cache:
            cache[path] = (path.read_text(), digest(path))
        text, actual = cache[path]
        assert actual == c['text_sha256']
        assert text[c['source_start_char']:c['source_end_char']] == c['content']
        s = S[c['source_id']]
        if c['source_id'] == 'B1' or not s.get('pages'):
            assert c['sha256'] == actual
        else:
            assert c['sha256'] == digest(ROOT/s['raw_path'])


def test_full_text_coverage_without_synthetic_summaries():
    grouped = defaultdict(list)
    for c in C:
        if c.get('retrieval_role') != 'compile-feedback':
            grouped[c['extracted_path']].append(c)
    for path, rows in grouped.items():
        rows.sort(key=lambda c:c['source_start_char'])
        assert rows[0]['source_start_char'] == 0
        assert all(a['source_end_char'] == b['source_start_char'] for a,b in zip(rows,rows[1:]))
        assert ''.join(c['content'] for c in rows) == (ROOT/path).read_text()


def test_all_downloaded_pdf_pages_have_text_and_provenance():
    for sid in ['D1','D1-v1','D2','D3','D5','E1','E2','E3','E4','B2']:
        s = S[sid]
        assert (ROOT/s['raw_path']).read_bytes().startswith(b'%PDF')
        assert s['pages'] > 0
        assert set(s['empty_pages']) == set(s['verified_blank_pages'])
        assert s['pages_requiring_ocr'] == []
        text = (ROOT/s['extracted_path']).read_text()
        assert text.count('===== PAGE ') == s['pages']
        assert s['chunk_count'] > 0


def test_book_english_only_and_include_completeness():
    inv = json.loads((ROOT/'corpus/raw/B/B1/inventory.json').read_text())
    s = S['B1']
    assert s['unresolved_includes'] == []
    assert s['english_rst_files'] == sum(i['kind']=='english-rst' for i in inv)
    assert s['referenced_code_files'] == sum(i['kind']=='literalinclude-code' for i in inv)
    for i in inv:
        assert not any(x in Path(i['upstream_path']).parts for x in ['locale','retired','build','_build'])
        assert digest(ROOT/i['path']) == i['sha256']
    assert 'NOT license' in s['rights_note']


def test_mandatory_feedback_excerpt_and_scoped_catalog():
    c = next(c for c in C if c['id'] == M['mandatory_compile_feedback_chunk'])
    assert c['source_id'] == 'D2' and 'page 8' in c['locator']
    assert 'compilation loop' in c['content'] and 'simulation loop' in c['content']
    assert 'OpenModelica API' in c['content'] and 'syntax or structural errors' in c['content']
    assert c['must_compile'] is True and 'behavioral' in c['context_note']
    catalog = json.loads((ROOT/'corpus/raw/F/catalog.json').read_text())
    assert len(catalog['entries']) <= 20
    assert not list((ROOT/'corpus/raw/F').rglob('*.pdf'))
    assert all(c['content_kind']=='proceedings-catalog-abstract' for c in C if c['collection']=='F')


def test_d1_version_identity_and_interstitial_rejection():
    assert digest(ROOT/'corpus/raw/D/D1/source.pdf') == digest(ROOT/'corpus/raw/D/D1/v2-pinned.pdf')
    assert digest(ROOT/'corpus/raw/D/D1/source.pdf') != digest(ROOT/'corpus/raw/D/D1/v1.pdf')
    assert S['D1']['version'].endswith('v2') and S['D1-v1']['version'].endswith('v1')
    assert json.loads((ROOT/'corpus/raw/B/B4/source.receipt.json').read_text())['status']=='rejected-interstitial'


def test_paragraph_chunker_preserves_content():
    spec = importlib.util.spec_from_file_location('research_build', ROOT/'scripts/research_build.py')
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    for text in ['x'*19000, ('Heading\n=======\n\n'+'sentence. '*230+'\n\n')*10, 'short', '']:
        spans=list(module.segments(text))
        assert ''.join(text[a:b] for a,b in spans)==text
        assert all(0 < b-a <= 4000 for a,b in spans)
