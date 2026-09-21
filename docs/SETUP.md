# Installed runtime and desktop

**For a visible window controlled by Hermes, use “OpenModelica — Hermes Shared” and the `omedit-desktop` MCP.** See `SHARED_DESKTOP.md`. The native app and original headless server documented below remain independent alternatives; their original isolation statements do not describe the shared instance's deliberately mounted Wayland socket.

## Native desktop application (no Docker needed to run it)

- Launcher: **OpenModelica OMEdit** in the desktop application menu.
- Command: `/home/nathan/.local/bin/OMEdit`.
- Native compiler: `/home/nathan/.local/bin/omc-native`.
- Prefix: `/home/nathan/.local/opt/openmodelica-1.27.1/`.
- GUI library cache: `/home/nathan/.openmodelica/libraries/` (independent copy).
- GUI settings: `/home/nathan/.config/openmodelica/omedit.ini`.
- GUI output directory: `/home/nathan/openmodelica-ai/artifacts/native-gui/`.

This is a **per-user native binary installation**, not a pacman-managed package and not a container launcher. It uses signed official OpenModelica 1.27.1 resolute packages, verified against signed release metadata and SHA256, with a small set of signed Arch runtime libraries in its own prefix. CORBA runtime dependencies came from the signed Ubuntu packages in the locally built, pinned Qt6 image. Package and dependency provenance are recorded in `install-manifest.json` and `dependency-manifest.json` in the prefix. No system library was replaced; no sudo credential was stored or used.

`launch.py` sets the installation prefix and private library paths only for the launched process. Native `omc --version`, native compilation/simulation of the supplied BouncingBall and a ballistic analytical check have passed. The GUI was launched on native Wayland with BouncingBall and MSL 4.1.0 loaded. Some nonfatal packaging/rendering warnings remain: Debian expects symbol-version metadata absent from Arch's libcurl-gnutls, and OMEdit may fall back from GBM to Vulkan and from a missing en_US translation. These are not hidden; see `artifacts/native-omedit.log`, the OMEdit output log, and `artifacts/native-tests.log`.

The desktop GUI MCP is deliberately **disabled**. The Hermes MCP below controls a separate isolated OMEdit, not your visible desktop window. Open the same saved `.mo` files in the native editor to inspect or modify them. Do not assume unsaved edits in one instance have reached the other.

Browse `Modelica > Electrical > Analog > Examples`, `Modelica > Electrical > Machines > Examples`, or `Modelica > Mechanics > Rotational > Examples` in the library tree. Double-click a model, then use **Simulation → Simulate**. Project examples are documented in `docs/SMOKE.md`.

## Reproducible agent compiler

`bin/om` starts an ephemeral official OpenModelica/OMPython container. `bin/omc` and the user PATH command `omc` are compatibility shims for this isolated compiler; use `omc-native` when specifically testing the desktop installation.

- Compiler: OpenModelica **1.27.1**.
- OMPython: **4.1.0**, image Python 3.10; use `OMCSessionLocal()` (old `OMCSessionZMQ()` is deprecated).
- Official image: `openmodelica/openmodelica@sha256:a79649b5b65bc3051b324efa05dbf24af460048d51894447e5e324d52e79c65f`.
- MSL reports **4.1.0**; actual installed package is **4.1.0+maint.om**, OpenModelica-maintained commit `8df0769a9cee6ad04ddfff95faee64cd70f662ec`. See `runtime/library-lock.json` for component hashes.
- Reference checkout is upstream **v4.1.0** and is NOT bit-identical to the installed maintained package. Compiler reflection is the runtime authority.

```sh
cd /home/nathan/openmodelica-ai
omc --version
bin/om python3 -c 'from OMPython import OMCSessionLocal; o=OMCSessionLocal(); print(o.sendExpression("getVersion()")); o.sendExpression("quit()")'
.venv/bin/python -m unittest discover -s tests -p test_toolchain.py -v
```

Host `.venv` uses Python 3.12 for retrieval, MCP, PDF extraction, plotting and pytest; `requirements.lock` pins its dependencies. It does not replace the system Python. OMPython executes inside `bin/om`, not that host venv.

## Official OMEdit MCP, isolated

The official `v1.27.1-gui` Docker image was verified to contain **Qt5 and no MCP server**. Merely checking the OpenModelica version is insufficient. The working image was built from official release **Qt6** packages on pinned Ubuntu 26.04 using `docker/omedit/Dockerfile`. The runtime launcher pins the resulting image ID. Keep/rebuild that image deliberately; do not silently replace it with the Qt5 GUI tag.

```sh
bin/omedit-mcp start
bin/omedit-mcp health
bin/omedit-mcp status
bin/omedit-mcp logs
bin/omedit-mcp stop
hermes mcp test omedit
```

`bin/omedit-mcp serve` adapts stdio to the official MCP HTTP endpoint **inside** the container using `docker exec`; it does not implement a replacement Modelica tool API or intercept model-provider traffic. Schemas/results, including plot images, come from the official OMEdit server. It starts the container on demand. No host HTTP port is opened, so `localhost:3000` in your host browser is intentionally not this server.

Hermes default profile entry `mcp_servers.omedit` is configured with lazy startup, disabled sampling/elicitation and sequential calls. The adapter exposes 24 allowlisted tools; environment reset is excluded. Load-file paths must be existing `.mo` files inside the project. A checker text failure cannot be treated as success merely because its JSON-RPC request succeeded.

Actual initialize/tool discovery/create/edit/check/simulate/result-file/plot/error handling was exercised in `tests/test_omedit.py`; per-run protocol evidence and PNGs are under `artifacts/omedit/OMEditVerification_*/`.

### Execution boundary

Both agent containers run non-root, network `none`, no privileges, all capabilities dropped, read-only container root, 2 CPU / 3 GiB / 256-PID limits. Project code, venv, reference repositories and examples are read-only **inside** containers; only `runtime/`, `artifacts/`, and private ephemeral container `/tmp` are writable. No host Docker socket, host home directory, credentials, Wayland socket, or X11 display is mounted. The headless OMEdit uses private Xvfb. Native OMEdit, in contrast, has normal user permissions and should only open trusted models.

Use fresh output directories under `artifacts/` for compiled executables. Host-side agents may edit source normally; container compilation cannot rewrite host-executed project code. Modelica external functions can execute native code, so this boundary matters even if a model looks like a collection of equations.

No Hermes model/provider selection was changed. Existing `omcp` settings were preserved and checked against their pre-change digest.

## Compiler cancellation and deadlines

`bin/om` creates each container with a UUID name and ownership label, then starts/attaches separately. A separate-session guardian owns the read end of a private lifetime pipe. Normal completion, SIGTERM, SIGKILL, or caller timeout closes that pipe; the guardian removes only the exact owned container ID and verifies absence. This is deliberately not a `finally` block in the killed process. It also verifies Docker-client PID/start identity before signalling it. Lifecycle evidence is under `artifacts/lifecycle/`.

The workload additionally runs under GNU `timeout` **inside** the container: 600 seconds by default, TERM followed by KILL after five seconds. Override with `OPENMODELICA_TIMEOUT_SECONDS` only as an integer from 1 through 3600. This is a fallback bound, not a substitute for cancellation cleanup. An unverified cleanup returns failure rather than silently passing. Actual host timeout, SIGTERM and SIGKILL tests verify container absence; a separate deadline test proves exit 124 and checks preserved stdin/nonzero exit propagation.

This lifecycle guarantee concerns ephemeral `bin/om` jobs. Persistent `omedit-mcp` has its own start/stop lifecycle; an RPC timeout means execution state is unknown and requires inspection, not a claim that its GUI operation stopped.

## Optional choices

Julia was absent. `ModelicaRag.jl` was cloned/reviewed but not installed: its default GitHub embeddings require credentials and its whole-symbol embedding differs from the brief's interface-focused ingestion. The project implements local, credential-free corpus/library retrieval instead; see `docs/CORPUS.md`. This is not a claim that Julia semantic RAG has been installed.

Modex, external simulation MCP servers, fine-tuning, production plant inputs and specialist power-study replacements remain out of scope.
