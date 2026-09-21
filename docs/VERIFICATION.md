# Foundation verification and review disposition

**Checkpoint note:** this document records the completed foundation/review stage. The later shared-desktop feature changed the MCP adapter and added two GUI tests; its subsequent full run passed **61 tests** (`artifacts/shared-desktop-all-tests.log`). See `SHARED_DESKTOP.md`. Counts and “final” statements below refer to the earlier 59-test checkpoint.

## Verdict

**PASS for the local OpenModelica modeling foundation, with documented source/feature gaps.** The final parent-run integration command passed **59 tests**. A subsequent fresh run passed all **six smoke cases**, and both Hermes MCP connections were re-tested. This is not an engineering-suitability certification, a Fable benchmark/preflight, an FMI importer test, or completion of the future dad presentation.

## Acceptance evidence

| Gate | Observed evidence |
|---|---|
| Pinned compiler + OMPython | Real version/load checks in `tests/test_toolchain.py`; isolated OM 1.27.1 / OMPython 4.1.0 / MSL 4.1.0 |
| Reference repositories | `repos-lock.json`: all seven required and five recommended checkouts, exact commits checked |
| Corpus and grounding | A–F index rebuilt and validated; 9,723 unique chunks; exact live class reflection and fail-closed bundles exercised |
| MCP integration | `artifacts/post-review-omedit-connection.log` and `post-review-corpus-connection.log`; 24 and three tools respectively; actual lookup/load/check/simulate/plot calls also made through Hermes |
| Model/script pairs and physics | `artifacts/post-review-smoke-run.log` points to the fresh summary; BouncingBall, RL, inertia, parameter reruns, three-phase and seeded repair all passed |
| Failure handling | Real compiler error despite raw OMC exit 0; stale/nonfinite/incomplete-data checks; rejected overrides now fail; cancellation cleanup tested |
| Native desktop | Per-user native OMEdit launcher registered; Wayland window observed with MSL and BouncingBall; native version and simulation/analytical checks passed |
| Durable operating procedure | Root `README.md`, `AGENTS.md`, setup/corpus/smoke/research docs; `openmodelica-ai` and `modelica-corpus-grounding` skills saved |

Main log: `artifacts/post-review-all-tests.log` — **59 passed in 174.02 s**. No source code was edited after that run; subsequent edits updated documentation/evidence only.

## Independent review findings and owner disposition

The original separate-context reviewer returned **no_ship** with two demonstrated P1 findings. Its report remains unchanged at `artifacts/review/REVIEW.md`. The author/parent implemented and verified fixes; the reviewer has **not** issued a second verdict. Do not relabel the original no_ship report as a clean review.

### P1: Existing but rejected parameter overrides — FIXED

Original final/evaluated `gain=2` requests produced `gain=1`, `x(1)=1`, yet the runner returned PASS. Names-only validation was inadequate.

The runner now checks compiled type/changeability, preserves targeted rejection diagnostics and reads actual effective parameter values from the simulation's `-output` stream. Requested values, compiled defaults and runtime readback are separate fields. Unsupported override types are explicit failures; benign warnings do not indiscriminately fail a run.

- RED log: `artifacts/override-fix/01-final-evaluated-red.log`.
- Post-fix replay: `artifacts/override-fix/independent/summary.json`.
- Both original-model probes now return **exit 1 / FAIL**, with actual `gain=1` retained. Original reviewer evidence hashes were rechecked unchanged.
- Relevant smoke/runner suite: **27 passed**, followed by the parent full **59-test** rerun.

### P1: Docker workload survives host timeout — FIXED

The original wrapper only exec'd `docker run --rm`. Killing that client left the computation running.

The wrapper now creates/starts separately, labels each exact UUID container, and uses an independent-session pipe-EOF guardian to verify exact-ID removal after caller timeout/SIGTERM/SIGKILL. A container-side deadline provides a second bound. The guardian checks ownership and Docker-client PID/start identity; it never removes containers by broad name/image matching.

- RED: `artifacts/lifecycle-red.log` (timeout/SIGKILL failures).
- GREEN: `artifacts/lifecycle-complete.log` (seven lifecycle/toolchain checks).
- Per-invocation cleanup and cancellation evidence: `artifacts/lifecycle/` and `artifacts/lifecycle-tests/`.
- The final complete suite includes these tests. A post-suite Docker query found no surviving ephemeral containers carrying this wrapper's ownership label.

Persistent headless OMEdit is a separate lifecycle: an RPC timeout does not assert its GUI simulation stopped. See `docs/SETUP.md`.

## Boundaries retained

D4 full text is still unavailable; B3/B4 are bibliography only, and the supplied Fritzson excerpt is historical Modelica 2.1. Third-party libraries are reference-only; incomplete ThermoPower aliases are marked. Retrieval is lexical, not semantic GraphRAG; Julia/ModelicaRag is not installed. Source reuse licenses remain restrictive in places.

No model/provider change, proprietary employer-data use, quant-corpus ingestion, trading-project write, trading-box operation, or external publication occurred. The PID presentation handoff is recorded as future context in `docs/END_GOAL.md`, not claimed as a finished demo.
