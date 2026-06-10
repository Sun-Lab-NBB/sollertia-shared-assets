# sollertia-shared-assets

Provides data acquisition and processing assets shared between Sollertia platform libraries.

![PyPI - Version](https://img.shields.io/pypi/v/sollertia-shared-assets)
![PyPI - Python Version](https://img.shields.io/pypi/pyversions/sollertia-shared-assets)
[![uv](https://tinyurl.com/uvbadge)](https://github.com/astral-sh/uv)
[![Ruff](https://tinyurl.com/ruffbadge)](https://github.com/astral-sh/ruff)
![type-checked: mypy](https://img.shields.io/badge/type--checked-mypy-blue?style=flat-square&logo=python)
![PyPI - License](https://img.shields.io/pypi/l/sollertia-shared-assets)
![PyPI - Status](https://img.shields.io/pypi/status/sollertia-shared-assets)
![PyPI - Wheel](https://img.shields.io/pypi/wheel/sollertia-shared-assets)

___

## Detailed Description

This library is part of the [Sollertia](https://github.com/Sun-Lab-NBB/sollertia) AI-assisted scientific data
acquisition and processing platform, built on the [Ataraxis](https://github.com/Sun-Lab-NBB/ataraxis) framework and
developed in the Sun (NeuroAI) lab at Cornell University. It keeps the two main Sollertia libraries used for data
acquisition ([sollertia-experiment](https://github.com/Sun-Lab-NBB/sollertia-experiment)) and processing
([sollertia-forgery](https://github.com/Sun-Lab-NBB/sollertia-forgery)) independent of each other by providing the
shared assets both depend on.

The library stores dataclasses used to save data acquired with the Sollertia platform (sessions, subjects, hardware
state) and configure data acquisition and processing runtimes. It also provides a CLI (`slsa`) for platform
configuration and an MCP server with tools for agentic configuration management, session operations, and Unity Editor
integration. A subset of the MCP tools relay commands to a running Unity Editor instance via the McpBridge plugin from
[sollertia-unity-tasks](https://github.com/Sun-Lab-NBB/sollertia-unity-tasks). This subset enables agents to generate
task prefabs, manage scenes, and control Play Mode.

___

## Table of Contents

- [Dependencies](#dependencies)
- [Installation](#installation)
- [Usage](#usage)
  - [CLI Commands](#cli-commands)
  - [MCP Server](#mcp-server)
- [API Documentation](#api-documentation)
- [Developers](#developers)
  - [Adding New Session Types](#adding-new-session-types)
  - [Adding New Acquisition Systems](#adding-new-acquisition-systems)
  - [Adding a New Read Asset](#adding-a-new-read-asset)
- [Versioning](#versioning)
- [Authors](#authors)
- [License](#license)
- [Acknowledgments](#acknowledgments)

___

## Dependencies

- [Python](https://www.python.org/downloads/) **3.14** (the only currently supported interpreter version).
- An optional
  [Google service account credentials JSON file](https://cloud.google.com/iam/docs/service-account-overview),
  required only when downstream Sollertia libraries fetch subject metadata or water-restriction logs from Google Sheets.
- An optional running [Unity Editor](https://unity.com/download) instance with the McpBridge plugin from
  [sollertia-unity-tasks](https://github.com/Sun-Lab-NBB/sollertia-unity-tasks), required only by the MCP tools that
  generate task prefabs, manage scenes, and control Play Mode.

For users, all other library dependencies are installed automatically by all supported installation methods. For
developers, see the [Developers](#developers) section for information on installing additional development
dependencies.

___

## Installation

### Source

***Note,*** installation from source is ***highly discouraged*** for anyone who is not an active
project developer.

1. Download this repository to the local machine using the preferred method, such as git-cloning.
   Use one of the [stable releases](https://github.com/Sun-Lab-NBB/sollertia-shared-assets/tags)
   that include precompiled binary and source code distribution (sdist) wheels.
2. If the downloaded distribution is stored as a compressed archive, unpack it using the
   appropriate decompression tool.
3. `cd` to the root directory of the prepared project distribution.
4. Run `pip install .` to install the project and its dependencies.

### pip

Use the following command to install the library and all of its dependencies via
[pip](https://pip.pypa.io/en/stable/): `pip install sollertia-shared-assets`

___

## Usage

Most library components are intended to be used via other Sollertia platform libraries. For details on using shared
assets for data acquisition and preprocessing, see the
[sollertia-experiment](https://github.com/Sun-Lab-NBB/sollertia-experiment) library. For details on using shared assets
for data processing and dataset formation, see the
[sollertia-forgery](https://github.com/Sun-Lab-NBB/sollertia-forgery) library.

***Warning!*** End users should not use any component of this library directly or install this library into any Python
environment. All assets from this library are intended to be used exclusively by developers working on other Sollertia
platform libraries.

### CLI Commands

This library provides the `slsa` CLI that exposes the following commands and command groups:

| Command                 | Description                                                           |
|-------------------------|-----------------------------------------------------------------------|
| `mcp`                   | Starts the MCP server for agentic configuration management            |
| `get directory`         | Reports the configured local Sollertia platform working directory     |
| `get data-root`         | Reports the configured local Sollertia platform data root             |
| `get credentials`       | Reports the path to the requested category's credentials file         |
| `get templates`         | Reports the configured sollertia-unity-tasks task templates directory |
| `get projects`          | Lists the projects stored under the data root                         |
| `get experiments`       | Lists the experiment configurations available for a project           |
| `configure directory`   | Sets the local Sollertia platform working directory                   |
| `configure data-root`   | Sets the local Sollertia platform data root                           |
| `configure credentials` | Copies a credentials file into the platform credentials directory     |
| `configure templates`   | Sets the path to the sollertia-unity-tasks task templates directory   |
| `configure project`     | Creates a project directory structure for data acquisition            |

Use `slsa --help`, `slsa get --help`, `slsa configure --help`, or `slsa COMMAND --help` for detailed usage
information.

### MCP Server

This library provides an MCP server that exposes configuration management, session and dataset operations, and Unity
Editor relay tools for AI agent integration. The server enables agents to query and configure shared Sollertia platform
workflow components.

#### Starting the Server

Start the MCP server using the CLI:

```bash
slsa mcp
```

The server defaults to the `stdio` transport. Use the `-t/--transport` flag to select one of `stdio`, `sse`, or
`streamable-http`.

#### Available Tools

| Tool                                            | Description                                                                                    |
|-------------------------------------------------|------------------------------------------------------------------------------------------------|
| `create_experiment_from_vr_template_tool`       | Creates an experiment configuration from a Unity VR task template using sensible defaults      |
| `create_project_tool`                           | Creates the on-disk directory structure for a new project under a data root                    |
| `create_task_tool`                              | Builds a Unity task end-to-end from a template: task prefab plus matching scene in one call    |
| `delete_asset_tool`                             | Deletes a non-scene Unity asset (cue prefabs, materials) within the InfiniteCorridorTask root  |
| `delete_task_tool`                              | Removes a Unity task end-to-end: scene, scene companion, task prefab, and every segment prefab |
| `describe_experiment_configuration_schema_tool` | Returns the schema for the experiment configuration of a given acquisition system              |
| `describe_session_data_schema_tool`             | Returns the schema for the SessionData dataclass                                               |
| `describe_session_descriptor_schema_tool`       | Returns the schema for the descriptor associated with a given session type                     |
| `describe_session_hardware_state_schema_tool`   | Returns the hardware-state schema for a given acquisition system                               |
| `describe_data_asset_schema_tool`               | Returns the read-asset dataclass schema for the given data_asset                               |
| `describe_template_schema_tool`                 | Returns the schema for TaskTemplate and nested Cue, TrialStructure, and VREnvironment          |
| `discover_experiments_tool`                     | Discovers all experiment configuration YAML files under the data root                          |
| `discover_templates_tool`                       | Lists all task templates in the configured templates directory                                 |
| `enter_play_mode_tool`                          | Enters Play Mode in the Unity Editor                                                           |
| `exit_play_mode_tool`                           | Exits Play Mode in the Unity Editor                                                            |
| `filter_sessions_tool`                          | Filters discovered session entries by \date range and animal- or session-name criteria         |
| `get_data_root_overview_tool`                   | Builds the project/animal/session hierarchy and status; optionally surfaces empty directories  |
| `get_platform_environment_status_tool`          | Reports the status of the working directory, data root, templates directory, and credentials   |
| `get_play_state_tool`                           | Returns the current Unity Editor play state and active scene name                              |
| `inspect_prefab_tool`                           | Returns the full hierarchy, components, transforms, and collider details of a prefab           |
| `inspect_scene_tool`                            | Returns the active scene's metadata, dirty flag, and recursive root GameObject hierarchy       |
| `inspect_sessions_tool`                         | Produces a detailed health and inventory report for one or more sessions                       |
| `list_assets_tool`                              | Lists Unity assets of a given type within a search path                                        |
| `list_processing_trackers_tool`                 | Enumerates the canonical ProcessingTracker filenames written by each pipeline                  |
| `list_scenes_tool`                              | Lists all Unity scene assets and identifies the currently active scene                         |
| `list_session_type_support_tool`                | Returns the full mapping of each acquisition system to the session types it can run            |
| `list_supported_acquisition_systems_tool`       | Enumerates the acquisition systems supported by the Sollertia platform                         |
| `list_supported_credentials_tool`               | Enumerates the credentials categories supported by the Sollertia platform                      |
| `list_supported_data_assets_tool`               | Enumerates the read-asset data formats supported by the Sollertia platform                     |
| `list_supported_session_types_tool`             | Enumerates session types, optionally scoped to one acquisition system                          |
| `list_supported_trial_types_tool`               | Enumerates the trial classes supported by an acquisition system's experiment configuration     |
| `list_supported_trigger_types_tool`             | Enumerates the trigger type values supported by trial structures                               |
| `open_scene_tool`                               | Opens a Unity scene in the Editor with explicit unsaved-edits handling                         |
| `read_credentials_tool`                         | Returns the path to the requested credentials file in the platform credentials directory       |
| `read_data_root_tool`                           | Returns the configured Sollertia platform data root path                                       |
| `read_experiment_configuration_tool`            | Loads an experiment configuration YAML (project source or per-session frozen snapshot)         |
| `read_session_data_tool`                        | Loads a session_data.yaml file via the SessionData schema                                      |
| `read_session_descriptor_tool`                  | Loads a session descriptor YAML using the descriptor class for the given session type          |
| `read_session_hardware_state_tool`              | Loads a hardware-state YAML for a session using the class for the given acquisition system     |
| `read_data_asset_tool`                          | Loads a read-asset YAML, parsing it with the dataclass for the given data_asset                |
| `read_task_parameters_tool`                     | Reads the Unity Editor's Task Parameters window state, options, and per-control visibility     |
| `read_task_templates_directory_tool`            | Returns the configured path to the task templates directory                                    |
| `read_template_tool`                            | Loads a TaskTemplate YAML (live template or per-session frozen snapshot)                       |
| `read_working_directory_tool`                   | Returns the configured Sollertia platform working directory path                               |
| `set_credentials_tool`                          | Copies a credentials file into the platform credentials directory under its canonical name     |
| `set_data_root_tool`                            | Sets the local Sollertia platform data root                                                    |
| `set_task_templates_directory_tool`             | Sets the path to the task templates directory                                                  |
| `set_working_directory_tool`                    | Sets the local Sollertia platform working directory                                            |
| `validate_experiment_configuration_tool`        | Validates an experiment configuration YAML for a project                                       |
| `validate_template_tool`                        | Validates a TaskTemplate (live or session snapshot) against its schema and constraints         |
| `write_experiment_configuration_tool`           | Creates or replaces an experiment configuration YAML for a project                             |
| `write_session_data_tool`                       | Creates or replaces a session_data.yaml file, validated against the SessionData schema         |
| `write_session_descriptor_tool`                 | Creates or replaces a session descriptor YAML for a session                                    |
| `write_session_hardware_state_tool`             | Creates or replaces a session's hardware-state YAML using the acquisition-system dataclass     |
| `write_data_asset_tool`                         | Creates or replaces a read-asset YAML, validated against the given data_asset's dataclass      |
| `write_task_parameters_tool`                    | Writes a subset of the Unity Editor's Task Parameters fields atomically in one relay call      |
| `write_template_tool`                           | Creates or replaces a live TaskTemplate YAML in the configured templates directory             |

***Note,*** tools that interact with Unity (`create_task_tool`, `delete_asset_tool`, `delete_task_tool`,
`enter_play_mode_tool`, `exit_play_mode_tool`, `get_play_state_tool`, `inspect_prefab_tool`, `inspect_scene_tool`,
`list_assets_tool`, `list_scenes_tool`, `open_scene_tool`, `read_task_parameters_tool`, `write_task_parameters_tool`)
require the Unity Editor to be running on the local machine with the McpBridge plugin from
[sollertia-unity-tasks](https://github.com/Sun-Lab-NBB/sollertia-unity-tasks) active. These tools relay commands to the
Editor via HTTP.

#### Client Registration

MCP server registration and Claude Code skill assets for this library are distributed through the
[sollertia](https://github.com/Sun-Lab-NBB/sollertia) marketplace as part of the **assets** plugin. Install the
plugin from the marketplace to automatically register the MCP server with compatible clients and make all associated
skills available.

___

## API Documentation

See the [API documentation](https://sollertia-shared-assets-api-docs.netlify.app/) for the detailed description of the
methods and classes exposed by components of this library.

***Note,*** the API documentation includes additional details about the `slsa` CLI commands and their
parameters beyond what is covered in the [CLI Commands](#cli-commands) section above.

___

## Developers

This section provides installation, dependency, and build-system instructions for the developers
that want to modify the source code of this library.

### Installing the Project

***Note,*** this installation method requires **mamba version 2.3.2 or above**. Currently, all
Sollertia Platform automation pipelines require that mamba is installed through the
[miniforge3](https://github.com/conda-forge/miniforge) installer.

1. Download this repository to the local machine using the preferred method, such as git-cloning.
2. If the downloaded distribution is stored as a compressed archive, unpack it using the
   appropriate decompression tool.
3. `cd` to the root directory of the prepared project distribution.
4. Install the core Sollertia Platform development dependencies into the ***base*** mamba environment via the
   `mamba install tox uv tox-uv` command.
5. Use the `tox -e create` command to create the project-specific development environment followed
   by `tox -e install` command to install the project into that environment as a library.

### Additional Dependencies

In addition to installing the project and all user dependencies, install the following
dependencies:

1. [Python](https://www.python.org/downloads/) distributions, one for each version supported by
   the developed project. Currently, this library supports Python 3.14 only. It is recommended to
   use a tool like [pyenv](https://github.com/pyenv/pyenv) to install and manage the required
   versions.

### Development Automation

This project uses `tox` for development automation. The following tox environments are available:

| Environment    | Description                                                  |
|----------------|--------------------------------------------------------------|
| `lint`         | Runs ruff formatting, ruff linting, and mypy type checking   |
| `stubs`        | Generates py.typed marker and .pyi stub files                |
| `py314-test`   | Runs the test suite via pytest for Python 3.14               |
| `coverage`     | Aggregates test coverage into an HTML report                 |
| `docs`         | Builds the API documentation via Sphinx                      |
| `build`        | Builds sdist and wheel distributions                         |
| `upload`       | Uploads distributions to PyPI via twine                      |
| `install`      | Builds and installs the project into its mamba environment   |
| `uninstall`    | Uninstalls the project from its mamba environment            |
| `create`       | Creates the project's mamba development environment          |
| `remove`       | Removes the project's mamba development environment          |
| `provision`    | Recreates the mamba environment from scratch                 |
| `export`       | Exports the mamba environment as .yml and spec.txt files     |
| `import`       | Creates or updates the mamba environment from a .yml file    |

Run any environment using `tox -e ENVIRONMENT`. For example, `tox -e lint`.

***Note,*** all pull requests for this project have to successfully complete the `tox` task before
being merged. To expedite the task's runtime, use the `tox --parallel` command to run some tasks
in parallel.

### Adding New Session Types

A session type identifies the high-level activity performed during acquisition (e.g., training, experiment,
window-checking). Each type has its own descriptor dataclass that captures the type-specific task parameters and
outcome metadata, persisted as `session_descriptor.yaml` inside the session's `raw_data` directory. The descriptor
filename is flat across all types — only the parsing class varies, and is dispatched via `DESCRIPTOR_REGISTRY`.

**Step 1: Extend the SessionTypes enum and pair it with an acquisition system**

In `enums.py`, add a new member to `SessionTypes`:

```python
class SessionTypes(StrEnum):
    LICK_TRAINING = "lick training"
    RUN_TRAINING = "run training"
    MESOSCOPE_EXPERIMENT = "mesoscope experiment"
    WINDOW_CHECKING = "window checking"
    NEW_TYPE = "new type"  # Add new session type here
```

Then, in `registries.py`, add the new member to the `SYSTEM_SESSION_TYPES` frozenset of every acquisition system that
can run it. The import-time parity check (`_assert_registry_coverage`) raises if any session type is claimed by no
acquisition system, and `SessionData.create()` rejects a session type that is not paired with the session's
acquisition system.

**Step 2: Add the descriptor dataclass**

Add a `<Type>Descriptor` dataclass inheriting from `YamlConfig` that captures the task parameters and outcome
metadata for the new session type. Each acquisition system keeps its runtime dataclasses in the `runtime_data.py`
module of its own subpackage; add the descriptor to the subpackage of the system that runs the new session type. Use
`LickTrainingDescriptor` or `RunTrainingDescriptor` in `mesoscope_vr/runtime_data.py` as reference. Export the new
class from the subpackage's `__init__.py`.

**Step 3: Register the descriptor**

In `registries.py` (the registry hub):

1. Import the new descriptor class from its system subpackage.
2. Register it in `DESCRIPTOR_REGISTRY` under the new `SessionTypes` key.

**Step 4: Update required-asset checks (if applicable)**

The required-asset policy lives in `SessionData.required_raw_assets` (`data_hierarchy/session_data.py`), and the
session inventory tool delegates to it. The policy is data-driven rather than a per-session-type branch: every session
requires `session_descriptor.yaml` and `system_configuration.yaml`; `experiment_configuration.yaml` is required
whenever the session has an `experiment_name`; and `vr_configuration.yaml` is required for any session type listed in
`SESSION_TYPES_USING_VR_TASK` (`registries.py`). If the new session type runs the linear infinite corridor task, add
it to that frozenset; if it requires some other extra asset, extend `required_raw_assets` accordingly.

**Step 5: Update downstream libraries**

Coordinate with sollertia-experiment, which is the package that actually creates sessions of the new type during
acquisition.

### Adding New Acquisition Systems

An acquisition system identifies a hardware platform that can produce a session (e.g., the Mesoscope-VR system).
Each system contributes its own hardware-state snapshot, experiment-configuration schema, and a system-specific raw
data dataclass that resolves the system's unique on-disk assets. All of these classes live together in the system's
own subpackage (e.g., `mesoscope_vr/`). Three registries dispatch parsing and builder classes by `AcquisitionSystems`
value: `HARDWARE_STATE_REGISTRY`, `EXPERIMENT_CONFIGURATION_REGISTRY`, and `SYSTEM_RAW_DATA_REGISTRY`. Each system
must also declare the session types it can run in `SYSTEM_SESSION_TYPES`. Every registry, the `SYSTEM_SESSION_TYPES`
association, and the import-time checks that guard them are defined — fully populated — in the top-level
`registries.py` module. System-level hardware and software configuration classes live in the acquisition runtime
package (sollertia-experiment).

**Step 1: Extend the AcquisitionSystems enum**

In `enums.py`, add a new member to `AcquisitionSystems`:

```python
class AcquisitionSystems(StrEnum):
    MESOSCOPE_VR = "mesoscope"
    NEW_SYSTEM = "new_system"  # Add new system here
```

**Step 2: Create the system subpackage**

Create a new `<system>/` subpackage (a sibling of `mesoscope_vr/`) holding the new system's dataclasses, and export
every class from the subpackage's `__init__.py`. The Mesoscope-VR subpackage is the reference for both the module
split and the contents:

1. `<system>/runtime_data.py` — a `<System>HardwareState` dataclass inheriting from `YamlConfig` that records the
   configuration of every active hardware module on the new system, plus the system's per-session-type descriptors.
   Use `mesoscope_vr/runtime_data.py` as reference.
2. `<system>/experiment_configuration.py` — a `<System>ExperimentConfiguration` dataclass inheriting from
   `YamlConfig` that captures the runtime experiment parameters for the new system. Every
   `<System>ExperimentConfiguration` shares one contract: an `experiment_states` field (a mapping of
   `ExperimentState`, the experiment state machine that every experiment runs as), a `trial_structures` field (the
   trials the experiment runs, whose concrete trial classes vary per system), a `unity_scene_name` field (the linear
   infinite corridor task the experiment runs), and a `from_task_template` classmethod that builds the configuration
   from a task template. Fields beyond that contract are system-specific. Use
   `mesoscope_vr/experiment_configuration.py` as reference.
3. `<system>/raw_data.py` — a `<System>RawData` `@dataclass(slots=True)` that holds the absolute paths to all
   system-specific raw assets and exposes a `build(cls, root: Path) -> <System>RawData` classmethod that resolves
   every field against the session's `raw_data` directory. Optionally add `<System>RawDataFiles` and/or
   `<System>Directories` `StrEnum` classes that enumerate any canonical filenames or subdirectories unique to the
   new system's `raw_data`. Use `mesoscope_vr/raw_data.py` as reference.

**Step 3: Register the dispatch classes**

In `registries.py` (the registry hub), import the new classes from the system subpackage and add an entry for the
new system to each registry:

1. Add `<System>HardwareState` to `HARDWARE_STATE_REGISTRY`.
2. Add `<System>ExperimentConfiguration` to `EXPERIMENT_CONFIGURATION_REGISTRY`. `SessionData.create()` consults this
   registry to load the per-session experiment configuration snapshot and cache the matching corridor task template.
3. Add `<System>RawData` to `SYSTEM_RAW_DATA_REGISTRY`. `SessionData` consults this registry to build the
   runtime-only `system_raw_data` sub-dataclass attribute, so this step is what wires the new system into session
   loading.
4. Add a `SYSTEM_SESSION_TYPES` entry mapping the new `AcquisitionSystems` key to the `frozenset` of `SessionTypes`
   the system can run. The parity check raises if a system declares no session types, and `SessionData.create()`
   uses this set to reject session-type / system pairings the system does not support.

**Step 4: Implement the experiment-configuration creation path**

Every Sollertia acquisition system builds its experiment configuration from a Unity VR task template through the shared
`create_experiment_from_vr_template_tool`, so no new tool is needed. Add a `from_task_template` classmethod to the
system's `<System>ExperimentConfiguration` dataclass that maps the template's trial structures to the system's runtime
trials and seeds the default runtime states. The tool dispatches through `EXPERIMENT_CONFIGURATION_REGISTRY` to the
registered class's `from_task_template`, and the import-time `_assert_experiment_configuration_contract` check fails
fast if the builder or any contract field is missing. Use `MesoscopeExperimentConfiguration.from_task_template` as
reference. The generic `write_experiment_configuration_tool` remains available to author or repair a full payload
directly.

**Step 5: Update downstream libraries**

Coordinate with sollertia-experiment (which owns the system-level hardware/software configuration classes and the
acquisition runtime) and sollertia-forgery (data processing) as needed.

### Adding a New Read Asset

A **read asset** is metadata the platform reads from an external, human-maintained source (for example, the surgery
log Google Sheet). The concrete architecture decision is that every read asset is translated by the acquisition
library (sollertia-experiment) into a typed dataclass and cached on disk in a standardized format. Downstream
consumers (notably sollertia-forgery) then interact only with that on-disk dataclass and never touch the external
source. Because the dataclass is the canonical format, it is reusable regardless of the upstream storage — the
acquisition library translates whatever source it reads (Google Sheets or otherwise) into it.

This applies only to assets the platform **reads**. Assets the platform only **writes** to an external source (for
example, the water-restriction log) have no on-disk representation to standardize, so they need no dataclass and no
registry entry — they are owned entirely by the writing library.

`ReadAssets` (in `enums.py`) enumerates the supported read-asset formats and `READ_ASSET_REGISTRY` (in
`registries.py`) maps each to its on-disk dataclass. The contract dataclasses themselves live in the `data_classes/`
package. Unlike the acquisition-system registries, this is a contract surface curated by Sollertia platform
maintainers: each entry is a durable translation contract, and adding one is a platform-contract decision rather
than a routine extension. The import-time parity check (`_assert_registry_coverage`) enforces that every
`ReadAssets` member has a registered dataclass.

**Step 1: Add the contract dataclass**

In `data_classes/`, add a new module holding the concrete on-disk representation as a dataclass inheriting from
`YamlConfig` (use `data_classes/surgery_data.py`'s `SurgeryData` as reference). Contract modules export plain
dataclasses and never consume the dispatch registries. Export the new class from `data_classes/__init__.py`.

**Step 2: Extend the ReadAssets enum**

In `enums.py`, add a new member to `ReadAssets`:

```python
class ReadAssets(StrEnum):
    SURGERY_DATA = "surgery_data"
    NEW_ASSET = "new_asset"  # Add new read-asset format here
```

**Step 3: Register the dataclass**

In `registries.py`, register it in `READ_ASSET_REGISTRY` under the new `ReadAssets` key:

```python
READ_ASSET_REGISTRY: dict[ReadAssets, type[YamlConfig]] = {
    ReadAssets.SURGERY_DATA: SurgeryData,
    ReadAssets.NEW_ASSET: NewAsset,
}
```

The parity check catches a forgotten registry entry at import time, naming the missing member.

**Step 4: Wire the translation downstream**

Coordinate with sollertia-experiment, which reads the external source, translates it into the new dataclass, and
caches it on disk for sollertia-forgery to consume. This is the only place that knows the source's storage-specific
representation; the dataclass keeps every downstream consumer storage-agnostic.

### AI-Assisted Development

Claude Code skills and AI development assets for this project are distributed through two marketplaces:

- [sollertia](https://github.com/Sun-Lab-NBB/sollertia) marketplace:
  - **assets** plugin — registers the `slsa mcp` server with compatible MCP clients and provides configuration and
    data skills for working directory setup, session discovery, session data, descriptors, hardware state, subject
    metadata, task templates, experiment configuration, library extension, and MCP environment setup. The server also
    fronts the Unity Editor relay that the **unity** plugin's skills drive.
  - **unity** plugin — Unity Editor skills that drive the `McpBridge` relay tools served by the `slsa mcp` server,
    document the MQTT contract and `CreateTask` pipeline, and guide manufacturing of new trigger zone prefabs.
- [ataraxis](https://github.com/Sun-Lab-NBB/ataraxis) marketplace:
  - **automation** plugin — shared development skills that enforce Sollertia Platform coding conventions (Python
    style, README style, commit messages, pyproject.toml, tox configuration) and general-purpose codebase
    exploration tools.

Install all three plugins to make the full skill set available to compatible AI coding agents. The **unity** plugin
depends on the **assets** plugin for the backing `slsa mcp` server that drives the Unity Editor relay.

### Automation Troubleshooting

Many packages used in `tox` automation pipelines (uv, mypy, ruff) and `tox` itself may experience
runtime failures. In most cases, this is related to their caching behavior. If an unintelligible
error is encountered with any of the automation components, deleting the corresponding cache
directories (`.tox`, `.ruff_cache`, `.mypy_cache`, etc.) manually or via a CLI command typically
resolves the issue.

___

## Versioning

This project uses [semantic versioning](https://semver.org/). See the
[tags on this repository](https://github.com/Sun-Lab-NBB/sollertia-shared-assets/tags) for the available project
releases.

___

## Authors

- Ivan Kondratyev ([Inkaros](https://github.com/Inkaros))
- Kushaan Gupta ([kushaangupta](https://github.com/kushaangupta))
- Natalie Yeung

___

## License

This project is licensed under the Apache 2.0 License: see the [LICENSE](LICENSE) file for
details.

___

## Acknowledgments

- All Sun lab [members](https://neuroai.github.io/sunlab/people) for providing the inspiration
  and comments during the development of this library.
- The creators of all other dependencies and projects listed in the
  [pyproject.toml](pyproject.toml) file.
