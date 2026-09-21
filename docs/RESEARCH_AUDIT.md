# Research acquisition and claim audit

## Scope and observed deliverable

This audit covers the briefing's literature/pedagogy/domain collections B, D, E and F, for compiler-grounded dynamic-model generation. It separates original-source statements from project recommendations; it is not an evaluation of Fable 5.1 or GPT Astra, an engineering certification, or a claim to replace licensed power-system tools.

Acquisition timestamps are preserved in individual receipts; the build timestamp is `2026-09-21T03:49:28.396774+00:00`. Sources are untrusted data, including papers containing system/user prompt examples. No source prompts or examples were executed, no accounts/paywalls were bypassed, no third-party installers were run, and no model inference API was called by the acquisition/build/audit scripts.

| Collection | Logical source records | Retrieval chunks | Acquired scope |
|---|---:|---:|---|
| B | 4 | 567 | Full English narrative source, referenced examples, supplied Fritzson excerpt; B3/B4 bibliography only |
| D | 7 | 152 | D1 v1 + v2, D2, D3, D5 full PDFs, D6 article; D4 metadata and explicit gap |
| E | 7 | 95 | Four methods PDFs and three upstream discovery README snapshots |
| F | 10 | 9 | Nine selected proceedings abstracts plus historical OMPython metadata |
| **Total** | **28** | **823** | Counts computed from the manifest and JSONL |

There are **10 distinct PDF originals covering 252 physical PDF pages**; the second download of D1 v2 verifies its version pin and is not counted as another original. B1 contains **90 tracked English RST files** and **199 uniquely referenced code files**, with **0 unresolved literal includes**. F's bounded catalog contains **13 entries**, including E cross-references rather than duplicate papers. These are local inventory measurements, not publisher claims.

## Identity, provenance and claim audit

Confidence below describes what the acquired evidence supports, not independent reproduction of a paper's experiments.

| Item / briefing claim | Observed original and locator | Verdict / confidence |
|---|---|---|
| D1: ModiGen uses SFT, GraphRAG, feedback, component and test-case generation | v1, title/abstract and methods. Authors: Jiahui Xiang, Tong Ye, Peiyu Liu, Yinan Zhang, Wenhai Wang. [2] | **Supported for v1**, not a version-neutral description. High identity confidence; experimental results not reproduced here. |
| D1 version drift | v2 PDF p.1 calls itself *ModiGen: A Large Language Model-Based Framework for Modelica Component Generation in Multi-Domain Systems*; arXiv HTML metadata/PDF properties retain the earlier *Workflow for Multi-Task...* title. v2 pp.3,6–7 describe component evaluation, structural retrieval and refinement. [1] [2] | **Material mismatch.** Both PDFs retained; latest file was re-downloaded as `2503.18460v2` and byte hashes matched. Use the visible original title, not stale metadata. |
| D1 compiler/simulation feedback | v2 §4.4, PDF pp.6–7, preloads dependencies and returns precise diagnostics with original prompt and current component; §3.2 p.3 also checks trajectories and uses human inspection. [1] | **Supported, high.** Successful compilation/simulation alone is not the paper's functional-validity criterion. |
| D2 names and scope | Title page identifies Hanlong Wan, Xing Lu, Yan Chen, Karthik Devaprasad and Laura Hinkle, PNNL. Experiments address four logic tasks and five building-control tasks. [3] | **Supported, high.** PDF document-properties author `Patel, Viral K.` is not the byline and was not used. Do not extrapolate to all electrical or Modelica tasks. |
| D2: naive RAG confused `And` and `Or`; exact lookup helped | §3.2.1 pp.13–14 and §4.2 p.15 describe semantic-overlap mismatches and pulling exact existing module names. [3] | **Supported within this experiment.** Not proof that all semantic retrieval is inferior, or that exact names alone establish behavioral correctness. |
| D2: Claude Sonnet 4 stronger than GPT-4o | pp.11–15 report zero-shot failures and strong results with scaffolds/library context; later control-module experiments focus on Claude. [3] | **Scoped support.** Model, prompt and task conditions differ; not a universal or future-model ranking. |
| D2: reported 83% and productivity gains | Abstract/discussion report 83% best-case success and 40–60% savings. §3.2.3 p.14 gives expert baseline estimates 6–8 and 8–12 hours, while discussion/conclusion quote 10–20 to 4–6 hours; Table 3 and prose also deserve careful reconciliation before reusing absolute failure claims. [3] | **Report as authors' figures, not independently established constants.** Internal reporting caveats retained; not used to predict project ROI. |
| D2: OMPython compile loop | Paper §2.2 pp.7–8 says OpenModelica API. Pinned `ModuleGenerator.py` imports/creates `OMCSessionZMQ`, calls `loadFile`/`getErrorString`, and later `simulate`/`getErrorString` (lines 179–271). [3] [31] | **Supported by paper + repository, with caveat:** `check_and_fix_model` labels successful loading as compilation and does not call `checkModel`. Do not copy that weaker gate as a validated runner. Repository code was read, not executed. |
| D3: fine-tuning helps in-domain but GPT-4o generalizes better | Title page and §§3.1–3.2 pp.4–5. Authors: Sophia Rupprecht, Yassine Hounat, Monisha Kumar, Giacomo Lastrucci, Artur M. Schweidtmann. Evaluation manually assesses syntax/semantics and discusses Dymola unit checks. [4] | **Supported for reported reactor scenarios, high.** Not evidence that every LLM–Modelica paper uses an OpenModelica closed loop. |
| D4: Modelica→SysML v2 agents | Crossref DOI deposit verifies title *Automating Model Transformation from Modelica to SysML v2 with LLM-based Agents* and authors Eduardo Cibrián, José Francisco Olivert Iserte, Francesco Casella, Mario García Rodríguez, Jose María Alvarez-Rodríguez, Juan Llorens. [6] | **Bibliography verified; methods unverified.** SSRN returned 403; bounded title/author-institution searches found no matching public PDF. No fabricated summary chunks. |
| D5: prompting/RAG/LoRA pitfalls | Philippe J. Giabbanelli, title/abstract p.1, discusses non-determinism, attention limits, knowledge augmentation and evaluation. [5] | **Supported, high.** General M&S guidance, not a Modelica benchmark or proof that low temperature ensures deterministic output. |
| D6: GPT-4 mishandled `der()` | Lixiang Li's 2026-03-18 Modelon article, “Early Signals” paragraph, says a 2023 model used finite differences instead of `der()` and was corrected by a follow-up prompt. [7] | **Supported as a vendor anecdote**, not a controlled benchmark. It says the draft was syntactically correct; the problem was modeling/operator use, not necessarily a syntax error. |
| B1: free book means reusable corpus | Repository license distinguishes HTML output (CC BY-NC-ND 3.0) from the source/derived works (redistribution not granted); ModelicaByExample code is separately MIT. [29] | **Important rights qualification.** Full English text is acquired for this local/private corpus, not licensed for public/commercial redistribution. |
| B2: supplied excerpt is from Modelica 3.3 edition | PDF p.1 explicitly says *Principles of Object-Oriented Modeling and Simulation with Modelica 2.1*, Peter Fritzson. [9] | **Mismatch, high.** Retain supplied excerpt only, label historical version. Do not silently relabel as 3.3 or ingest the complete book. |
| B3/B4 books | Association list confirms titles; B3 public product page supplies 2026-04-17, 276 pages, ISBN and System Modeler-only workflows; B4 Crossref verifies Michael Tiller, 2001 and DOI. [10] [30] [11] | **Bibliographic only.** No full book contents chunked. B4 Springer page was an HTTP-200 client-load interstitial, rejected despite extractor exit 0. |
| E1: OpenModelica vs Simulink converter-heavy transients | Figueras Llerins et al., PDF p.1 and full methods/results compare a modeled transmission system in both environments. [12] | **Supported within the study.** Not general equivalence, regulatory certification, or replacement for proprietary tools. |
| E2: induction motors/VSDs and multi-domain coupling | Fachini, de Castro, Bogodorova and Vanfretti, *Electronics* 2024, 13(9), 1614; title/abstract p.1 and full PDF. [13] | **Supported.** Publisher HTML/PDF gateway returned 403; official public CDN PDF succeeded. Paper literally says “Modelica v4.0.0”; do not promote this to a Modelica language-specification version. |
| E3/E4: library methods | Franke/Wiesmann's 2014 PowerSystems design paper describes replaceable PhaseSystem; C. Kral/A. Haumer's 2005 paper describes DC/three-phase/polyphase machine libraries. [14] [15] | **Supported historical methods.** Do not use their legacy class names as current installed-library truth. |
| PowerGrids/OpenIPSL/OmniPES | Upstream README snapshots describe phasor/electromechanical modeling, compatibility caveats, and steady-state/transient-stability frameworks respectively. [16] [17] [18] | **Discovery metadata only.** Not installed, cloned or runtime-tested here. OpenIPSL describes Dymola as primary and OpenModelica as largely compatible. |
| F proceedings index completeness | Association index repeats `10.3384/ecp218` under both international 2025 and Asian 2024 labels. [32] | **Catalog ambiguity, not silently repaired.** This corpus uses individually verified 2021/2023 article pages and bounded historical references; no exhaustive long-tail coverage claimed. |

## Advisory interpretation — not quoted findings

- **Recommended local generation gate:** exact installed class/connector lookup → draft `.mo` plus `.mos`/Python → load/check → simulate → inspect result artifacts and compare task-specific physical expectations. The final acceptance gate should be stricter than a `loadFile`/error-string-only test.
- Require compiler/simulation evidence for **every** generating model. The briefing's Fable-primary/Astra-draft-only split is a project preference, not a result established by the acquired papers. Literal occurrences in the acquired D texts: `{"Fable 5.1": 0, "GPT Astra": 0}`. No capability ranking of either model was measured here.
- A D1/D2 error-loop excerpt, matching specification section, exact library headers and API recipe form a defensible retrieval design. This is a project synthesis inspired by the papers, not a tested “PNNL retrieval recipe” reproduced verbatim.
- Compiler acceptance is necessary for executable-model delivery but does not establish units, conservation, parameter suitability, numerical robustness or behavioral validity for the user's intended system. Historical example sources still require current-toolchain validation.

## Retrieval/provenance contract

- Main JSONL: `corpus/chunks/research.jsonl`; machine manifest: `corpus/manifests/research.json`.
- Required error-loop record: **`research-D2-compile-feedback`**, original PDF p.8 §2.2, includes explicit compilation and simulation loops. Its `context_note` points to the paper's failed/limited behavioral AI evaluation; use the note, not just the excerpt.
- Every chunk carries the requested tags, a `research-` ID, source URL/version, source checksum, rights note, locator, exact extracted-text offsets and text checksum. PDF chunks hash the original PDF; HTML chunks hash the actual retained extraction because a separate HTML fetch can differ. Each receipt also hashes the raw response where available.
- Paragraph-first target is 1,500–4,000 characters. Actual range is 96–3999; 180 short file/tail chunks are deliberately kept without padding or unrelated joins. The explicit compile-feedback record overlaps full-paper chunks by design.
- B1 narrative includes remain source directives; referenced `.mo`/C files are separately retained/chunked once. No translation/build/retired duplicates. The two referenced C files use the allowed `example-mo` retrieval family with `language: c`, not a claim that C is Modelica.
- `must_compile` is a requirement for generated artifacts using that material, **not** evidence that the literature examples compiled. E methods use the briefing's closest allowed tag, `library-class`; the manifest identifies them as papers by title/version/status.
- PyMuPDF preserves source-block order for multi-column documents; extracted equations, tables, figures and hyphenation may still need consulting the PDF. B2 physical page 12 was empty in the text layer, had no images/drawings, and rendered blank; it is recorded as a verified blank page rather than silently omitted or invented.
- **Do not publish this corpus as-is.** Public access is not a blanket redistribution license. B1 narrative source, B2 excerpt, arXiv distribution-only works and D6 have restrictions; D5 is CC BY-NC-ND 4.0. D1 v2's PDF states CC BY 4.0 while its arXiv landing page links a non-exclusive distribution notice, so preserve both. E2's PDF explicitly states CC BY 4.0.

## Selected source anchors

The B1 snapshot retains the English authoring source at its pinned repository commit, with the separately audited license boundary described above.[8]

The F selection includes the FMI 3.0 clock/scheduling overview, the LOTAR analytical-mBSE archival paper, and the OpenModelica.jl compiler-framework article; only their public metadata/abstract pages were ingested.[19][20][21]

It also includes cloud-native simulation-as-a-service, the OpenModelica–Matlab interface, and layered FMI standards, again as public abstracts rather than full papers.[22][23][24]

The remaining selected abstracts address a preCICE–FMI runner, secure black-box model exchange, and hybrid power systems with SSP/FMI.[25][26][27]

The historical OMPython/PySimulator reference is a bibliographic discovery entry, not current installation or API guidance.[28]

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

## Sources

[1] https://arxiv.org/pdf/2503.18460v2 — ModiGen: A Large Language Model-Based Framework for Modelica Component Generation in Multi-Domain Systems
[2] https://arxiv.org/pdf/2503.18460v1 — ModiGen: A Large Language Model-Based Workflow for Multi-Task Modelica Code Generation
[3] https://arxiv.org/pdf/2509.14623v1 — Automating Modelica Module Generation Using Large Language Models: A Case Study on Building Control Description Language
[4] https://arxiv.org/pdf/2503.17004v1 — Text2Model: Generating Dynamic Chemical Reactor Models Using Large Language Models (LLMs)
[5] https://arxiv.org/pdf/2602.05883v1 — A Guide to Large Language Models in Modeling and Simulation: From Core Techniques to Critical Challenges
[6] https://api.crossref.org/works/10.2139/ssrn.5564442 — Automating Model Transformation from Modelica to SysML v2 with LLM-based Agents
[7] https://www.modelon.com/blog/from-intent-to-insight-ai-driven-physics-based-modeling-with-modelica — AI-Powered System Simulation with Modelica
[8] https://github.com/mtiller/ModelicaBook — Modelica by Example
[9] https://www.ida.liu.se/labs/pelab/modelica/OpenModelica/Documents/ModelicaBookExcerpts.pdf — Principles of Object-Oriented Modeling and Simulation with Modelica 2.1 — publicly supplied excerpts
[10] https://modelica.org/publications/books — Getting Started with Modelica
[11] https://api.crossref.org/works/10.1007/978-1-4615-1561-6 — Introduction to Physical Modeling with Modelica
[12] https://arxiv.org/pdf/2112.00862v1 — Modelling and Simulation of Power Systems with Grid-Connected Converters in OpenModelica
[13] https://www.mdpi.com/2079-9292/13/9/1614 — Modeling of Induction Motors and Variable Speed Drives for Multi-Domain System Simulations Using Modelica and the OpenIPSL Library
[14] https://2014.international.conference.modelica.org/proceedings/html/submissions/ECP14096515_FrankeWiesmann.pdf — Flexible modeling of electrical power systems — the Modelica PowerSystems library
[15] https://modelica.org/events/Conference2005/online_proceedings/Session7/Session7a2.pdf — Modelica libraries for dc machines, three phase and polyphase machines
[16] https://github.com/PowerGrids/PowerGrids — PowerGrids — Modelica library for electro-mechanical modelling of power systems
[17] https://github.com/OpenIPSL/OpenIPSL — OpenIPSL — Open-Instance Power System Library
[18] https://github.com/marcelotomim/OmniPES — OmniPES — Modelica Library for Power Systems Simulation
[19] https://ecp.ep.liu.se/index.php/modelica/article/view/179 — The FMI 3.0 Standard Interface for Clocked and Scheduled Simulations
[20] https://ecp.ep.liu.se/index.php/modelica/article/view/181 — Modelica, FMI and SSP for LOTAR of Analytical mBSE models: First Implementation and Feedback
[21] https://ecp.ep.liu.se/index.php/modelica/article/view/186 — OpenModelica.jl: A modular and extensible Modelica compiler framework in Julia targeting ModelingToolkit.jl
[22] https://ecp.ep.liu.se/index.php/modelica/article/view/217 — A Cloud-native Implementation of the Simulation as a Service-Concept Based on FMI
[23] https://ecp.ep.liu.se/index.php/modelica/article/view/937 — Application of the OpenModelica-Matlab Interface to Integrated Simulation and Successive Linearization Based Model Predictive Control
[24] https://ecp.ep.liu.se/index.php/modelica/article/view/947 — Beyond FMI - Towards New Applications with Layered Standards
[25] https://ecp.ep.liu.se/index.php/modelica/article/view/958 — A preCICE-FMI Runner to Couple FMUs to PDE-Based Simulations
[26] https://ecp.ep.liu.se/index.php/modelica/article/view/959 — Secure Exchange of Black-Box Simulation Models using FMI in the Industrial Context
[27] https://ecp.ep.liu.se/index.php/modelica/article/view/985 — Hybrid Power Systems Simulation and Optimization Utilizing SSP and FMI
[28] https://api.crossref.org/works/10.3384/ecp12076537 — An OpenModelica Python Interface and its use in PySimulator
[29] https://github.com/mtiller/ModelicaBook/blob/e9f0bc71f0c3f01be512dbeacd162f1b0749c030/LICENSE.md — ModelicaBook license
[30] https://www.amazon.com/Getting-Started-Modelica-Language-Modeling/dp/9199160803 — Getting Started with Modelica — public product metadata
[31] https://github.com/pnnl/prompt2control/blob/6583075268e8ae1ad579284280986af3483a2aba/ModuleGenerator.py — prompt2control ModuleGenerator.py (pinned source)
[32] https://modelica.org/publications/proceedings — Modelica Conference Proceedings index
