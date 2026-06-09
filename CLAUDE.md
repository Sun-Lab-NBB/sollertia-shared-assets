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
consumed by `sollertia-experiment`, `sollertia-forgery`, and the `sollertia-unity-tasks` McpBridge. Local clones of all
of these typically live alongside this repository under `/home/cyberaxolotl/Desktop/GitHubRepos/`.

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
| `/working-directory`            | Initialize the working directory, Google credentials, and templates path         |
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
member, `SessionTypes` member, runtime trial class (a sibling of `WaterRewardTrial` / `GasPuffTrial`), 
`TriggerType` member, or extending the template vocabulary beyond the infinite corridor. The skill owns the touch list 
and the import-time parity check.

## MCP server

This library exposes an MCP server registered in the sollertia marketplace as part of the `assets` plugin. The server
runs through the `slsa mcp` CLI command and is consumed by AI agents working on Sollertia data. The server bootstrap,
the CLI, and all tool implementations live in `src/sollertia_shared_assets/interfaces/`:

| Module              | File                                | Surface                                                            |
|---------------------|-------------------------------------|--------------------------------------------------------------------|
| CLI entry point     | `interfaces/cli.py`                 | `slsa` Click group: `mcp` + `get` + `configure` subcommands        |
| Server bootstrap    | `interfaces/mcp_server.py`          | Imports tool modules to trigger registration; exposes `run_server` |
| Shared MCP instance | `interfaces/mcp_instance.py`        | FastMCP instance, response helpers, serialization, validators      |
| Configuration tools | `interfaces/configuration_tools.py` | working dir, data root, Google creds, templates dir, experiments   |
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
  `MesoscopeExperimentConfiguration`, the working directory, and the Google credentials path. Owns the system-level
  `MesoscopeSystemConfiguration`, which extends but does not live in this library.
- **sollertia-forgery** (data-processing pipeline). Consumes `SessionData.load`, `filter_sessions`, the working
  directory itself (per-project artifacts like `<working_dir>/<project>/manifest.feather`) and its `configuration/`
  subdirectory (where the forgery server configuration is persisted), the `ProcessingTrackers` enum,
  `MesoscopeHardwareState`, and `MesoscopeExperimentConfiguration`.
- **sollertia-unity-tasks** (Unity Editor McpBridge plugin). Consumed by `interfaces/unity_tools.py` over HTTP
  localhost; the plugin itself is authored on the Unity side.

You MUST maintain backwards compatibility for any class, constant, or filename that is exported through
`src/sollertia_shared_assets/__init__.py` unless the user explicitly requests a breaking change. When breaking
changes are necessary, coordinate with the downstream library maintainers and bump the major version.

## Project context

This is **sollertia-shared-assets**, a Python library that provides data acquisition and processing assets shared
between Sollertia platform libraries. It is part of the Sollertia AI-assisted scientific data acquisition and
processing platform, built on the Ataraxis framework, and developed in the Sun (NeuroAI) lab at Cornell University.

### Key areas

| Directory                                    | Purpose                                                                                      |
|----------------------------------------------|----------------------------------------------------------------------------------------------|
| `src/sollertia_shared_assets/configuration/` | VR-task and experiment configuration dataclasses (YamlConfig)                                |
| `src/sollertia_shared_assets/data_classes/`  | Session, descriptor, and surgery dataclasses, the read-asset registry, and discovery helpers |
| `src/sollertia_shared_assets/interfaces/`    | `slsa` CLI and FastMCP server with all MCP tool modules                                      |
| `tests/`                                     | Test suite (configuration and data-classes only; MCP excluded)                               |
| `docs/`                                      | Sphinx API documentation source                                                              |
| `envs/`                                      | Conda/mamba development environment specifications                                           |

### Architecture

- **Configuration layer**: `TaskTemplate` (system-agnostic Unity template) and `MesoscopeExperimentConfiguration`
  (Mesoscope-VR experiment config) are independent siblings — both inherit directly from `YamlConfig`, neither
  inherits from the other. Every `<System>ExperimentConfiguration` shares one contract: an `experiment_states` field
  (a mapping of `ExperimentState`, the experiment state machine; every experiment is a state machine, so this is
  required) and a `trial_structures` field (the trials the experiment runs; required, with the concrete trial classes
  varying per system). Fields beyond the contract are system-specific. `unity_scene_name` is Mesoscope-VR's addition
  as a system that uses Unity VR tasks.
  `MesoscopeExperimentConfiguration.from_task_template` converts a `TaskTemplate` into a
  `MesoscopeExperimentConfiguration` by mapping each `TrialStructure.trigger_type` to a `WaterRewardTrial` (for
  `TriggerType.LICK`) or `GasPuffTrial` (for `TriggerType.OCCUPANCY`). `create_experiment_from_vr_template_tool` and
  `TaskTemplate` are shared by every acquisition system that uses Unity VR tasks. Such a system reuses them by adding a
  `from_task_template` classmethod to its own configuration class and registering that class under its
  `AcquisitionSystems` member in `VR_TEMPLATE_CONFIG_REGISTRY` (typed by the `SupportsTaskTemplate` protocol);
  `create_experiment_from_vr_template_tool` dispatches through that registry.
  `write_experiment_configuration_tool` authors any system's configuration from a full payload. See the README's
  "Adding New Acquisition Systems" Step 6 for the full experiment-configuration creation-path recipe.
- **Data layer**: `SessionData` is the entry point for every session on disk. `SessionData.create()` mints a new
  session, `SessionData.load()` rehydrates one. Both build runtime-only `raw_data`, `processed_data`, and
  `system_raw_data` sub-dataclasses by consulting `SYSTEM_RAW_DATA_REGISTRY`. Descriptor and hardware-state classes are
  dispatched by `SessionTypes` and `AcquisitionSystems` enum membership.
- **Interface layer**: A single `FastMCP` instance lives in `interfaces/mcp_instance.py` with shared serialization,
  validation, and dataclass-introspection helpers; the dispatch registries and their import-time checks live in the
  data layer's extension-point hub (`data_classes/extensions.py`), not here. Tool modules import the instance and
  register `@mcp.tool()` functions. The CLI
  (`slsa`) starts the server and exposes `configure {directory,data-root,google,templates,project}` and
  `get {directory,data-root,google,templates,projects,experiments}` command groups.
- **Persistent host settings**: Four independent `platformdirs`-backed settings — working directory, data root,
  Google credentials path, templates directory — are managed in `configuration/configuration_utilities.py`. Only the
  working directory is required for `slsa mcp` to function.

### Extension contracts

Five registries route polymorphic behavior off three enums — the two primary enums (`SessionTypes`,
`AcquisitionSystems`) plus the read-asset enum (`ReadAssets`). A sixth structure, `SYSTEM_SESSION_TYPES`, is an
association keyed by `AcquisitionSystems` that records which session types each acquisition system can run. Adding a
new acquisition system or session type means touching the relevant registries below and `SYSTEM_SESSION_TYPES`;
adding a new external read asset means touching `READ_ASSET_REGISTRY`. Use the `/library-extension` skill — it owns
the touch list and the import-time parity check that fails if any registry is incomplete.

| Registry                              | File                                       | Keyed by             |
|---------------------------------------|--------------------------------------------|----------------------|
| `DESCRIPTOR_REGISTRY`                 | `data_classes/extensions.py`               | `SessionTypes`       |
| `HARDWARE_STATE_REGISTRY`             | `data_classes/extensions.py`               | `AcquisitionSystems` |
| `EXPERIMENT_CONFIGURATION_REGISTRY`   | `configuration/configuration_utilities.py` | `AcquisitionSystems` |
| `SYSTEM_RAW_DATA_REGISTRY`            | `data_classes/session_data.py`             | `AcquisitionSystems` |
| `SYSTEM_SESSION_TYPES`                | `data_classes/session_data.py`             | `AcquisitionSystems` |
| `READ_ASSET_REGISTRY`                 | `data_classes/read_assets.py`              | `ReadAssets`         |

These registries, the `SYSTEM_SESSION_TYPES` association, the `SESSION_TYPES_USING_VR_TASK` gate, and the import-time
checks that guard them are collected in the extension-point hub `data_classes/extensions.py`, which defines
`DESCRIPTOR_REGISTRY` and `HARDWARE_STATE_REGISTRY` directly and re-exports the rest from the modules that consume
them. `_assert_registry_coverage()` there runs on a bare `import sollertia_shared_assets` (the hub lives in the data
layer, so it loads without the MCP server) and raises `RuntimeError` if any of the five public dispatch registries is
missing entries for a known enum member, or if `SYSTEM_SESSION_TYPES` leaves an acquisition system with no session
types or a session type unclaimed by any system. The hub additionally runs `_assert_descriptor_contract()` (every
registered descriptor must declare the `incomplete` field the inspection tooling reads) and
`_assert_vr_template_registry_consistency()` (see below).

`VR_TEMPLATE_CONFIG_REGISTRY` in `configuration/configuration_utilities.py` is a separate, optional registry keyed by
`AcquisitionSystems`. It maps each acquisition system that uses Unity VR tasks to its experiment-configuration class,
typed by the `SupportsTaskTemplate` protocol, and `create_experiment_from_vr_template_tool` dispatches through it.
Only systems that build a configuration from a task template register here, so the dispatch-registry coverage check
does not require an entry for every system. The `_assert_vr_template_registry_consistency()` check in
`data_classes/extensions.py` does, however, verify at import that every experiment configuration providing a
`from_task_template` builder is registered here (and that every registered system provides that builder), so a
half-wired VR system fails fast instead of having its template-creation tool silently refuse it.

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

1. Read the relevant module under `src/sollertia_shared_assets/configuration/`
2. Preserve the `YamlConfig` inheritance — downstream libraries serialize and deserialize these
3. Update `__post_init__` validation when adding fields with cross-field constraints
4. Run `tox -e lint` and verify no field renames break sollertia-experiment or sollertia-forgery

**Modifying session or descriptor dataclasses:**

1. Read the relevant module under `src/sollertia_shared_assets/data_classes/`
2. New canonical filenames require an entry in `RawDataFiles` or a system-specific `*RawDataFiles` enum
3. New canonical subdirectories require an entry in `Directories` or a system-specific `*Directories` enum
4. New required `raw_data` assets require updating `SessionData.required_raw_assets` in `data_classes/session_data.py`
   (for a Unity-VR session type, add it to the `SESSION_TYPES_USING_VR_TASK` gate consumed there)

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
