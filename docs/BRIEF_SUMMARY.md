# OpenModelica + AI — short briefing

## 1. What the files and tools are

- **`.mo`**: the Modelica model—components, connectors, parameters and equations describing a dynamic system. Open it in OMEdit to inspect and simulate.
- **`.mos`**: an OpenModelica automation script that loads libraries/models, checks them and runs simulations. Opening it in OMEdit displays text; it does not execute the script.
- **OMPython**: Python access to the OpenModelica compiler's scripting API. It supports repeatable runs, parameter sweeps, diagnostic capture and an agent's generate→check→repair loop. Our installed version uses `OMCSessionLocal()`.
- **`omc`** is the compiler; **OMEdit** is the graphical editor/simulation/plotting application.

## 2. Enabling OMEdit MCP

Use an MCP-capable **OpenModelica 1.27+ Qt6 build**; version alone is insufficient—the stock 1.27.1 GUI container we checked used Qt5 and lacked MCP.

For a conventional Linux/macOS installation, configure `~/.config/openmodelica/omedit.ini`:

```ini
[modelContextProtocol]
enabled=true
port=3000
enableAdminTools=true
```

Restart OMEdit. Connect a Streamable HTTP MCP client to `http://localhost:3000/mcp`; `/mcp/admin` additionally exposes administrative file/library-loading tools. Enable those only when needed and keep the service local. Verify discovery **and an actual check/simulation**, not just connectivity.

**Our installed setup is already connected:** “OpenModelica — Hermes Shared” uses `omedit-desktop` MCP. A local stdio adapter reaches the official server inside a network-disabled container; no host HTTP port is published. Hermes operates the same visible window Nathan watches.

## 3. Literature and library grounding

Keep collections separate:

- **D — LLM research:** ModiGen (`2503.18460`), PNNL's CDL-generation study (`2509.14623`), Text2Model (`2503.17004`), Giabbanelli's M&S guide (`2602.05883`), Modelica→SysML v2 agents, and Modelon's cautionary example. Pin paper versions; distinguish experiments from vendor anecdotes. The SysML paper's full text remains unavailable.
- **A — language/library authority:** released **Modelica Language Specification 3.7**, especially connectors, equations, events and initialization; **Modelica Standard Library 4.1.0** interfaces/documentation. Language and library version numbers are different things.
- **B — learning:** Tiller's *Modelica by Example* first; licensed/public Fritzson excerpts as supporting material. The supplied Fritzson excerpt is **Modelica 2.1**, not 3.3. Public accessibility does not grant unrestricted redistribution.
- **C — tooling:** OpenModelica User Guide, scripting API, OMPython documentation, release notes, official OMEdit MCP documentation and the released MCP specification.
- **E — electrical/energy:** MSL Electrical and Machines first; PowerSystems and ElectroMechanicalDrives references; ThermoPower for coupling. PowerGrids, OpenIPSL and OmniPES are later domain candidates, not automatically installed or validated dependencies.
- **F — proceedings:** retrieve relevant scripting/FMI/electrical-methods papers on demand; do not ingest unrelated case studies indiscriminately.

Index library class names, connectors, parameters and documentation—not wholesale equation dumps. Do not mix the quant corpus or proprietary employer data into this corpus.

## 4. Repositories: clone versus defer

**Core/reference clones:**
`OpenModelica/OpenModelica`, `OpenModelica/OMPython`, `modelica/ModelicaStandardLibrary`, `mtiller/ModelicaBook`, `pnnl/prompt2control`, `miko99jh/ModiGen`.

**Useful additional references:**
`OpenModelica/ModelicaRag.jl`, `modelica-3rdparty/PowerSystems`, `casella/ThermoPower`, `benvansleen/LLModelica`, `christiankral/ElectroMechanicalDrives`, `modelcontextprotocol/modelcontextprotocol`.

All of those are cloned and pinned here. **ModelicaRag.jl is reference-only:** Julia/semantic embeddings are not installed; local retrieval uses SQLite FTS5 plus compiler reflection.

**Defer unless a specific need arises:** `Casys-AI/mcp-modelica`, `Orthogonalpub/modelica_simulation_mcp_server`, `OpenModelica/ThermalAndPowerGridSystem`, and Modex. The official MCP and current workflow already cover our immediate task. Cloning a repository is not approval to execute its installer or proof of library compatibility.

## 5. Ingest tags and mandatory retrieval

Every chunk carries provenance—URL, version/commit, locator, checksums and rights—and these tags:

```text
type: spec | textbook | example-mo | tool-api | llm-paper | library-class
task: generate-component | generate-test | simulate | edit-diagram | search-library | mcp-tool | export-fmu
domain: electrical-power | machines-drives | control | thermal | general
audience: methods | corporate-ee | interoperability
must_compile: true | false
```

`must_compile` expresses a requirement, not evidence that a referenced example already passed. Exclude/downrank site operations, protection coordination, cable ampacity and arc-flash work.

Every generation bundle must include:
1. A **D1/D2 compiler-feedback/error-loop excerpt**.
2. The matching **A1 connector/equation rule**.
3. **Two or three exact library interfaces**, checked against the installed compiler.
4. **C2 loading/checking/simulation/diagnostic guidance**.

Missing required grounding fails the bundle; plausible invented class names are not substitutes. This retrieval recipe is a project synthesis informed by the literature, not a reproduced universal benchmark result.

## 6. Fable 5.1 versus Astra

The original briefing preferred Fable 5.1 and restricted Astra to drafting. **Nathan superseded that restriction: Astra can generate, repair, retune and operate the complete live demo.** Keep the selected model pinned. Fable remains an option, not a dependency.

Both must use the same compiler and physical-validation gates. Older GPT-4o/Claude studies do not establish a capability ranking for current Astra versus Fable.

## 7. Smoke-test ladder—no invented grid model

Advance in order: **BouncingBall → step-driven R–L circuit → torque/inertia → verified parameter reruns → small balanced three-phase source–line–load**. Stop and repair the toolchain if the early cases fail. The public speed-PI demo comes after these foundations, not instead of them.

For every delivered model require successful loading, `checkModel`, simulation, fresh finite full-horizon data, effective parameter readback where overridden, and analytical/independent physical checks. Preserve real diagnostics and label seeded repair examples honestly.

**Shell exit 0, an attractive diagram, or compiler success alone is not physical validation.** No “fake grid” shortcut and no claim to replace specialist engineering studies.

---
Based on the supplied briefing, corrected by the implemented/audited project documentation: `SETUP.md`, `CORPUS.md`, `RESEARCH_AUDIT.md`, `SMOKE.md`, `SHARED_DESKTOP.md`, and Nathan's approval of Astra for the full demo.
