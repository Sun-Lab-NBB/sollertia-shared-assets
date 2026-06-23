# Claude Code Instructions

## Session start behavior

At the beginning of each coding session, before making any code changes, you should build a comprehensive understanding
of the codebase by invoking the `/explore-codebase` skill.

This ensures you:
- Understand the project architecture before modifying code
- Follow existing patterns and conventions
- Do not introduce inconsistencies or break integrations with the downstream libraries that consume this library

## Style guide compliance

You MUST invoke the appropriate skill before performing ANY of the following tasks:

| Task                                       | Skill to invoke    |
|--------------------------------------------|--------------------|
| Writing or modifying Python code           | `/python-style`    |
| Writing or modifying README files          | `/readme-style`    |
| Writing git commit messages                | `/commit`          |
| Writing or modifying pyproject.toml        | `/pyproject-style` |
| Writing or modifying tox.ini               | `/tox-config`      |
| Writing or modifying Sphinx docs files     | `/api-docs`        |
| Creating or verifying project structure    | `/project-layout`  |
| Writing or modifying skill files / this MD | `/skill-design`    |
| Auditing for style compliance              | `/audit-style`     |
| Auditing for factual accuracy              | `/audit-facts`     |

Each skill contains a verification checklist that you MUST complete before submitting any work. Failure to invoke the
appropriate skill results in style violations that block release.

## Cross-referenced library verification

This library depends on `ataraxis-base-utilities`, `ataraxis-time`, and `ataraxis-data-structures`, and is itself
consumed by `sollertia-experiment`, `sollertia-forgery`, and the `sollertia-virtual-reality` McpBridge. Local
clones of all of these typically live alongside this repository under `/home/cyberaxolotl/Desktop/GitHubRepos/`.

**Before writing code that interacts with a cross-referenced library, you MUST:**

1. **Check for local version**: Look for the library in the parent directory (e.g., `../ataraxis-base-utilities/`,
   `../ataraxis-data-structures/`, `../sollertia-experiment/`).

2. **Compare versions**: If a local copy exists, compare its version against the latest release or main branch on
   GitHub:
   - Read the local `pyproject.toml` to get the current version
   - Use `gh api repos/Sun-Lab-NBB/{repo-name}/releases/latest` to check the latest release
   - Alternatively, check the main branch version on GitHub

3. **Handle version mismatches**: If the local version differs from the latest release or main branch, notify the user
   with the following options:
   - **Use online version**: Fetch documentation and API details from the GitHub repository
   - **Update local copy**: The user will pull the latest changes locally before proceeding

4. **Proceed with correct source**: Use whichever version the user selects as the authoritative reference for API
   usage, patterns, and documentation.

**Why this matters**: Skills and documentation may reference outdated APIs. Always verify against the actual library
state to prevent integration errors.

## Available skills

The sollertia marketplace ships an `assets` plugin with skills that target this library directly, and a `unity` plugin
whose Unity Editor skills drive the `McpBridge` relay tools that this library's `slsa mcp` server exposes through
`interfaces/unity_tools.py`. The ataraxis marketplace ships the `automation` plugin used across all Sollertia Platform
repositories.

| Skill                           | Description                                                                      |
|---------------------------------|----------------------------------------------------------------------------------|
| `/explore-codebase`             | Perform in-depth codebase exploration at session start                           |
| `/python-style`                 | Apply Sollertia Platform Python coding conventions (REQUIRED for Python changes) |
| `/readme-style`                 | Apply Sollertia Platform README conventions (REQUIRED for README changes)        |
| `/commit`                       | Draft Sollertia Platform style-compliant git commit messages                     |
| `/pyproject-style`              | Apply Sollertia Platform pyproject.toml conventions                              |
| `/tox-config`                   | Apply Sollertia Platform tox.ini conventions                                     |
| `/api-docs`                     | Apply Sollertia Platform Sphinx documentation conventions                        |
| `/project-layout`               | Apply Sollertia Platform project directory structure conventions                 |
| `/skill-design`                 | Generate, update, and verify skill files and this CLAUDE.md                      |
| `/audit-facts`                  | Audit documentation files against source code for factual accuracy               |
| `/audit-style`                  | Audit files against applicable style skill checklists for compliance             |
| `/assets-mcp-environment-setup` | Diagnose and resolve `slsa mcp` server connectivity issues                       |
| `/working-directory`            | Initialize the working directory, credentials files, and templates path          |
| `/project-hierarchy`            | Discover the project / animal / session tree under the data root                 |
| `/session-discovery`            | Discover and filter sessions by date, animal, or name (`session_paths` flow)     |
| `/session-data`                 | Read, write, and validate `session_data.yaml` markers                            |
| `/session-descriptors`          | Read, write, and validate per-session-type `session_descriptor.yaml` files       |
| `/session-hardware-state`       | Read, write, and validate `hardware_state.yaml` snapshots                        |
| `/subject-metadata`             | Read and amend `surgery_metadata.yaml` SurgeryData files                         |
| `/experiment-configuration`     | Author per-project `MesoscopeExperimentConfiguration` YAMLs                      |
| `/task-templates`               | Author and validate reusable Unity `TaskTemplate` YAMLs                          |
| `/library-extension`            | Orchestrate cross-cutting changes when extending the library's vocabulary        |

You MUST invoke `/library-extension` instead of editing the registries directly when adding a new `AcquisitionSystems`
member, `SessionTypes` member, runtime trial class (a sibling of `MesoscopeWaterRewardTrial` /
`MesoscopeGasPuffTrial`), or `TriggerType` member. The skill owns the touch list and the import-time parity check.

## MCP server

This library exposes an MCP server registered in the sollertia marketplace as part of the `assets` plugin. The server
runs through the `slsa mcp` CLI command and is consumed by AI agents working on Sollertia data. The server bootstrap,
the CLI, and all tool implementations live in `src/sollertia_shared_assets/interfaces/`:

| Module              | File                                | Surface                                                            |
|---------------------|-------------------------------------|--------------------------------------------------------------------|
| CLI entry point     | `interfaces/cli.py`                 | `slsa` Click group: `mcp` + `get` + `configure` subcommands        |
| Server bootstrap    | `interfaces/mcp_server.py`          | Auto-imports `*_tools.py` to register; exposes `run_server`        |
| Shared MCP instance | `interfaces/mcp_instance.py`        | FastMCP instance, response helpers, serialization, validators      |
| Configuration tools | `interfaces/configuration_tools.py` | working dir, data root, credentials, templates dir, experiments    |
| Data tools          | `interfaces/data_tools.py`          | session discovery, inspection, descriptors, surgery, etc.          |
| Unity tools         | `interfaces/unity_tools.py`         | McpBridge HTTP relay (Editor must be running)                      |

Project conventions for MCP tools:
- MCP tool functions are excluded from unit tests by project convention. Do NOT write tests for `@mcp.tool()` functions.
  Coverage configuration in `pyproject.toml` already omits `*/interfaces/*`.
- Every MCP tool returns a `dict[str, Any]` response constructed via `ok_response(...)` or `error_response(...)` from
  `mcp_instance`. Return shapes documented in each tool's `Returns` docstring section are part of the public contract.
- Tools that take a session path use file-path-based access — the caller passes the path explicitly, not a session ID.
- Tool responses chain: `get_data_root_overview_tool` produces `sessions` entries, `filter_sessions_tool` consumes
  them and returns a `session_paths` list that downstream `sollertia-*` MCP servers (forgery, etc.) accept directly.
  Non-Sollertia MCP servers (`cindra`, `ataraxis-video-system`, `ataraxis-communication-interface`) do not consume
  `session_paths` — pass concrete paths or recordings instead.

For server connectivity issues, invoke `/assets-mcp-environment-setup`.

## Downstream library integration

This library is the shared-asset layer between every other Sollertia component. Changes to dataclasses, registry
contracts, or canonical filenames ripple through three downstream libraries:

- **sollertia-experiment** (acquisition runtime). Consumes `SessionData.create` / `load`, every descriptor class,
  `MesoscopeExperimentConfiguration`, the working directory, and the Google credentials file resolved through
  `get_credentials`. Owns the system-level `MesoscopeSystemConfiguration`, which extends but does not live in this
  library.
- **sollertia-forgery** (data-processing pipeline). Consumes `SessionData.load`, `filter_sessions`, the working
  directory itself (per-project artifacts like `<working_dir>/<project>/manifest.feather`) and its `configuration/`
  subdirectory (where the forgery server configuration is persisted), the `ProcessingTrackers` enum,
  `MesoscopeHardwareState`, and `MesoscopeExperimentConfiguration`.
- **sollertia-virtual-reality** (Unity Editor McpBridge plugin). Consumed by `interfaces/unity_tools.py` over HTTP
  localhost; the plugin itself is authored on the Unity side.

You MUST maintain backwards compatibility for any class, constant, or filename that is exported through
`src/sollertia_shared_assets/__init__.py` unless the user explicitly requests a breaking change. When breaking
changes are necessary, coordinate with the downstream library maintainers and bump the major version.

## Project context

This is **sollertia-shared-assets**, a Python library that provides data acquisition and processing assets shared
between Sollertia platform libraries. It is part of the Sollertia AI-assisted scientific data acquisition and
processing platform, built on the Ataraxis framework, and developed in the Sun (NeuroAI) lab at Cornell University.

### Key areas

| Directory or module                           | Purpose                                                                                                                              |
|-----------------------------------------------|--------------------------------------------------------------------------------------------------------------------------------------|
| `src/sollertia_shared_assets/enums.py`        | Cross-system vocabulary enums (`AcquisitionSystems`, `SessionTypes`, `ReadAssets`, `CredentialsTypes`); a leaf with no local imports |
| `src/sollertia_shared_assets/registries.py`   | Every dispatch registry as a fully populated literal, plus the import-time checks and `resolve_read_asset`                           |
| `src/sollertia_shared_assets/credentials.py`  | Credentials toolset (`resolve_credentials_file`, `set_credentials`, `get_credentials`)                                               |
| `src/sollertia_shared_assets/configuration/`  | Persistent host settings and the shared VR-task / experiment configuration primitives                                                |
| `src/sollertia_shared_assets/data_classes/`   | Read-asset contract dataclasses (currently `surgery_data.py`); registry-free by design                                               |
| `src/sollertia_shared_assets/data_hierarchy/` | `SessionData`, the project/animal hierarchy views, and the session-discovery helpers                                                 |
| `src/sollertia_shared_assets/mesoscope_vr/`   | Mesoscope-VR system subpackage: experiment configuration, runtime data, raw-data layout                                              |
| `src/sollertia_shared_assets/interfaces/`     | `slsa` CLI and FastMCP server with all MCP tool modules                                                                              |
| `tests/`                                      | Test suite mirroring the source layout (MCP tools excluded)                                                                          |
| `docs/`                                       | Sphinx API documentation source                                                                                                      |
| `envs/`                                       | Conda/mamba development environment specifications                                                                                   |

### Architecture

- **Vocabulary and wiring**: The keying enums live in the leaf `enums.py` module, and every dispatch registry is
  defined — fully populated — in the top-level `registries.py` module, which imports each system subpackage and the
  contract dataclasses. The import graph is a strict DAG: `enums`, `data_classes`, and `configuration` are leaves;
  `mesoscope_vr` imports `configuration`; `registries` imports the leaves and the system subpackages; `credentials`
  and `data_hierarchy` sit above `registries`; `interfaces` sits on top. Shared modules never import from a system
  subpackage — only `registries.py` does.
- **Configuration layer**: `TaskTemplate` (the Unity corridor template, in `configuration/`) and
  `MesoscopeExperimentConfiguration` (Mesoscope-VR experiment config, in `mesoscope_vr/`) are independent siblings —
  both inherit directly from `YamlConfig`, neither inherits from the other. Every Sollertia acquisition system runs a
  Unity VR task in the linear infinite corridor, so every `<System>ExperimentConfiguration` shares one contract: an
  `experiment_states` field (the experiment state machine), a `trial_structures` field (the trials the experiment
  runs, with concrete trial classes varying per system), a `unity_scene_name` field (the corridor task the experiment
  runs), and a `from_task_template` classmethod. Fields beyond the contract are system-specific; `ExperimentState` is
  the shared building block that stays in `configuration/`, while each acquisition system defines its own trial
  classes in its subpackage (Mesoscope-VR's `MesoscopeWaterRewardTrial` and `MesoscopeGasPuffTrial` live in
  `mesoscope_vr/experiment_configuration.py`).
  The platform `TriggerType` enum carries five members — `INTERACTION`, `COLLISION`, `OCCUPANCY_DISARM`,
  `OCCUPANCY_ARM`, and `OCCUPANCY_TRIGGER` — and each acquisition system maps only the subset it supports.
  `MesoscopeExperimentConfiguration.from_task_template` converts a `TaskTemplate` into a
  `MesoscopeExperimentConfiguration` by mapping each `TrialStructure.trigger_type` to a `MesoscopeWaterRewardTrial`
  (for `TriggerType.INTERACTION`) or `MesoscopeGasPuffTrial` (for `TriggerType.OCCUPANCY_DISARM`). The remaining three
  members (`COLLISION`, `OCCUPANCY_ARM`, `OCCUPANCY_TRIGGER`) are intentionally unmapped on Mesoscope-VR, so a
  Mesoscope-VR config that uses one raises a clear "not mapped to a runtime trial class" error; a new `TriggerType`
  member does NOT require a `from_task_template` branch, because a system may leave it unsupported.
  `create_experiment_from_vr_template_tool` dispatches through `EXPERIMENT_CONFIGURATION_REGISTRY` to the registered
  class's `from_task_template`, and `write_experiment_configuration_tool` authors any system's configuration from a
  full payload. See the README's "Adding New Acquisition Systems" Step 4 for the creation-path recipe.
- **Data layer**: `SessionData` (in `data_hierarchy/session_data.py`) is the entry point for every session on disk.
  `SessionData.create()` mints a new session, `SessionData.load()` rehydrates one. Both build runtime-only
  `raw_data`, `processed_data`, and `system_raw_data` sub-dataclasses by consulting `SYSTEM_RAW_DATA_REGISTRY`.
  Descriptor and hardware-state classes are dispatched by `SessionTypes` and `AcquisitionSystems` enum membership.
  The `data_classes/` package holds only read-asset contract dataclasses; contract modules export plain dataclasses
  and never consume the registries.
- **Interface layer**: A single `FastMCP` instance lives in `interfaces/mcp_instance.py` with shared serialization,
  validation, and dataclass-introspection helpers; the dispatch registries and their import-time checks live in the
  top-level `registries.py` module, not here. Tool modules import the instance and register `@mcp.tool()` functions.
  The CLI (`slsa`) starts the server and exposes `configure {directory,data-root,credentials,templates,project}` and
  `get {directory,data-root,credentials,templates,projects,experiments}` command groups.
- **Persistent host settings**: Three independent `platformdirs`-backed settings — working directory, data root,
  templates directory — are managed in `configuration/configuration_utilities.py`. The credentials toolset that
  copies each category's credentials file into the working directory's `credentials/` subdirectory under its
  canonical filename lives in the top-level `credentials.py` module, downstream of `registries.py`, because its
  functions consume `CREDENTIALS_FILE_REGISTRY` at runtime. Only the working directory is required for `slsa mcp` to
  function.

### Extension contracts

Every dispatch registry is defined — fully populated — in the top-level `registries.py` module, keyed by the
vocabulary enums in the leaf `enums.py` module. The registries form two governance tiers. The system registries
(`DESCRIPTOR_REGISTRY`, `HARDWARE_STATE_REGISTRY`, `EXPERIMENT_CONFIGURATION_REGISTRY`, `SYSTEM_RAW_DATA_REGISTRY`,
the `SYSTEM_SESSION_TYPES` association, and the `SESSION_TYPES_USING_VR_TASK` gate) form the designed extension
point: they grow whenever a new acquisition system or session type is added. The contract registries
(`READ_ASSET_REGISTRY`, `CREDENTIALS_FILE_REGISTRY`) are durable translation contracts curated by Sollertia platform
maintainers; adding an entry there is a platform-contract decision, not a routine extension. Use the
`/library-extension` skill for system and session-type extensions — it owns the touch list and the import-time
parity check that fails if any registry is incomplete.

| Registry                            | Keyed by             | Tier                       |
|-------------------------------------|----------------------|----------------------------|
| `DESCRIPTOR_REGISTRY`               | `SessionTypes`       | System (extension point)   |
| `HARDWARE_STATE_REGISTRY`           | `AcquisitionSystems` | System (extension point)   |
| `EXPERIMENT_CONFIGURATION_REGISTRY` | `AcquisitionSystems` | System (extension point)   |
| `SYSTEM_RAW_DATA_REGISTRY`          | `AcquisitionSystems` | System (extension point)   |
| `SYSTEM_SESSION_TYPES`              | `AcquisitionSystems` | System (extension point)   |
| `READ_ASSET_REGISTRY`               | `ReadAssets`         | Contract (maintainer-only) |
| `CREDENTIALS_FILE_REGISTRY`         | `CredentialsTypes`   | Contract (maintainer-only) |

`DESCRIPTOR_REGISTRY` is deliberately flat: a session type maps to exactly one descriptor platform-wide, so an
acquisition system that needs a different descriptor must mint a new `SessionTypes` member.
`_assert_registry_coverage()` in `registries.py` runs on a bare `import sollertia_shared_assets` (the hub loads
without the MCP server) and raises `RuntimeError` if any registry is missing entries for a known enum member. Also,
if `SYSTEM_SESSION_TYPES` leaves an acquisition system with no session types or a session type unclaimed by any
system. The hub additionally runs `_assert_descriptor_contract()` (every registered descriptor must declare the
`incomplete` field the inspection tooling reads) and `_assert_experiment_configuration_contract()` (every registered
experiment configuration must declare the `experiment_states`, `trial_structures`, and `unity_scene_name` contract
fields and provide a `from_task_template` classmethod. A half-wired acquisition system fails fast instead of
having its template-creation tool refuse it at runtime).

Each acquisition system's trial vocabulary and the nested schemas of its experiment configuration are derived by
introspection from that system's `<System>ExperimentConfiguration` dataclass.

### Code standards

- Apache-2.0 licensed; license string lives in `pyproject.toml` and is mirrored in `LICENSE`
- Python 3.14 only (`requires-python = ">=3.14,<3.15"`)
- MyPy in strict mode (equivalent to `--strict`), with `extra_checks` and `pretty` output enabled in `pyproject.toml`
- Google-style docstrings, 120-character line limit
- Ruff for formatting and linting; `pyproject.toml` declares the project-specific lint ignores
- See `/python-style` for complete conventions

### Project-specific conventions

- **Library naming in prose**: Write `sollertia-shared-assets`, not `slsa`, in documentation, comments, and commit
  messages. The short form is reserved for the CLI entry point and the mamba environment name (`slsa_dev`).
- **Minimal machinery**: Prefer concrete classes, explicit `Path` fields, and `if`/`elif` dispatch over ABCs,
  `@property`-derived state, back-references, or unnecessary registries. The registries and the `SYSTEM_SESSION_TYPES`
  association listed above are necessary because they cross enum boundaries; do not add more without justification.
- **No tests for MCP tools**: `@mcp.tool()` functions live behind the FastMCP server and are excluded from coverage.
  Test the helper functions they delegate to instead.
- **Frozen acquisition snapshots**: Every per-session YAML in `raw_data/` (descriptor, hardware state, system
  configuration, experiment configuration, VR configuration, surgery metadata) is an immutable record of the
  session's acquisition context. MCP write tools repair corruption; they do not edit live runtime state.

### Workflow guidance

**Adding a new session type or acquisition system:**

Invoke `/library-extension`. It enumerates every registry and sibling-skill update required, including the README's
"Adding New Session Types" / "Adding New Acquisition Systems" sections.

**Modifying configuration dataclasses:**

1. Read the relevant module: shared primitives live under `src/sollertia_shared_assets/configuration/`,
   system-specific experiment configurations under the system's subpackage (e.g.,
   `mesoscope_vr/experiment_configuration.py`)
2. Preserve the `YamlConfig` inheritance — downstream libraries serialize and deserialize these
3. Update `__post_init__` validation when adding fields with cross-field constraints
4. Run `tox -e lint` and verify no field renames break sollertia-experiment or sollertia-forgery

**Modifying session or descriptor dataclasses:**

1. Read the relevant module: `SessionData` and the hierarchy views live under
   `src/sollertia_shared_assets/data_hierarchy/`, per-system descriptors and raw-data layouts under the system's
   subpackage (e.g., `mesoscope_vr/runtime_data.py`, `mesoscope_vr/raw_data.py`)
2. New canonical filenames require an entry in `RawDataFiles` (`data_hierarchy/session_data.py`) or a system-specific
   `*RawDataFiles` enum (`<system>/raw_data.py`)
3. New canonical subdirectories require an entry in `Directories` or a system-specific `*Directories` enum
4. New required `raw_data` assets require updating `SessionData.required_raw_assets` in
   `data_hierarchy/session_data.py` (for a session type that runs the corridor task, add it to the
   `SESSION_TYPES_USING_VR_TASK` gate in `registries.py`)

**Adding or modifying MCP tools:**

1. Add the `@mcp.tool()`-decorated function to the appropriate module under `src/sollertia_shared_assets/interfaces/`
2. Use `ok_response(...)` and `error_response(...)` from `mcp_instance` for all responses
3. Document the response key shape in the `Returns` docstring section — it is part of the public contract
4. Update the README's MCP tool table, ensuring each row description matches the source docstring summary, and
   re-run `tox -e docs` to regenerate the API documentation

**Running tests, linting, and the docs build:**

```bash
tox -e lint                # ruff format + ruff check + mypy
tox -e stubs               # generate .pyi stubs after lint passes
tox -e py314-test          # run pytest with coverage
tox -e coverage            # combine and render coverage report
tox -e docs                # build Sphinx HTML documentation
tox -e build               # build sdist + wheel
```

The `tox` envlist runs `uninstall → export → lint → stubs → py314-test → coverage → docs → build → install` end to end.
