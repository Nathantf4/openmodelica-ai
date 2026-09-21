# Local Modelica corpus and read-only MCP

This is **SQLite FTS5 lexical retrieval**, not embeddings, semantic nearest-neighbour retrieval, or GraphRAG. ModelicaRag.jl is a reference checkout, not an installed or exercised backend. No model provider is called.

## Commands

Run from `/home/nathan/openmodelica-ai`:

```sh
# Explicit source acquisition. Reuses archived web snapshots and matching library caches.
.venv/bin/python scripts/corpus.py acquire

# Offline: validate and atomically index every corpus/chunks/*.jsonl, including research.jsonl.
.venv/bin/python scripts/corpus.py build
.venv/bin/python scripts/corpus.py status
.venv/bin/python scripts/corpus.py search 'connector flow connect' --collection A --limit 5
.venv/bin/python scripts/corpus.py lookup Modelica.Electrical.Analog.Basic.Resistor
.venv/bin/python scripts/corpus.py lookup PowerSystems
.venv/bin/python scripts/corpus.py bundle 'step-driven RL circuit'
.venv/bin/python scripts/corpus.py bundle 'rotational inertia torque step'
.venv/bin/python scripts/corpus.py bundle 'BouncingBall equations when reinit'

# Override smoke-family defaults with TWO or THREE distinct, exact MSL names.
.venv/bin/python scripts/corpus.py bundle 'rotational torque input' \
  --class Modelica.Mechanics.Rotational.Components.Inertia \
  --class Modelica.Mechanics.Rotational.Sources.TorqueStep

# Read-only MCP over stdio; no HTTP listener. EOF/client disconnect stops it.
.venv/bin/python scripts/corpus_mcp.py

# Tests include actual isolated compiler reflection, a simulation, and stdio MCP.
.venv/bin/pytest tests/test_corpus.py tests/test_corpus_mcp.py -q
# Also exercise acquisition and archived-source integration:
CORPUS_ACQUIRE=1 .venv/bin/pytest tests/test_corpus.py tests/test_corpus_mcp.py -q
```

`build` does not acquire sources or modify other producers' JSONL. Failed validation preserves the previous index. CLI errors are JSON with a nonzero exit status. Search limits are 1–30; query length is at most 2,000 characters. FTS operators in user queries are treated as literal words, not executable query syntax.

`acquire` writes A/C technical snapshots, chunks and its own manifest. It does not register MCP, alter Hermes, install libraries, or run upstream installers. To deliberately refresh a web source, archive/remove that specific cached raw file first, then run `acquire`; this is not an automatic latest-version updater. Library caches carry their reference commit and reflection-schema version.

## What was acquired

The authoritative inventory is [`../corpus/manifests/technical.json`](../corpus/manifests/technical.json). Each source has a URL, raw checksum, local snapshot path and, where applicable, a git commit/version. The `acquired_utc` value records the acquisition/assembly run; cached web bytes can predate that run.

| Source | Captured scope |
|---|---|
| A1 | Released **MLS 3.7**, verified using the official release index and the versioned document title. Eight chapters: classes/declarations, scoping/name lookup/flattening, operators/`der()`, equations/`when`/`if`, connectors/connections, statements/algorithms, packages, annotations. No master/3.8-dev corpus. |
| A2 | MSL **v4.1.0 reference checkout**: 6,368 OMC-parsed class records. Headers, public interface declarations, parameter declarations, inheritance names and Documentation annotations—not equation-section dumps. |
| A2-PowerSystems | 1,289 reference class records. |
| A2-ThermoPower | 981 reference class records; 38 carry incomplete-interface diagnostics. These are chiefly nested aliases requiring legacy dependencies such as `Modelica.SIunits`. Errors are retained in the manifest, not converted into a compatibility pass. |
| A2-ElectroMechanicalDrives | 78 reference class records. |
| C1 | OpenModelica v1.27.1 pinned User Guide sources: introduction, compiler, solving, FMI/TLM and OMEdit chapters. This is selected coverage, not the whole manual. |
| C2 | Pinned OMPython chapter plus a separately labelled, locally authored compiler-diagnostics adapter tested with OMPython 4.1.0. |
| C3 | Pinned scripting API chapter and actual `ModelicaBuiltin.mo` declarations for loading, checking, simulation, diagnostics and reflection. |
| C4 | Pinned OpenModelica bibliography. Bibliographic entries are not a claim that every referenced paper was ingested. |
| C5 | Official **1.27.0** release notes, including MCP, and **1.27.1** patch release notes. |
| C6 | MCP **released 2025-11-25** specification documents from that explicit directory in the pinned checkout. No unversioned draft. |
| C7 | Pinned OMEdit MCP README and a point-in-time snapshot of issue 15385. Issue text is not release authority. |
| C8 | Modex public product overview excerpt only; no claim of full docs, editor installation or integration testing. |

The additional library references share collection A under distinct `A2-*` source IDs; research/domain literature remains in the separate producer's E collection. This keeps compiler/library authority distinct from papers without mixing the producers' files.

Snapshot sources can be followed directly from the manifest. Important version anchors:

- [MLS official versions](https://specification.modelica.org/) and [MLS 3.7](https://specification.modelica.org/maint/3.7/MLS.html).
- [Pinned OpenModelica source](https://github.com/OpenModelica/OpenModelica/tree/4a7248c1ab64f4205eb4222b6b009bbf2b0df383).
- [Pinned MSL v4.1.0 reference](https://github.com/modelica/ModelicaStandardLibrary/tree/8ae3d35c24e519cb2996cab20f3b13daf2b0c50a).
- [Released MCP specification directory](https://github.com/modelcontextprotocol/modelcontextprotocol/tree/24efd6e7cbd7a074e6b3b781eb370891df40afad/docs/specification/2025-11-25).

Rights are recorded per source/chunk. Local archival/indexing does not grant a blanket redistribution license. Retain the upstream repositories' notices and review rights before sharing the corpus.

## Compiler lookup versus reference indexing

The installed compiler library is **4.1.0+maint.om**, while `getVersion(Modelica)` reports `4.1.0`. The reference checkout is the pure **v4.1.0** tag. They are **not claimed to be bit-identical**.

- `lookup Modelica.…` starts an isolated offline `bin/om` compiler session, loads version `4.1.0`, confirms the reported version, checks `existClass`, then uses fixed reflection calls. Returned data includes runtime source path, line range, file SHA-256 and actual library source path.
- Public connector and parameter declarations are collected recursively through inheritance. Conditional connectors such as `heatPort` and `support` are reported as **declared interfaces**, not as proof they are enabled. Redeclarations, modifiers, conditional activation and final dimensions still require instantiation/checking.
- Reference indexing loads each pinned package with `uses=false`. This establishes parsability and exact names, **not** dependency compatibility or simulation success. It indexes declared interfaces and inheritance separately.
- Third-party exact lookup reads the reference index only and returns `reference-only`. It does not load a third-party library into the runtime or claim compatibility.
- ASCII dotted identifiers only are accepted. Whitespace, quoted identifiers, punctuation, function calls and expression injection are rejected. This is deliberately narrower than the full Modelica identifier grammar.
- `getComponents(..., useQuotes=true)` is intentional: symbolic dimensions such as `{na + nr + 1}` break the OMPython typed parser in its unquoted form. Boolean declaration fields are normalized explicitly; dimensions remain textual declarations.
- The correct existence query is `existClass`, not `isClass` (the latter tests a class restriction and rejects ordinary models).

No arbitrary OMC expression is exposed. The private extraction workers print JSON to stdout; host Python writes snapshots. They work with a read-only project mount and writable runtime scratch. Reflection may create compiler temporary/log files, but it does not modify models or invoke simulation.

## Fail-closed generation bundles

Every successful bundle contains:

1. One D1/D2 chunk containing compiler/error and feedback/iteration/repair language.
2. One A1 connector or equation chapter chunk, selected lexically for the query.
3. Two or three exact, currently reflected MSL interfaces. The response contains names/connectors and provenance rather than full library source. It distinguishes the runtime source checksum from the reference citation.
4. The C2 `checkModel` / `getErrorString` diagnostics adapter.

Missing papers, the relevant specification chapter, diagnostics, or any requested indexed class cause an error. Compiler lookup failure also fails the bundle. It does not silently substitute a reference-only library or omit a required source.

Defaults are deterministic, not a semantic-nearest claim:

| Family | Exact interfaces |
|---|---|
| Electrical / ambiguous | `Modelica.Electrical.Analog.Basic.Resistor`, `.Inductor`, `Modelica.Electrical.Analog.Sources.StepVoltage` |
| Rotational / inertia / torque | `Modelica.Mechanics.Rotational.Components.Inertia`, `Modelica.Mechanics.Rotational.Sources.TorqueStep`, `Modelica.Mechanics.Rotational.Sensors.SpeedSensor` |
| Bouncing / ball / impact | `Modelica.Mechanics.Translational.Components.Mass`, `.ElastoGap`, `Modelica.Mechanics.Translational.Sources.Force` |

These are grounding interfaces, **not wiring diagrams or complete models**. BouncingBall can be written directly with equations; the translational interfaces are alternatives for library-based modelling. For other domains, search and supply explicit exact classes. The bundle always sets `must_compile=true`; fresh model loading, `checkModel`, simulation, diagnostics, finite-data and physical-result checks remain mandatory.

## Schema and integrity

Every technical chunk has `id`, `collection`, `source_id`, `title`, `url`, `locator`, `content`, `sha256`, `rights_note`, `type`, `task`, `domain`, `audience`, and boolean `must_compile`. IDs start `technical-`. Required tag values are validated against the briefing's enums.

For technical documents, `sha256` hashes chunk UTF-8 content; `source_sha256` hashes archived source bytes. The locator identifies a chapter/file plus character offsets in the separately saved extracted text. For library records, the locator is an upstream `.mo` line range, `source_sha256` hashes that `.mo` file, and `raw_path` identifies its structured reflection snapshot.

The research producer uses `sha256` for acquired source bytes and supplies `text_sha256`, `extracted_path`, `source_start_char`, and `source_end_char`. The index preserves those identifiers/checksums exactly. For that schema, build verifies the extracted text's checksum and requires the chunk to equal the exact indicated slice; extracted paths must resolve below `corpus/raw`. Every indexed record additionally gets a computed `content_sha256` to make chunk integrity unambiguous. Raw-source checksums in that schema remain the research producer's provenance assertions; this index independently checks extracted-text/chunk integrity, not PDF extraction correctness.

Duplicate IDs, invalid tags, missing provenance, content/checksum mismatches and invalid extraction slices reject the rebuild. Reads open SQLite in `mode=ro`; only the explicit host CLI `build` command replaces the index.

## MCP integration

Launch command for the parent-owned registration:

```json
{
  "command": "/home/nathan/openmodelica-ai/.venv/bin/python",
  "args": ["/home/nathan/openmodelica-ai/scripts/corpus_mcp.py"]
}
```

Exactly three tools are exposed:

- `search_corpus(query, limit=6, collection=null)`
- `lookup_class(class_name)`
- `generation_bundle(query, class_names=null)`

All advertise `readOnlyHint=true`, `destructiveHint=false`, `idempotentHint=true`, and `openWorldHint=false`. There are no model APIs, sampling requests, file writers, arbitrary shell/OMC tools, source-acquisition tools or public listeners. Corpus text is untrusted reference data, not agent instructions. Standard MCP errors carry missing-source and validation failures to the client.

## Verification performed

- Vertical RED → GREEN runs covered indexing/provenance, live class lookup and injection rejection, source interface extraction, chunking/acquisition, missing-source bundle gates, symbolic dimensions, CLI, stdio MCP, source-hash interoperability and the executable diagnostics adapter.
- Final all-enabled run: **11 tests passed**, including real compiler and stdio protocol calls. Ordinary offline test mode skips only explicit acquisition.
- The archived C2 adapter checked and simulated pinned upstream `OMCompiler/Examples/BouncingBall.mo`, producing a nonempty MAT file. The official container did **not** contain the User Guide's assumed installed testmodels path; the adapter uses the verified checkout path instead. Run simulations from writable `runtime/tmp` or `artifacts` subdirectories, not the read-only project root.
- Real combined-corpus CLI bundles succeeded for RL, rotational inertia and BouncingBall, each with D1/D2, A1, three reflected classes, and C2.
- Real stdio MCP negotiated **2025-11-25**, discovered the three tools, searched the actual corpus, built an RL bundle and returned a PowerSystems lookup labelled reference-only.
- Combined index at verification: **9,723 chunks**, including **8,900 technical chunks**. Collection counts: A 8,765; B 567; C 135; D 152; E 95; F 9. `status` is authoritative after another producer changes its corpus; rerun `build` after such changes.

This verifies retrieval and the tool interface, not the engineering suitability of an agent-generated model. ThermoPower's incomplete aliases, C8's limited coverage, symbolic/conditional-interface limitations and the non-semantic retrieval backend remain explicit limitations.
