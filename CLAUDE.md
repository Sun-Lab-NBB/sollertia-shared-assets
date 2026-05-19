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

The sollertia marketplace ships an `assets` plugin with skills that target this library directly. The ataraxis
marketplace ships the `automation` plugin used across all Sun Lab repositories.

| Skill                           | Description                                                                  |
|---------------------------------|------------------------------------------------------------------------------|
| `/explore-codebase`             | Perform in-depth codebase exploration at session start                       |
| `/python-style`                 | Apply Sun Lab Python coding conventions (REQUIRED for Python changes)        |
| `/readme-style`                 | Apply Sun Lab README conventions (REQUIRED for README changes)               |
| `/commit`                       | Draft Sun Lab style-compliant git commit messages                            |
| `/pyproject-style`              | Apply Sun Lab pyproject.toml conventions                                     |
| `/tox-config`                   | Apply Sun Lab tox.ini conventions                                            |
| `/api-docs`                     | Apply Sun Lab Sphinx documentation conventions                               |
| `/project-layout`               | Apply Sun Lab project directory structure conventions                        |
| `/skill-design`                 | Generate, update, and verify skill files and this CLAUDE.md                  |
| `/audit-facts`                  | Audit documentation files against source code for factual accuracy           |
| `/audit-style`                  | Audit files against applicable style skill checklists for compliance         |
| `/assets-mcp-environment-setup` | Diagnose and resolve `slsa mcp` server connectivity issues                   |
| `/working-directory`            | Initialize the working directory, Google credentials, and templates path     |
| `/project-hierarchy`            | Discover the project / animal / session tree under the data root             |
| `/session-discovery`            | Discover and filter sessions by date, animal, or name (`session_paths` flow) |
| `/session-data`                 | Read, write, and validate `session_data.yaml` markers                        |
| `/session-descriptors`          | Read, write, and validate per-session-type `session_descriptor.yaml` files   |
| `/session-hardware-state`       | Read, write, and validate `hardware_state.yaml` snapshots                    |
| `/subject-metadata`             | Read and amend `surgery_metadata.yaml` SurgeryData files                     |
| `/experiment-configuration`     | Author per-project `MesoscopeExperimentConfiguration` YAMLs                  |
| `/task-templates`               | Author and validate reusable Unity `TaskTemplate` YAMLs                      |
| `/library-extension`            | Orchestrate cross-cutting changes when extending the library's vocabulary    |

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
| CLI entry point     | `interfaces/cli.py`                 | `slsa` Click group: `mcp` + `configure` subcommands                |
| Server bootstrap    | `interfaces/mcp_server.py`          | Imports tool modules to trigger registration; exposes `run_server` |
| Shared MCP instance | `interfaces/mcp_instance.py`        | FastMCP instance, registries, response helpers, validators         |
| Configuration tools | `interfaces/configuration_tools.py` | working dir, Google creds, templates dir, experiments              |
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

| Directory                                          | Purpose                                                          |
|----------------------------------------------------|------------------------------------------------------------------|
| `src/sollertia_shared_assets/configuration/`       | VR-task and experiment configuration dataclasses (YamlConfig)    |
| `src/sollertia_shared_assets/data_classes/`        | Session, descriptor, and surgery dataclasses + discovery helpers |
| `src/sollertia_shared_assets/interfaces/`          | `slsa` CLI and FastMCP server with all MCP tool modules          |
| `tests/`                                           | Test suite (configuration and data-classes only; MCP excluded)   |
| `docs/`                                            | Sphinx API documentation source                                  |
| `envs/`                                            | Conda/mamba development environment specifications               |

### Architecture

- **Configuration layer**: `TaskTemplate` (system-agnostic Unity template) and `MesoscopeExperimentConfiguration`
  (Mesoscope-VR experiment config) are independent siblings — both inherit directly from `YamlConfig`, neither
  inherits from the other. `create_experiment_configuration` converts a `TaskTemplate` into a
  `MesoscopeExperimentConfiguration` by mapping each `TrialStructure.trigger_type` to a `WaterRewardTrial` (for
  `TriggerType.LICK`) or `GasPuffTrial` (for `TriggerType.OCCUPANCY`).
- **Data layer**: `SessionData` is the entry point for every session on disk. `SessionData.create()` mints a new
  session, `SessionData.load()` rehydrates one. Both build runtime-only `raw_data`, `processed_data`, and
  `system_raw_data` sub-dataclasses by consulting `SYSTEM_RAW_DATA_REGISTRY`. Descriptor and hardware-state classes are
  dispatched by `SessionTypes` and `AcquisitionSystems` enum membership.
- **Interface layer**: A single `FastMCP` instance lives in `interfaces/mcp_instance.py` with shared serialization,
  validation, and registry helpers. Tool modules import the instance and register `@mcp.tool()` functions. The CLI
  (`slsa`) starts the server and exposes `configure {directory,google,templates,project,experiment}` commands.
- **Persistent host settings**: Three independent `platformdirs`-backed settings — working directory, Google
  credentials path, templates directory — are managed in `configuration/configuration_utilities.py`. Only the working
  directory is required for `slsa mcp` to function.

### Extension contracts

Five dispatch registries route polymorphic behavior off the two primary enums. Adding a new acquisition system or
session type means touching every registry below. Use the `/library-extension` skill — it owns the touch list and
the import-time parity check that fails if any registry is incomplete.

| Registry                              | File                                       | Keyed by             |
|---------------------------------------|--------------------------------------------|----------------------|
| `DESCRIPTOR_REGISTRY`                 | `interfaces/mcp_instance.py`               | `SessionTypes`       |
| `HARDWARE_STATE_REGISTRY`             | `interfaces/mcp_instance.py`               | `AcquisitionSystems` |
| `EXPERIMENT_CONFIGURATION_REGISTRY`   | `configuration/configuration_utilities.py` | `AcquisitionSystems` |
| `SYSTEM_RAW_DATA_REGISTRY`            | `data_classes/session_data.py`             | `AcquisitionSystems` |
| `_experiment_config_factory_registry` | `configuration/configuration_utilities.py` | `AcquisitionSystems` |

`_assert_registry_coverage()` in `mcp_instance.py` runs at import time and raises `RuntimeError` if any of the four
public registries is missing entries for a known enum member. `_experiment_config_factory_registry` is **not** covered
by the parity check (a missing factory only fails at call time, not at import).

A sixth structure, `_TRIAL_CLASSES` in `interfaces/configuration_tools.py`, maps trial-class **names** (e.g.,
`"WaterRewardTrial"`) to their concrete dataclasses. It is not a dispatch registry and is not parity-checked;
`list_supported_trial_types_tool` reads it to enumerate the trial vocabulary. Adding a new runtime trial class
requires a matching entry here, otherwise the new class is silently omitted from the tool's response.

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
  `@property`-derived state, back-references, or unnecessary registries. The five registries listed above are
  necessary because they cross enum boundaries; do not add more without justification.
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
4. New required `raw_data` assets require updating `_required_asset_inventory` in `interfaces/data_tools.py`

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
