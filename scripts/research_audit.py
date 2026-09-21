#!/usr/bin/env python3
"""Generate the evidence-bounded research audit and citation ledger.
Uses Hermes' installed stdlib citation verifier, not an LLM or external API.
"""
from pathlib import Path
import json
import re
import subprocess
import sys
from collections import Counter

ROOT = Path(__file__).resolve().parents[1]
LEDGER = ROOT/'corpus/raw/D/citation-ledger.json'
CITER = Path.home()/'.hermes/skills/research/grounded-citations/scripts/sources.py'
REPORT = ROOT/'docs/RESEARCH_AUDIT.md'
M = json.loads((ROOT/'corpus/manifests/research.json').read_text())
S = {s['source_id']:s for s in M['sources']}


def cite(*args):
    p = subprocess.run([sys.executable,str(CITER),'--ledger',str(LEDGER),*args],capture_output=True,text=True)
    if p.returncode:
        raise RuntimeError(p.stdout+p.stderr)
    return p.stdout


def quote_block(n, path, needle):
    text = path.read_text()
    start = text.index(needle)
    end = text.find('\n\n',start)
    if end < 0: end = len(text)
    quote = text[start:end]
    cite('quote',str(n),'--text',quote,'--from',str(path))


def main():
    cite('reset')
    ids = {}
    for s in M['sources']:
        citation_url = s['url']
        if s['source_id'] in {'D4','B4','F-OMPython'}:
            citation_url = json.loads((ROOT/Path(s['raw_path']).with_name('crossref.receipt.json')).read_text())['url']
        result=cite('add',citation_url,'--title',s['title'])
        match = re.search(r'\[(\d+)\]',result)
        assert match, result
        n=int(match.group(1)); ids[s['source_id']]=n
        if s['source_id']=='B1':
            path=ROOT/'corpus/raw/B/B1/LICENSE.md'
        elif s.get('evidence_path'):
            path=ROOT/s['evidence_path']
        else:
            path=ROOT/s.get('extracted_path',s.get('raw_path'))
        text=path.read_text()
        # Every source gets actual source bytes as evidence, then claim-specific blocks below.
        excerpt = s['title'] if path.suffix == '.json' else text[:min(400,len(text))]
        cite('quote',str(n),'--text',excerpt,'--from',str(path))
    extras=[('B1-license','https://github.com/mtiller/ModelicaBook/blob/'+S['B1']['version']+'/LICENSE.md','ModelicaBook license',ROOT/'corpus/raw/B/B1/LICENSE.md'),
        ('B3-product','https://www.amazon.com/Getting-Started-Modelica-Language-Modeling/dp/9199160803/','Getting Started with Modelica — public product metadata',ROOT/'corpus/raw/B/B3/publisher.md'),
        ('D2-code',S['D2']['repository_evidence']['url'],'prompt2control ModuleGenerator.py (pinned source)',ROOT/S['D2']['repository_evidence']['path']),
        ('F-index','https://modelica.org/publications/proceedings/','Modelica Conference Proceedings index',ROOT/'corpus/raw/F/F-index/source.md')]
    for key,url,title,path in extras:
        result=cite('add',url,'--title',title);n=int(re.search(r'\[(\d+)\]',result).group(1));ids[key]=n
        cite('quote',str(n),'--text',path.read_text()[:400],'--from',str(path))
    evidence = [
        ('D1','corpus/raw/D/D1/source.txt','General Applicability.'),
        ('D1','corpus/raw/D/D1/source.txt','4.4\nFeedback-Driven Refinement'),
        ('D1-v1','corpus/raw/D/D1/v1.txt','Modelica is a widely adopted language'),
        ('D2','corpus/raw/D/D2/source.txt','In our framework, we designed three specialized LLM roles'),
        ('D2','corpus/raw/D/D2/source.txt','We initially explored an RAG pipeline'),
        ('D2','corpus/raw/D/D2/source.txt','The evaluation results demonstrate'),
        ('D3','corpus/raw/D/D3/source.txt','We observe that overall'),
        ('D5','corpus/raw/D/D5/source.txt','Abstract Large language models'),
        ('D6','corpus/raw/D/D6/source.md','The result was not perfect.'),
        ('B1-license','corpus/raw/B/B1/LICENSE.md','But a license is NOT granted'),
        ('B1-license','corpus/raw/B/B1/LICENSE.md','The source code of the'),
        ('B3-product','corpus/raw/B/B3/publisher.md','A note on tools:'),
        ('E-PowerGrids','corpus/raw/E/E-PowerGrids/source.md','PowerGrids was developed and tested'),
        ('E-OpenIPSL','corpus/raw/E/E-OpenIPSL/source.md','OpenIPSL is compatible'),
        ('E-OmniPES','corpus/raw/E/E-OmniPES/source.md','At the present stage'),
        ('D2-code','corpus/raw/D/D2/ModuleGenerator.py.txt','    def check_and_fix_model'),
    ]
    for key,relative,needle in evidence:
        quote_block(ids[key],ROOT/relative,needle)
    def ref(key):return f'[{ids[key]}]'
    counts=M['chunk_counts_by_collection']
    pdfs=[s for s in M['sources'] if s.get('status') in {'full-text','public-excerpt-only'}]
    pages=sum(s['pages'] for s in pdfs)
    files={s['sha256'] for s in pdfs}
    source_counts=Counter(s['collection'] for s in M['sources'])
    d_text='\n'.join((ROOT/s['extracted_path']).read_text() for s in M['sources'] if s['collection']=='D' and s.get('extracted_path'))
    routing_hits={name:len(re.findall(re.escape(name),d_text,re.I)) for name in ['Fable 5.1','GPT Astra']}
    stats={'source_count':M['source_count'],'chunk_count':M['chunk_count'],'distinct_pdf_count':len(files),'pdf_pages':pages,
           'book_english_rst_files':S['B1']['english_rst_files'],'book_referenced_code_files':S['B1']['referenced_code_files'],
           'f_catalog_entries':len(json.loads((ROOT/'corpus/raw/F/catalog.json').read_text())['entries']),
           'routing_name_occurrences_in_acquired_D_text':routing_hits}
    (ROOT/'corpus/raw/D/audit-evidence.json').write_text(json.dumps({'stats':stats,'citation_ids':ids,'claim_specific_quotes':evidence,
       'D4_alternate_search':{'scope':'Bounded public search, not exhaustive','queries':['"Automating Model Transformation from Modelica to SysML v2"','"Automating Model Transformation" "Modelica" site:polimi.it','"Automating Model Transformation" "Modelica" site:uc3m.es'],
                            'observed':'No matching institutional manuscript found. UC3M research-stay record and unrelated Modelica/Pyomo or transformation papers were not treated as D4.',
                            'institution_record_attempt':'corpus/raw/D/D4/institution.receipt.json'}},ensure_ascii=False,indent=2)+'\n')
    report=f'''# Research acquisition and claim audit

## Scope and observed deliverable

This audit covers the briefing's literature/pedagogy/domain collections B, D, E and F, for compiler-grounded dynamic-model generation. It separates original-source statements from project recommendations; it is not an evaluation of Fable 5.1 or GPT Astra, an engineering certification, or a claim to replace licensed power-system tools.

Acquisition timestamps are preserved in individual receipts; the build timestamp is `{M['built_at']}`. Sources are untrusted data, including papers containing system/user prompt examples. No source prompts or examples were executed, no accounts/paywalls were bypassed, no third-party installers were run, and no model inference API was called by the acquisition/build/audit scripts.

| Collection | Logical source records | Retrieval chunks | Acquired scope |
|---|---:|---:|---|
| B | {source_counts['B']} | {counts['B']} | Full English narrative source, referenced examples, supplied Fritzson excerpt; B3/B4 bibliography only |
| D | {source_counts['D']} | {counts['D']} | D1 v1 + v2, D2, D3, D5 full PDFs, D6 article; D4 metadata and explicit gap |
| E | {source_counts['E']} | {counts['E']} | Four methods PDFs and three upstream discovery README snapshots |
| F | {source_counts['F']} | {counts['F']} | Nine selected proceedings abstracts plus historical OMPython metadata |
| **Total** | **{M['source_count']}** | **{M['chunk_count']}** | Counts computed from the manifest and JSONL |

There are **{len(files)} distinct PDF originals covering {pages} physical PDF pages**; the second download of D1 v2 verifies its version pin and is not counted as another original. B1 contains **{S['B1']['english_rst_files']} tracked English RST files** and **{S['B1']['referenced_code_files']} uniquely referenced code files**, with **{len(S['B1']['unresolved_includes'])} unresolved literal includes**. F's bounded catalog contains **{stats['f_catalog_entries']} entries**, including E cross-references rather than duplicate papers. These are local inventory measurements, not publisher claims.

## Identity, provenance and claim audit

Confidence below describes what the acquired evidence supports, not independent reproduction of a paper's experiments.

| Item / briefing claim | Observed original and locator | Verdict / confidence |
|---|---|---|
| D1: ModiGen uses SFT, GraphRAG, feedback, component and test-case generation | v1, title/abstract and methods. Authors: Jiahui Xiang, Tong Ye, Peiyu Liu, Yinan Zhang, Wenhai Wang. {ref('D1-v1')} | **Supported for v1**, not a version-neutral description. High identity confidence; experimental results not reproduced here. |
| D1 version drift | v2 PDF p.1 calls itself *ModiGen: A Large Language Model-Based Framework for Modelica Component Generation in Multi-Domain Systems*; arXiv HTML metadata/PDF properties retain the earlier *Workflow for Multi-Task...* title. v2 pp.3,6–7 describe component evaluation, structural retrieval and refinement. {ref('D1')} {ref('D1-v1')} | **Material mismatch.** Both PDFs retained; latest file was re-downloaded as `2503.18460v2` and byte hashes matched. Use the visible original title, not stale metadata. |
| D1 compiler/simulation feedback | v2 §4.4, PDF pp.6–7, preloads dependencies and returns precise diagnostics with original prompt and current component; §3.2 p.3 also checks trajectories and uses human inspection. {ref('D1')} | **Supported, high.** Successful compilation/simulation alone is not the paper's functional-validity criterion. |
| D2 names and scope | Title page identifies Hanlong Wan, Xing Lu, Yan Chen, Karthik Devaprasad and Laura Hinkle, PNNL. Experiments address four logic tasks and five building-control tasks. {ref('D2')} | **Supported, high.** PDF document-properties author `Patel, Viral K.` is not the byline and was not used. Do not extrapolate to all electrical or Modelica tasks. |
| D2: naive RAG confused `And` and `Or`; exact lookup helped | §3.2.1 pp.13–14 and §4.2 p.15 describe semantic-overlap mismatches and pulling exact existing module names. {ref('D2')} | **Supported within this experiment.** Not proof that all semantic retrieval is inferior, or that exact names alone establish behavioral correctness. |
| D2: Claude Sonnet 4 stronger than GPT-4o | pp.11–15 report zero-shot failures and strong results with scaffolds/library context; later control-module experiments focus on Claude. {ref('D2')} | **Scoped support.** Model, prompt and task conditions differ; not a universal or future-model ranking. |
| D2: reported 83% and productivity gains | Abstract/discussion report 83% best-case success and 40–60% savings. §3.2.3 p.14 gives expert baseline estimates 6–8 and 8–12 hours, while discussion/conclusion quote 10–20 to 4–6 hours; Table 3 and prose also deserve careful reconciliation before reusing absolute failure claims. {ref('D2')} | **Report as authors' figures, not independently established constants.** Internal reporting caveats retained; not used to predict project ROI. |
| D2: OMPython compile loop | Paper §2.2 pp.7–8 says OpenModelica API. Pinned `ModuleGenerator.py` imports/creates `OMCSessionZMQ`, calls `loadFile`/`getErrorString`, and later `simulate`/`getErrorString` (lines 179–271). {ref('D2')} {ref('D2-code')} | **Supported by paper + repository, with caveat:** `check_and_fix_model` labels successful loading as compilation and does not call `checkModel`. Do not copy that weaker gate as a validated runner. Repository code was read, not executed. |
| D3: fine-tuning helps in-domain but GPT-4o generalizes better | Title page and §§3.1–3.2 pp.4–5. Authors: Sophia Rupprecht, Yassine Hounat, Monisha Kumar, Giacomo Lastrucci, Artur M. Schweidtmann. Evaluation manually assesses syntax/semantics and discusses Dymola unit checks. {ref('D3')} | **Supported for reported reactor scenarios, high.** Not evidence that every LLM–Modelica paper uses an OpenModelica closed loop. |
| D4: Modelica→SysML v2 agents | Crossref DOI deposit verifies title *Automating Model Transformation from Modelica to SysML v2 with LLM-based Agents* and authors Eduardo Cibrián, José Francisco Olivert Iserte, Francesco Casella, Mario García Rodríguez, Jose María Alvarez-Rodríguez, Juan Llorens. {ref('D4')} | **Bibliography verified; methods unverified.** SSRN returned 403; bounded title/author-institution searches found no matching public PDF. No fabricated summary chunks. |
| D5: prompting/RAG/LoRA pitfalls | Philippe J. Giabbanelli, title/abstract p.1, discusses non-determinism, attention limits, knowledge augmentation and evaluation. {ref('D5')} | **Supported, high.** General M&S guidance, not a Modelica benchmark or proof that low temperature ensures deterministic output. |
| D6: GPT-4 mishandled `der()` | Lixiang Li's 2026-03-18 Modelon article, “Early Signals” paragraph, says a 2023 model used finite differences instead of `der()` and was corrected by a follow-up prompt. {ref('D6')} | **Supported as a vendor anecdote**, not a controlled benchmark. It says the draft was syntactically correct; the problem was modeling/operator use, not necessarily a syntax error. |
| B1: free book means reusable corpus | Repository license distinguishes HTML output (CC BY-NC-ND 3.0) from the source/derived works (redistribution not granted); ModelicaByExample code is separately MIT. {ref('B1-license')} | **Important rights qualification.** Full English text is acquired for this local/private corpus, not licensed for public/commercial redistribution. |
| B2: supplied excerpt is from Modelica 3.3 edition | PDF p.1 explicitly says *Principles of Object-Oriented Modeling and Simulation with Modelica 2.1*, Peter Fritzson. {ref('B2')} | **Mismatch, high.** Retain supplied excerpt only, label historical version. Do not silently relabel as 3.3 or ingest the complete book. |
| B3/B4 books | Association list confirms titles; B3 public product page supplies 2026-04-17, 276 pages, ISBN and System Modeler-only workflows; B4 Crossref verifies Michael Tiller, 2001 and DOI. {ref('B3')} {ref('B3-product')} {ref('B4')} | **Bibliographic only.** No full book contents chunked. B4 Springer page was an HTTP-200 client-load interstitial, rejected despite extractor exit 0. |
| E1: OpenModelica vs Simulink converter-heavy transients | Figueras Llerins et al., PDF p.1 and full methods/results compare a modeled transmission system in both environments. {ref('E1')} | **Supported within the study.** Not general equivalence, regulatory certification, or replacement for proprietary tools. |
| E2: induction motors/VSDs and multi-domain coupling | Fachini, de Castro, Bogodorova and Vanfretti, *Electronics* 2024, 13(9), 1614; title/abstract p.1 and full PDF. {ref('E2')} | **Supported.** Publisher HTML/PDF gateway returned 403; official public CDN PDF succeeded. Paper literally says “Modelica v4.0.0”; do not promote this to a Modelica language-specification version. |
| E3/E4: library methods | Franke/Wiesmann's 2014 PowerSystems design paper describes replaceable PhaseSystem; C. Kral/A. Haumer's 2005 paper describes DC/three-phase/polyphase machine libraries. {ref('E3')} {ref('E4')} | **Supported historical methods.** Do not use their legacy class names as current installed-library truth. |
| PowerGrids/OpenIPSL/OmniPES | Upstream README snapshots describe phasor/electromechanical modeling, compatibility caveats, and steady-state/transient-stability frameworks respectively. {ref('E-PowerGrids')} {ref('E-OpenIPSL')} {ref('E-OmniPES')} | **Discovery metadata only.** Not installed, cloned or runtime-tested here. OpenIPSL describes Dymola as primary and OpenModelica as largely compatible. |
| F proceedings index completeness | Association index repeats `10.3384/ecp218` under both international 2025 and Asian 2024 labels. {ref('F-index')} | **Catalog ambiguity, not silently repaired.** This corpus uses individually verified 2021/2023 article pages and bounded historical references; no exhaustive long-tail coverage claimed. |

## Advisory interpretation — not quoted findings

- **Recommended local generation gate:** exact installed class/connector lookup → draft `.mo` plus `.mos`/Python → load/check → simulate → inspect result artifacts and compare task-specific physical expectations. The final acceptance gate should be stricter than a `loadFile`/error-string-only test.
- Require compiler/simulation evidence for **every** generating model. The briefing's Fable-primary/Astra-draft-only split is a project preference, not a result established by the acquired papers. Literal occurrences in the acquired D texts: `{json.dumps(routing_hits)}`. No capability ranking of either model was measured here.
- A D1/D2 error-loop excerpt, matching specification section, exact library headers and API recipe form a defensible retrieval design. This is a project synthesis inspired by the papers, not a tested “PNNL retrieval recipe” reproduced verbatim.
- Compiler acceptance is necessary for executable-model delivery but does not establish units, conservation, parameter suitability, numerical robustness or behavioral validity for the user's intended system. Historical example sources still require current-toolchain validation.

## Retrieval/provenance contract

- Main JSONL: `corpus/chunks/research.jsonl`; machine manifest: `corpus/manifests/research.json`.
- Required error-loop record: **`research-D2-compile-feedback`**, original PDF p.8 §2.2, includes explicit compilation and simulation loops. Its `context_note` points to the paper's failed/limited behavioral AI evaluation; use the note, not just the excerpt.
- Every chunk carries the requested tags, a `research-` ID, source URL/version, source checksum, rights note, locator, exact extracted-text offsets and text checksum. PDF chunks hash the original PDF; HTML chunks hash the actual retained extraction because a separate HTML fetch can differ. Each receipt also hashes the raw response where available.
- Paragraph-first target is 1,500–4,000 characters. Actual range is {M['chunk_length_summary']['min']}–{M['chunk_length_summary']['max']}; {M['chunk_length_summary']['under_1500']} short file/tail chunks are deliberately kept without padding or unrelated joins. The explicit compile-feedback record overlaps full-paper chunks by design.
- B1 narrative includes remain source directives; referenced `.mo`/C files are separately retained/chunked once. No translation/build/retired duplicates. The two referenced C files use the allowed `example-mo` retrieval family with `language: c`, not a claim that C is Modelica.
- `must_compile` is a requirement for generated artifacts using that material, **not** evidence that the literature examples compiled. E methods use the briefing's closest allowed tag, `library-class`; the manifest identifies them as papers by title/version/status.
- PyMuPDF preserves source-block order for multi-column documents; extracted equations, tables, figures and hyphenation may still need consulting the PDF. B2 physical page 12 was empty in the text layer, had no images/drawings, and rendered blank; it is recorded as a verified blank page rather than silently omitted or invented.
- **Do not publish this corpus as-is.** Public access is not a blanket redistribution license. B1 narrative source, B2 excerpt, arXiv distribution-only works and D6 have restrictions; D5 is CC BY-NC-ND 4.0. D1 v2's PDF states CC BY 4.0 while its arXiv landing page links a non-exclusive distribution notice, so preserve both. E2's PDF explicitly states CC BY 4.0.

## Selected source anchors

The B1 snapshot retains the English authoring source at its pinned repository commit, with the separately audited license boundary described above.{ref('B1')}

The F selection includes the FMI 3.0 clock/scheduling overview, the LOTAR analytical-mBSE archival paper, and the OpenModelica.jl compiler-framework article; only their public metadata/abstract pages were ingested.{ref('F-179')}{ref('F-181')}{ref('F-186')}

It also includes cloud-native simulation-as-a-service, the OpenModelica–Matlab interface, and layered FMI standards, again as public abstracts rather than full papers.{ref('F-217')}{ref('F-937')}{ref('F-947')}

The remaining selected abstracts address a preCICE–FMI runner, secure black-box model exchange, and hybrid power systems with SSP/FMI.{ref('F-958')}{ref('F-959')}{ref('F-985')}

The historical OMPython/PySimulator reference is a bibliographic discovery entry, not current installation or API guidance.{ref('F-OMPython')}

## Gaps and boundaries

D4 full text remains missing. B3/B4 are deliberately bibliography-only; B2 does not supply the requested 3.3 edition. Image-only diagram content is retained in PDFs but not converted into textual facts. The F catalog is intentionally bounded, not a conference sweep. No paper benchmark was rerun and no example library was compiled by this research task. Live compiler/runtime acceptance belongs to the separately owned runtime work, not this audit.

## Reproduce and verify

```sh
cd /home/nathan/openmodelica-ai
.venv/bin/python scripts/research_build.py
.venv/bin/python -m pytest tests/test_research_corpus.py -q
.venv/bin/python scripts/research_audit.py
```

The offline tests check required source/gap states, all tag enums, unique IDs and programmatic totals, exact per-chunk source spans and SHA-256 values, complete retained-text coverage, PDF page accounting, English/include-only book selection, version-pin identity, interstitial rejection, the mandatory compile-feedback excerpt and bounded F selection. Citation verification checks the generated Sources mapping and attached exact-source evidence. Test logs and citation verifier output are retained under `corpus/raw/D/`.
'''
    REPORT.parent.mkdir(parents=True,exist_ok=True)
    REPORT.write_text(report)
    cite('render','--replace-in',str(REPORT))
    result=cite('verify',str(REPORT),'--strict','--evidence')
    (ROOT/'corpus/raw/D/citation-verification.txt').write_text(result)
    print(json.dumps(stats,ensure_ascii=False,indent=2))
    print(result)

if __name__=='__main__':
    main()
