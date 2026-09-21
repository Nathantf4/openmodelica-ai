#!/usr/bin/env python3
"""Build an offline, traceable B/D/E/F corpus from acquired originals.
Run from anywhere: .venv/bin/python scripts/research_build.py
Does not download, execute source examples, call models, or touch other collections.
"""
from __future__ import annotations
from bisect import bisect_right
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import pymupdf
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / 'corpus/raw'
CHUNKS = ROOT / 'corpus/chunks/research.jsonl'
MANIFEST = ROOT / 'corpus/manifests/research.json'


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path: Path):
    return json.loads(path.read_text())


def write_json(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + '\n')


def segments(text: str, maximum: int = 4000, target: int = 3000):
    """Contiguous offsets; prefer paragraphs, then line/sentence/word boundaries.
    Short source/tail chunks are kept, never padded with synthetic text.
    """
    start = 0
    while start < len(text):
        if len(text) - start <= maximum:
            end = len(text)
        else:
            candidate = text.rfind('\n\n', start + 1500, start + target)
            if candidate < 0:
                candidate = text.rfind('\n\n', start + target, start + maximum)
            if candidate >= 0:
                end = candidate + 2
            else:
                candidate = text.rfind('\n', start + 1500, start + maximum)
                if candidate < 0:
                    candidate = text.rfind('. ', start + 1500, start + maximum - 1)
                if candidate < 0:
                    candidate = text.rfind(' ', start + 1500, start + maximum)
                end = candidate + 1 if candidate >= 0 else start + maximum
        yield start, end
        start = end


def domain_for(text: str, default=None):
    domains = []
    for domain, regex in [('electrical-power', r'electri|circuit|power.?system|phasor|\bRLC\b'),
                          ('machines-drives', r'motor|machine|drive|inertia|rotational'),
                          ('control', r'control|signal|feedback|hysteresis'),
                          ('thermal', r'thermal|heat|temperature|cooling')]:
        if re.search(regex, text, re.I):
            domains.append(domain)
    return domains or default or ['general']


sources = []
chunks = []

def add_source(s):
    s.setdefault('source_class', 'primary')
    s.setdefault('audience', ['methods'])
    s.setdefault('task', ['generate-component', 'simulate'])
    s.setdefault('must_compile', True)
    s.setdefault('domain', ['general'])
    s.setdefault('chunk_count', 0)
    sources.append(s)
    return s


def emit_document(s, path: Path, source_sha: str, kind=None, title=None, url=None, extra=None):
    text = path.read_text()
    page_marks = list(re.finditer(r'^===== PAGE (\d+) =====', text, re.M))
    page_starts = [m.start() for m in page_marks]
    for start, end in segments(text):
        if not text[start:end].strip():
            continue
        index = s['chunk_count'] + 1
        if page_marks:
            p1 = max(0, bisect_right(page_starts, start) - 1)
            p2 = max(0, bisect_right(page_starts, end - 1) - 1)
            locator = f'PDF pages {page_marks[p1].group(1)}-{page_marks[p2].group(1)}; {path.relative_to(ROOT)} chars {start}:{end}'
        else:
            l1 = text.count('\n', 0, start) + 1
            l2 = text.count('\n', 0, end - 1) + 1
            locator = f'{path.relative_to(ROOT)} lines {l1}-{l2}'
        chunk = {
            'id': f'research-{s["source_id"]}-{index:05d}',
            'collection': s['collection'], 'source_id': s['source_id'],
            'title': title or s['title'], 'url': url or s['url'], 'locator': locator,
            'content': text[start:end], 'sha256': source_sha,
            'rights_note': s['rights_note'], 'type': kind or s['type'],
            'task': s['task'], 'domain': domain_for((title or s['title']) + '\n' + text[start:end], s['domain']),
            'audience': s['audience'], 'must_compile': s['must_compile'],
            'content_kind': s.get('content_kind', 'primary-text'),
            'extracted_path': str(path.relative_to(ROOT)), 'text_sha256': sha(path),
            'source_start_char': start, 'source_end_char': end,
            'source_version': s.get('version'),
            'untrusted_source': True,
        }
        if extra:
            chunk.update(extra)
        chunks.append(chunk)
        s['chunk_count'] += 1


def pdf(sid, collection, basename, title, authors, url, rights, version=None, source_dir=None, kind='llm-paper', domain=None):
    directory = RAW / collection / (source_dir or sid)
    r = load(directory / f'{basename}.receipt.json')
    s = add_source({'source_id': sid, 'collection': collection, 'title': title, 'authors': authors,
        'url': url, 'acquisition_url': r['url'], 'version': version, 'type': kind,
        'rights_note': rights, 'status': 'full-text' if sid != 'B2' else 'public-excerpt-only',
        'content_kind': 'primary-text' if sid != 'B2' else 'public-excerpt',
        'sha256': r['sha256'], 'raw_path': r['raw_path'], 'extracted_path': r['text_path'],
        'pages': r['pages'], 'empty_pages': r['empty_pages'],
        'retrieved_at': r['retrieved_at'], 'metadata_verified_against': 'Original PDF title/author page; not PDF document properties',
        'domain': domain or ['general'], 'audience': ['methods', 'corporate-ee'] if collection == 'E' else ['methods']})
    s['verified_blank_pages'] = []
    s['pages_requiring_ocr'] = []
    with pymupdf.open(ROOT/r['raw_path']) as document:
        for n in r['empty_pages']:
            page = document[n-1]
            if not page.get_images() and not page.get_drawings() and not page.get_text().strip():
                s['verified_blank_pages'].append(n)
            else:
                s['pages_requiring_ocr'].append(n)
    emit_document(s, ROOT / r['text_path'], r['sha256'])
    return s


def main():
    sources.clear(); chunks.clear()
    pdf('D1','D','source','ModiGen: A Large Language Model-Based Framework for Modelica Component Generation in Multi-Domain Systems',
        ['Jiahui Xiang','Tong Ye','Peiyu Liu','Yinan Zhang','Wenhai Wang'], 'https://arxiv.org/pdf/2503.18460v2',
        'PDF title page states CC BY 4.0; arXiv metadata instead links nonexclusive-distrib/1.0. Preserve both notices; verify rights before redistribution.', '2503.18460v2')
    assert sha(RAW/'D/D1/source.pdf') == sha(RAW/'D/D1/v2-pinned.pdf'), 'Unversioned D1 no longer matches v2'
    pdf('D1-v1','D','v1','ModiGen: A Large Language Model-Based Workflow for Multi-Task Modelica Code Generation',
        ['Jiahui Xiang','Tong Ye','Peiyu Liu','Yinan Zhang','Wenhai Wang'], 'https://arxiv.org/pdf/2503.18460v1',
        'Public arXiv preprint, author copyright retained. arXiv non-exclusive distribution notice is not a general downstream license; local research use, do not redistribute without checking rights.', '2503.18460v1', 'D1')
    pdf('D2','D','source','Automating Modelica Module Generation Using Large Language Models: A Case Study on Building Control Description Language',
        ['Hanlong Wan','Xing Lu','Yan Chen','Karthik Devaprasad','Laura Hinkle'], 'https://arxiv.org/pdf/2509.14623v1',
        'Public arXiv/PNNL manuscript. arXiv non-exclusive distribution notice; DOE public-access and US-government-purpose notice on page 1 does not grant unrestricted downstream redistribution.', '2509.14623v1')
    pdf('D3','D','source','Text2Model: Generating Dynamic Chemical Reactor Models Using Large Language Models (LLMs)',
        ['Sophia Rupprecht','Yassine Hounat','Monisha Kumar','Giacomo Lastrucci','Artur M. Schweidtmann'], 'https://arxiv.org/pdf/2503.17004v1',
        'Public arXiv preprint; nonexclusive-distrib/1.0 notice, copyright retained. Local research copy; redistribution rights not assumed.', '2503.17004v1')
    pdf('D5','D','source','A Guide to Large Language Models in Modeling and Simulation: From Core Techniques to Critical Challenges',
        ['Philippe J. Giabbanelli'], 'https://arxiv.org/pdf/2602.05883v1',
        'CC BY-NC-ND 4.0 per arXiv license link. Local extracted retrieval text is not a permission to publish adaptations or use commercially.', '2602.05883v1')
    d4 = load(RAW/'D/D4/crossref.json')['message']
    add_source({'source_id':'D4','collection':'D','title':d4['title'][0],
        'authors':[f'{a.get("given", "")} {a["family"]}'.strip() for a in d4['author']],
        'url':'https://papers.ssrn.com/sol3/papers.cfm?abstract_id=5564442','doi':'10.2139/ssrn.5564442',
        'type':'llm-paper','status':'metadata-only-blocked','rights_note':'Copyright retained; no full-text rights established.',
        'metadata_verified_against':'Crossref DOI deposit only; primary full text unavailable',
        'raw_path':'corpus/raw/D/D4/crossref.json','sha256':sha(RAW/'D/D4/crossref.json'),
        'gap':'SSRN HTTP 403. Exact-title searches scoped to polimi.it and uc3m.es did not locate a matching public manuscript. A UC3M research-stay record is not the paper and is not substituted. No claims or summary chunks manufactured.'})
    r = load(RAW/'D/D6/source.receipt.json')
    d6 = add_source({'source_id':'D6','collection':'D','title':'AI-Powered System Simulation with Modelica',
        'authors':['Lixiang Li'],'url':r['url'],'type':'llm-paper','status':'full-text-html',
        'publication_date':'2026-03-18','source_class':'vendor-practitioner-account','content_kind':'primary-vendor-article',
        'rights_note':'Public Modelon blog; copyright retained, no blanket reuse license observed. Local research only.',
        'raw_path':r['raw_path'],'extracted_path':r['text_path'],'sha256':r['text_sha256'],
        'checksum_scope':'defuddle extraction; raw HTML has a separate receipt hash',
        'metadata_verified_against':'HTML title and visible byline/date'})
    emit_document(d6, ROOT/r['text_path'], r['text_sha256'])

    # A complete English narrative snapshot; no translations or Sphinx outputs.
    book = ROOT/'repos/ModelicaBook'
    commit = subprocess.check_output(['git','-C',str(book),'rev-parse','HEAD'],text=True).strip()
    tracked = subprocess.check_output(['git','-C',str(book),'ls-files'],text=True).splitlines()
    rst = sorted(f for f in tracked if f.startswith('text/source/') and f.endswith('.rst') and f not in {'text/source/advanced.rst','text/source/todo.rst'})
    b1 = add_source({'source_id':'B1','collection':'B','title':'Modelica by Example','authors':['Michael Tiller'],
        'url':'https://github.com/mtiller/ModelicaBook','version':commit,'type':'textbook','status':'english-source-text',
        'rights_note':'Copyright Michael Tiller. LICENSE.md grants CC BY-NC-ND 3.0 only to HTML output, and expressly does NOT license source/derived-work redistribution. This English source snapshot and retrieval chunks are local/private only. ModelicaByExample code separately MIT. Obtain permission before redistribution or commercial deployment.',
        'scope':'All tracked English narrative RST, excluding unwritten advanced.rst and developer todo.rst; literalinclude code retained once by source path; no locale/build/retired copies.',
        'raw_path':'corpus/raw/B/B1','source_files':[],'unresolved_includes':[]})
    inventory = []
    includes = set()
    for f in rst:
        src = book/f; dst = RAW/'B/B1'/f
        dst.parent.mkdir(parents=True, exist_ok=True); shutil.copyfile(src,dst)
        text = src.read_text()
        titles = re.findall(r'^([^\n]+)\n[-=~^]{3,}\s*$',text,re.M)
        title = 'Modelica by Example — ' + (titles[0].strip() if titles else Path(f).stem)
        inventory.append({'path':str(dst.relative_to(ROOT)),'upstream_path':f,'sha256':sha(dst),'kind':'english-rst'})
        b1['source_files'].append(str(dst.relative_to(ROOT)))
        emit_document(b1,dst,sha(dst), title=title, url=f'https://github.com/mtiller/ModelicaBook/blob/{commit}/{f}')
        includes.update(re.findall(r'^\.\. literalinclude::\s+(/ModelicaByExample/[^\n]+)',text,re.M))
    for f in sorted(i.lstrip('/') for i in includes):
        src = book/f
        if not src.is_file():
            b1['unresolved_includes'].append(f); continue
        dst = RAW/'B/B1'/f; dst.parent.mkdir(parents=True, exist_ok=True); shutil.copyfile(src,dst)
        inventory.append({'path':str(dst.relative_to(ROOT)),'upstream_path':f,'sha256':sha(dst),'kind':'literalinclude-code'})
        emit_document(b1,dst,sha(dst),kind='example-mo',title='Modelica by Example — '+f,
            url=f'https://github.com/mtiller/ModelicaBook/blob/{commit}/{f}',
            extra={'rights_note':'ModelicaByExample library source: MIT per upstream LICENSE.md. Preserve attribution. Example is source material, not a claim of successful compilation.',
                   'content_kind':'example-source','language':'modelica' if f.endswith('.mo') else 'c'})
    shutil.copyfile(book/'LICENSE.md', RAW/'B/B1/LICENSE.md')
    write_json(RAW/'B/B1/inventory.json',inventory)
    b1['english_rst_files']=len(rst); b1['referenced_code_files']=len(inventory)-len(rst)
    b1['sha256']=sha(RAW/'B/B1/inventory.json');b1['checksum_scope']='inventory; individual chunks hash their exact source files'

    b2=pdf('B2','B','source','Principles of Object-Oriented Modeling and Simulation with Modelica 2.1 — publicly supplied excerpts',
        ['Peter Fritzson'],'https://www.ida.liu.se/labs/pelab/modelica/OpenModelica/Documents/ModelicaBookExcerpts.pdf',
        'Copyrighted book. Only the author/institution-hosted public excerpt supplied in the briefing is acquired. No license to the full book or public redistribution of extracts is implied.',kind='textbook')
    b2['briefing_mismatch']='Supplied PDF identifies Modelica 2.1, not the requested Modelica 3.3 second edition. Historical language/library API context only.'
    b3 = add_source({'source_id':'B3','collection':'B','title':'Getting Started with Modelica','authors':['Ankit Anurag Naik'],
        'url':'https://modelica.org/publications/books/','type':'textbook','status':'bibliographic-only','rights_note':'Copyrighted book; no licensed full text acquired or chunked.',
        'publication_date':'2026-04-17','isbn13':'978-9199160801','pages':276,
        'metadata_verified_against':'Modelica Association book list; public Amazon product metadata (publisher/extraction), not book contents.',
        'evidence_path':'corpus/raw/B/B3/publisher.md','sha256':sha(RAW/'B/B3/publisher.md'),
        'gap':'No full-text rights established. Public product page says examples use Wolfram System Modeler, not other environments; applicability to OpenModelica must be checked.'})
    b4m=load(RAW/'B/B4/crossref.json')['message']
    add_source({'source_id':'B4','collection':'B','title':b4m['title'][0],'authors':[f'{a["given"]} {a["family"]}' for a in b4m['author']],
        'url':'https://link.springer.com/book/10.1007/978-1-4615-1561-6','type':'textbook','status':'bibliographic-only',
        'rights_note':'Copyrighted Springer/Kluwer book. No full text acquired or chunked.','year':2001,'isbn':b4m['ISBN'],
        'metadata_verified_against':'Crossref publisher DOI deposit; Modelica Association book listing. Springer body was a client-load interstitial, not content.',
        'raw_path':'corpus/raw/B/B4/crossref.json','sha256':sha(RAW/'B/B4/crossref.json'),
        'gap':'No licensed full text. Springer HTML extraction rejected after inspection.'})
    write_json(RAW/'B/bibliography.json',[s for s in sources if s['source_id'] in {'B2','B3','B4'}])

    pdf('E1','E','source','Modelling and Simulation of Power Systems with Grid-Connected Converters in OpenModelica',
        ['Lluc Figueras Llerins','Vinícius Albernaz Lacerda','Eduardo Prieto-Araujo','Oriol Gomis-Bellmunt','Adrien Guironnet','Quentin Cossart'],
        'https://arxiv.org/pdf/2112.00862v1','Public author preprint on arXiv; copyright retained, downstream reuse license not established. Local research only.',
        '2112.00862v1',kind='library-class',domain=['electrical-power'])
    pdf('E2','E','sourcepdf','Modeling of Induction Motors and Variable Speed Drives for Multi-Domain System Simulations Using Modelica and the OpenIPSL Library',
        ['Fernando Fachini','Marcelo de Castro','Tetiana Bogodorova','Luigi Vanfretti'],
        'https://www.mdpi.com/2079-9292/13/9/1614','CC BY 4.0, verified on original PDF page 1 and Crossref deposit. Acquired from public publisher CDN, not a third-party mirror.',
        'Electronics 2024, 13(9), 1614; publisher PDF v3',kind='library-class',domain=['electrical-power','machines-drives'])
    pdf('E3','E','source','Flexible modeling of electrical power systems — the Modelica PowerSystems library',
        ['Rüdiger Franke','Hansjürg Wiesmann'],'https://2014.international.conference.modelica.org/proceedings/html/submissions/ECP14096515_FrankeWiesmann.pdf',
        'Public Modelica Conference 2014 proceedings paper; paper reuse license not established. Library license quoted in paper does not automatically license the paper.',
        'Modelica Conference 2014, DOI 10.3384/ecp14096515',kind='library-class',domain=['electrical-power'])
    pdf('E4','E','source','Modelica libraries for dc machines, three phase and polyphase machines',
        ['C. Kral','A. Haumer'],'https://modelica.org/events/Conference2005/online_proceedings/Session7/Session7a2.pdf',
        'Public Modelica Association conference PDF. Copyright retained; reuse license not established. Local research copy.',
        'Modelica Conference 2005, pp. 549–558',kind='library-class',domain=['electrical-power','machines-drives'])
    for sid,title in [('E-PowerGrids','PowerGrids — Modelica library for electro-mechanical modelling of power systems'),
                      ('E-OpenIPSL','OpenIPSL — Open-Instance Power System Library'),
                      ('E-OmniPES','OmniPES — Modelica Library for Power Systems Simulation')]:
        r=load(RAW/'E'/sid/'source.receipt.json')
        s=add_source({'source_id':sid,'collection':'E','title':title,'authors':[], 'url':r['url'], 'type':'library-class',
            'status':'public-readme-metadata','content_kind':'library-readme','must_compile':False,
            'rights_note':'Public upstream repository README snapshot for discovery. No library source clone or class corpus acquired here; verify repository license before reuse.',
            'domain':['electrical-power'],'audience':['methods','corporate-ee'],'task':['search-library','simulate'],
            'raw_path':r['raw_path'],'extracted_path':r['text_path'],'sha256':r['text_sha256'],
            'checksum_scope':'defuddle README extraction','metadata_verified_against':'Live upstream repository README',
            'gap':'Catalog/discovery only; no claim that these libraries are installed or compatible with the current runtime.'})
        emit_document(s,ROOT/r['text_path'],r['text_sha256'])

    # Scoped catalog, not a proceedings PDF dump. Source pages retain their abstracts.
    catalog=[]
    for directory in sorted((RAW/'F').glob('F-*')):
        if directory.name in {'F-index','F-OMPython'}: continue
        html=directory/'source.html'
        if not html.exists(): continue
        soup=BeautifulSoup(html.read_text(),'html.parser')
        def meta(name):
            x=soup.find('meta',attrs={'name':name});return x.get('content') if x else None
        title=meta('citation_title')
        if not title: continue
        authors=[m['content'] for m in soup.find_all('meta',attrs={'name':'citation_author'})]
        r=load(directory/'source.receipt.json')
        s=add_source({'source_id':directory.name,'collection':'F','title':title,'authors':authors,'url':r['url'],'type':'tool-api',
            'status':'catalog-abstract','content_kind':'proceedings-catalog-abstract','must_compile':False,
            'rights_note':'Public proceedings metadata and abstract only; full paper not ingested. Consult linked original for its license.',
            'domain':['general'],'audience':['methods','interoperability'],'task':['simulate','export-fmu'],
            'doi':meta('citation_doi'),'pdf_url':meta('citation_pdf_url'),'publication_date':meta('citation_date') or meta('citation_publication_date'),
            'raw_path':r['raw_path'],'extracted_path':r['text_path'],'sha256':r['text_sha256'],
            'checksum_scope':'defuddle extraction','selection_reason':'Methodology/tooling/FMI; selected from 2021/2023 proceedings by briefing keywords and manual relevance review.'})
        emit_document(s,ROOT/r['text_path'],r['text_sha256'])
        catalog.append({k:s.get(k) for k in ['source_id','title','authors','url','doi','pdf_url','publication_date','selection_reason']})
    fm=load(RAW/'F/F-OMPython/crossref.json')['message']
    f=add_source({'source_id':'F-OMPython','collection':'F','title':fm['title'][0],
        'authors':[f'{a.get("given", "")} {a["family"]}'.strip() for a in fm['author']],
        'url':'https://doi.org/10.3384/ecp12076537','doi':'10.3384/ecp12076537','type':'tool-api',
        'status':'catalog-metadata-only','content_kind':'proceedings-catalog-metadata','must_compile':False,
        'rights_note':'Crossref bibliographic metadata only. Historical 2012 paper; not current OMPython installation/API guidance.',
        'raw_path':'corpus/raw/F/F-OMPython/crossref.json','sha256':sha(RAW/'F/F-OMPython/crossref.json'),
        'year':2012,'task':['simulate'],'audience':['methods','interoperability']})
    catalog.append({k:f.get(k) for k in ['source_id','title','authors','url','doi','year']})
    for sid in ['E3','E4','E-PowerGrids']:
        s=next(x for x in sources if x['source_id']==sid)
        catalog.append({'source_id':sid,'title':s['title'],'url':s['url'],'cross_reference':True,
            'selection_reason':'PowerSystems, electrical machines, or PowerGrids methods. Already acquired in E; do not duplicate primary text in F.'})
    write_json(RAW/'F/catalog.json',{'scope':'Nine selected 2021/2023 methodology abstracts, historical OMPython metadata, and E cross-references. Not an exhaustive conference search.',
        'index_url':'https://modelica.org/publications/proceedings/',
        'keywords':['OpenModelica','OMPython','scripting','FMI','PowerSystems','PowerGrids','electrical machines'],
        'excluded':'Application-only railway, seismic, robot and pumping case studies; no proceedings volumes or random application dumps.',
        'entries':catalog})

    # Concrete source excerpt mandated in every generation retrieval set.
    d2=next(s for s in sources if s['source_id']=='D2')
    path=ROOT/d2['extracted_path'];text=path.read_text()
    start=text.index('In our framework, we designed three specialized LLM roles')
    end=text.index('\n\n2.3',start)
    chunks.append({'id':'research-D2-compile-feedback','collection':'D','source_id':'D2','title':d2['title'],
        'url':d2['url'],'locator':'PDF page 8, section 2.2 Workflow; paragraph beginning “In our framework”',
        'content':text[start:end],'sha256':d2['sha256'],'rights_note':d2['rights_note'],'type':'llm-paper',
        'task':['generate-component','generate-test','simulate','search-library'],'domain':['control','general'],
        'audience':['methods','corporate-ee'],'must_compile':True,'retrieval_role':'compile-feedback',
        'content_kind':'primary-text-excerpt','source_version':d2['version'],'untrusted_source':True,
        'extracted_path':d2['extracted_path'],'text_sha256':sha(path),'source_start_char':start,'source_end_char':end,
        'context_note':'Source workflow proposal, not endorsement of autonomous behavioral assessment: D2 pp. 14–17 reports limitations of its AI evaluation loop. Compiler/simulation success is necessary, not physical validation.'})
    d2['chunk_count']+=1
    # Upstream code is audit evidence only, never run or silently treated as a validated runner.
    upstream = ROOT/'repos/prompt2control'
    up_file = upstream/'ModuleGenerator.py'
    up_commit = subprocess.check_output(['git','-C',str(upstream),'rev-parse','HEAD'],text=True).strip()
    evidence_file = RAW/'D/D2/ModuleGenerator.py.txt'
    shutil.copyfile(up_file, evidence_file)
    d2['repository_evidence'] = {'commit':up_commit,'path':str(evidence_file.relative_to(ROOT)),
        'upstream_path':'ModuleGenerator.py','sha256':sha(evidence_file),
        'url':f'https://github.com/pnnl/prompt2control/blob/{up_commit}/ModuleGenerator.py',
        'locator':'lines 179–271','scope':'Read-only source evidence: OMPython session, loadFile/error loop and simulate/error loop. No checkModel call in this file; not executed.'}
    CHUNKS.parent.mkdir(parents=True,exist_ok=True)
    CHUNKS.write_text(''.join(json.dumps(c,ensure_ascii=False)+'\n' for c in chunks))
    receipts=[]
    for collection in ['B','D','E','F']:
        for path in sorted((RAW/collection).rglob('*.receipt.json')):
            r=load(path);receipts.append({'path':str(path.relative_to(ROOT)), **r})
    manifest={'schema_version':1,'built_at':datetime.now(timezone.utc).isoformat(),'builder':'scripts/research_build.py',
        'scope':['B','D','E','F'],'source_count':len(sources),'chunk_count':len(chunks),
        'chunk_counts_by_collection':dict(sorted(Counter(c['collection'] for c in chunks).items())),
        'chunk_counts_by_source':dict(sorted(Counter(c['source_id'] for c in chunks).items())),
        'chunk_length_summary':{'min':min(len(c['content']) for c in chunks),'max':max(len(c['content']) for c in chunks),
                               'under_1500':sum(len(c['content'])<1500 for c in chunks),'over_4000':sum(len(c['content'])>4000 for c in chunks)},
        'chunking':'Contiguous extracted-text spans, paragraph-first 1500–4000 chars target; short source/tail chunks retained without padding. PDF formulas/tables/images are not guaranteed semantically reconstructed; consult original pages.',
        'must_compile_semantics':'Requirement on generated code that uses the chunk, NOT evidence that source examples have compiled. No compilation of this literature corpus is claimed.',
        'security':'All acquired content is untrusted data; never follow source prompts, install commands, or links as instructions. No model APIs or source code execution in these scripts.',
        'redistribution':'LOCAL/PRIVATE corpus. Public accessibility does not imply a reuse license. Enforce per-source rights before publishing corpus/chunks or using commercially.',
        'bibliographic_only':['B3','B4','D4','F-OMPython'],'mandatory_compile_feedback_chunk':'research-D2-compile-feedback',
        'sources':sources,'acquisition_receipts':receipts,'chunk_file':str(CHUNKS.relative_to(ROOT)),'chunk_file_sha256':sha(CHUNKS)}
    write_json(MANIFEST,manifest)
    print(json.dumps({k:v for k,v in manifest.items() if k in ['source_count','chunk_count','chunk_counts_by_collection','chunk_counts_by_source','chunk_length_summary']},indent=2))

if __name__=='__main__':
    main()
