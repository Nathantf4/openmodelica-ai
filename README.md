# OpenModelica AI workspace

A local compiler-grounded workflow for reusable dynamic-system models: **retrieve real library interfaces → draft `.mo` + `.mos` → check → simulate → inspect diagnostics → verify physics and plot**.

## Start here

- **For guided work with Hermes:** open **OpenModelica — Hermes Shared**. This is the visible window controlled by the new `omedit-desktop` MCP; see [`docs/SHARED_DESKTOP.md`](docs/SHARED_DESKTOP.md).
- The original **OpenModelica OMEdit** launcher / `OMEdit` command remains a separate native application.
- Native compiler: `omc-native`. Reproducible isolated compiler: `omc` or project `bin/om`.
- **New to OMEdit?** Read [`docs/GUI_QUICKSTART.md`](docs/GUI_QUICKSTART.md). Open `examples/inertia_step/model.mo` as a model; leave `.mos` scripts alone initially. Opening a script as text does not execute it.
- Example source pairs: [`examples/`](examples/).
- Operations and installation details: [`docs/SETUP.md`](docs/SETUP.md).
- Retrieval and exact class lookup: [`docs/CORPUS.md`](docs/CORPUS.md).
- Models, numerical checks and error-loop evidence: [`docs/SMOKE.md`](docs/SMOKE.md).
- Extra anti-hallucination audit: [`docs/LLM_LIMITATION_AUDIT.md`](docs/LLM_LIMITATION_AUDIT.md) — fresh native builds of all saved examples/scripts, current live-MCP rechecks and actual ZIP replay.
- Source claims, corrections and rights: [`docs/RESEARCH_AUDIT.md`](docs/RESEARCH_AUDIT.md).
- **Ready demo:** [`docs/DAD_PRESENTATION.md`](docs/DAD_PRESENTATION.md) — Hermes operates the shared speed-PI demo; portable pack at `deliverables/dad-speed-pi.zip`.
- Original presentation context: [`docs/END_GOAL.md`](docs/END_GOAL.md).

There are now three instances: **`omedit-desktop` is the visible shared window**; `omedit` remains the original headless automation instance; the native `OMEdit` application remains independent. Use **OpenModelica — Hermes Shared** when you want to see Hermes's edits and simulations directly. The original native window and any unsaved work were left untouched.

## Verified foundation

| Component | Observed result |
|---|---|
| Compiler/bridge | OpenModelica 1.27.1, OMPython 4.1.0, MSL reporting 4.1.0; native and isolated paths both exercised |
| Desktop | Native per-user OMEdit registered in the launcher; BouncingBall and MSL loaded; native compile/simulation checked |
| Hermes MCP | `omedit-desktop`: visible shared GUI; `omedit`: original headless instance, each with 24 allowlisted official tools; `modelica-corpus`: three read-only tools. Actual calls exercised through Hermes. |
| References | Seven required + five recommended repositories pinned in `repos-lock.json` |
| Corpus | 9,723 unique tagged A–F chunks; local SQLite FTS5 retrieval and real compiler reflection |
| Model checks | BouncingBall, RL step, rotational inertia, parameter reruns, balanced three-phase, and an explicitly seeded failure/repair case |
| Regression suite | **65 tests passed**, including the speed-PI metrics/independent ODE and extracted-package native replay; see `artifacts/dad-demo/full-tests.log`. Earlier foundation and shared-desktop checkpoints are retained. |
| Separate review | Two reproduced P1 findings fixed; original findings and before/after evidence retained. Owner verification/disposition: [`docs/VERIFICATION.md`](docs/VERIFICATION.md). |

Native installation is under `~/.local/opt/openmodelica-1.27.1`, not pacman-managed. It runs without Docker. The native runtime has documented nonfatal library-version/rendering warnings; compiler and simulation tests passed. No system libraries were replaced and no sudo credential was stored.

## Use the agent workflow

Launch Hermes from this directory so `AGENTS.md` is available, or ask Hermes to load the `openmodelica-ai` skill. The supporting `modelica-corpus-grounding` skill covers retrieval details. Both MCP entries are configured in the default Hermes profile; current session tool discovery has already exercised them. For a different older session that lacks the tools, use `/reload-mcp` or start a new session.

```sh
cd /home/nathan/openmodelica-ai

# Ground a task in sources and actual installed interfaces.
.venv/bin/python scripts/corpus.py bundle 'step-driven RL circuit'
.venv/bin/python scripts/corpus.py lookup Modelica.Blocks.Continuous.LimPID

# Run a saved model through checked OMPython, retaining diagnostics and CSV.
bin/om python3 scripts/run_model.py examples/rl_step/model.mo RLStep --stop 2

# Run the ordered physics-checked suite and produce fresh PNGs.
.venv/bin/python scripts/smoke.py

# Run every integration test, including the explicit acquisition gate.
CORPUS_ACQUIRE=1 .venv/bin/pytest tests/ -q
```

Each runner call prints its report path. Keep fresh per-run directories; process exit 0 is not proof of successful Modelica compilation. Standalone `.mos` scripts should run from a new writable artifact directory containing their model/script pair—see the recipe in `docs/SMOKE.md`, rather than compiling into read-only source directories.

The final post-review smoke rerun is recorded by `artifacts/post-review-smoke-run.log` (earlier runs are retained). Its summary includes model/source identity, versions, actual commands, diagnostics, result paths, numerical errors and plot paths. The repair case intentionally contains a FAIL followed by PASS; that expected failure is not hidden.

## Limits and honest gaps

- This is a tested model-development foundation, **not** a validated real plant or replacement for specialist electrical-study software. Physics validity is task-specific.
- The repair smoke is a labelled, scripted correction of a seeded typo. No separate Fable generation session or future-model performance comparison has been claimed.
- Retrieval is lexical FTS5, **not semantic GraphRAG**. Julia/ModelicaRag.jl is cloned but not installed; no embedding service credentials or model API calls are required.
- Installed maintained MSL differs from the upstream v4.1.0 reference tag; compiler reflection and `runtime/library-lock.json` identify the actual runtime source.
- Third-party libraries are references, not validated runtime dependencies; ThermoPower has 38 explicitly incomplete alias interfaces.
- D4 SSRN full text remains inaccessible. B3/B4 are bibliography-only. The supplied Fritzson excerpt is Modelica **2.1**, not the briefing's 3.3 edition.
- Corpus access does not grant redistribution/commercial rights. Keep it local/private unless the individual source license permits the intended use.
- Optional FMI 2.0 Model Exchange export was archive/XML/Linux-binary checked, not simulated in an importer.
- The dad speed-PI pack has completed technical preflight with Astra. The actual presentation has not yet happened. No quant corpus or proprietary employer inputs were used; only controller gains change in the measured comparison.

The user's pinned Hermes model/provider and original `omcp` configuration were preserved. There were no trading-project writes, trading-box operations, external postings or account creation.
