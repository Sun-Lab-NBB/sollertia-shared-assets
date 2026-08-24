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
configuration and an MCP server with tools for agentic configuration management, session and dataset operations, and
Unity Editor integration. A subset of those tools relays commands to a running Editor via the McpBridge plugin from
[sollertia-virtual-reality](https://github.com/Sun-Lab-NBB/sollertia-virtual-reality).

___

## Table of Contents

- [Dependencies](#dependencies)
- [Installation](#installation)
  - [Source](#source)
  - [pip](#pip)
- [Usage](#usage)
  - [CLI Commands](#cli-commands)
  - [MCP Server](#mcp-server)
- [API Documentation](#api-documentation)
- [Developers](#developers)
  - [Installing the Project](#installing-the-project)
  - [Additional Dependencies](#additional-dependencies)
  - [Development Automation](#development-automation)
  - [Adding New Session Types](#adding-new-session-types)
  - [Adding New Acquisition Systems](#adding-new-acquisition-systems)
  - [Adding a New Trial Class](#adding-a-new-trial-class)
  - [Adding a New Trigger Type](#adding-a-new-trigger-type)
  - [Adding a New Read Asset](#adding-a-new-read-asset)
  - [AI-Assisted Development](#ai-assisted-development)
  - [Automation Troubleshooting](#automation-troubleshooting)
- [Versioning](#versioning)
- [Authors](#authors)
- [License](#license)
- [Acknowledgments](#acknowledgments)

___

## Dependencies

- [Python](https://www.python.org/downloads/) **3.14** (the only currently supported interpreter version).
- An optional [Google service account credentials JSON
  file](https://cloud.google.com/iam/docs/service-account-overview), required only when downstream Sollertia libraries
  read subject metadata from, or write water-restriction logs to, Google Sheets.
- An optional running [Unity Editor](https://unity.com/download) instance with the McpBridge plugin from
  [sollertia-virtual-reality](https://github.com/Sun-Lab-NBB/sollertia-virtual-reality), required only by the MCP
  tools that generate task prefabs, manage scenes, and control Play Mode.

For users, all other library dependencies are installed automatically by all supported installation methods. For
developers, see the [Developers](#developers) section for information on installing additional development
dependencies.

___

## Installation

### Source

***Note,*** installation from source is ***highly discouraged*** for anyone who is not an active project developer.

1. Download this repository to the local machine using the preferred method, such as git-cloning. Use one of the
   [stable releases](https://github.com/Sun-Lab-NBB/sollertia-shared-assets/tags) that include precompiled binary and
   source code distribution (sdist) wheels.
2. If the downloaded distribution is stored as a compressed archive, unpack it using the appropriate decompression
   tool.
3. `cd` to the root directory of the prepared project distribution.
4. Run `pip install .` to install the project and its dependencies.

### pip

Use the following command to install the library and all of its dependencies via [pip](https://pip.pypa.io/en/stable/):
`pip install sollertia-shared-assets`

___

## Usage

Most library components are intended to be used via other Sollertia platform libraries. For details on using shared
assets for data acquisition and preprocessing, see the
[sollertia-experiment](https://github.com/Sun-Lab-NBB/sollertia-experiment) library. For details on using shared assets
for data processing and dataset formation, see the [sollertia-forgery](https://github.com/Sun-Lab-NBB/sollertia-forgery)
library.

***Warning!*** End users should not use any component of this library directly or install this library into any Python
environment. All assets from this library are intended to be used exclusively by developers working on other Sollertia
platform libraries.

### CLI Commands

This library provides the `slsa` CLI that exposes the following commands and command groups:

| Command                 | Description                                                               |
|-------------------------|---------------------------------------------------------------------------|
| `mcp`                   | Starts the MCP server for agentic configuration management                |
| `get directory`         | Reports the configured local Sollertia platform working directory         |
| `get data-root`         | Reports the configured local Sollertia platform data root                 |
| `get credentials`       | Reports the path to the requested category's credentials file             |
| `get templates`         | Reports the configured sollertia-virtual-reality task templates directory |
| `get projects`          | Lists the projects stored under the data root                             |
| `get experiments`       | Lists the experiment configurations available for a project               |
| `configure directory`   | Sets the local Sollertia platform working directory                       |
| `configure data-root`   | Sets the local Sollertia platform data root                               |
| `configure credentials` | Copies a credentials file into the platform credentials directory         |
| `configure templates`   | Sets the path to the sollertia-virtual-reality task templates directory   |
| `configure project`     | Creates a project directory structure for data acquisition                |

Use `slsa --help`, `slsa get --help`, `slsa configure --help`, or `slsa COMMAND --help` for detailed usage information.

### MCP Server

This library provides an MCP server that exposes configuration management, session and dataset operations, and Unity
Editor relay tools for AI agent integration. The dataset tools cover the forged-dataset container: its marker, its
structure, and its self-consistency. Composing a dataset and reading its forging job state are owned by
[sollertia-forgery](https://github.com/Sun-Lab-NBB/sollertia-forgery).

#### Starting the Server

Start the MCP server using the CLI:

```bash
slsa mcp
```

The server defaults to the `stdio` transport. Use the `-t/--transport` flag to select either `stdio` or
`streamable-http`.

#### Available Tools

| Tool                                            | Description                                                       |
|-------------------------------------------------|-------------------------------------------------------------------|
| `clone_zone_prefab_tool`                        | Clones a canonical base zone prefab into a trigger-zone prefab    |
| `create_experiment_from_vr_template_tool`       | Creates an experiment configuration from a Unity VR task template |
| `create_project_tool`                           | Creates the on-disk directory structure for a new project         |
| `create_task_tool`                              | Creates a Unity task end-to-end from a YAML task template         |
| `delete_asset_tool`                             | Deletes a non-scene Unity asset and refreshes the AssetDatabase   |
| `delete_task_tool`                              | Removes every Unity artifact created for a given task template    |
| `describe_dataset_data_schema_tool`             | Returns the DatasetData and nested DatasetSession schemas         |
| `describe_experiment_configuration_schema_tool` | Returns the experiment configuration schema for a system          |
| `describe_session_data_schema_tool`             | Returns the schema for the SessionData dataclass                  |
| `describe_session_descriptor_schema_tool`       | Returns the descriptor schema for a given session type            |
| `describe_session_hardware_state_schema_tool`   | Returns the hardware-state schema for an acquisition system       |
| `describe_data_asset_schema_tool`               | Returns the read-asset dataclass schema for a data asset          |
| `describe_template_schema_tool`                 | Returns the TaskTemplate schema and its nested class schemas      |
| `discover_datasets_tool`                        | Discovers every forged dataset marker under the data root         |
| `discover_experiments_tool`                     | Discovers every experiment configuration YAML under the data root |
| `discover_templates_tool`                       | Lists the task templates in the configured templates directory    |
| `enter_play_mode_tool`                          | Enters Play Mode in the Unity Editor                              |
| `exit_play_mode_tool`                           | Exits Play Mode in the Unity Editor                               |
| `filter_sessions_tool`                          | Filters session entries by date range and inclusion criteria      |
| `get_data_root_overview_tool`                   | Groups session markers into a project, animal, session tree       |
| `get_platform_environment_status_tool`          | Reports the health of the platform configuration components       |
| `get_play_state_tool`                           | Returns the Unity Editor play state and active scene name         |
| `inspect_datasets_tool`                         | Produces a structural inventory report for each dataset path      |
| `inspect_prefab_tool`                           | Returns a prefab's hierarchy, components, and collider details    |
| `inspect_scene_tool`                            | Returns the active scene's metadata and object hierarchy          |
| `inspect_sessions_tool`                         | Produces a health and inventory report for each session path      |
| `list_assets_tool`                              | Lists Unity assets of a given type within a search path           |
| `list_processing_trackers_tool`                 | Enumerates the ProcessingTracker filenames each pipeline writes   |
| `list_scenes_tool`                              | Lists every Unity scene and identifies the active one             |
| `list_session_type_support_tool`                | Maps each acquisition system to the session types it can run      |
| `list_supported_acquisition_systems_tool`       | Enumerates the acquisition systems the platform supports          |
| `list_supported_credentials_tool`               | Enumerates the credentials categories the platform supports       |
| `list_supported_data_assets_tool`               | Enumerates the read-asset data formats the platform supports      |
| `list_supported_session_types_tool`             | Enumerates session types, optionally scoped to one system         |
| `list_supported_trial_types_tool`               | Enumerates a system's experiment configuration trial classes      |
| `list_supported_trigger_types_tool`             | Enumerates the trigger types supported by trial structures        |
| `open_scene_tool`                               | Opens a Unity scene, applying the unsaved-changes policy          |
| `read_credentials_tool`                         | Returns the path to the requested credentials file                |
| `read_data_root_tool`                           | Returns the configured Sollertia platform data root path          |
| `read_dataset_column_descriptions_tool`         | Reads a dataset's per-column data descriptions companion          |
| `read_dataset_data_tool`                        | Loads a dataset.yaml file via the DatasetData schema              |
| `read_experiment_configuration_tool`            | Loads an experiment configuration YAML for a system               |
| `read_session_data_tool`                        | Loads a session_data.yaml file via the SessionData schema         |
| `read_session_descriptor_tool`                  | Loads a session descriptor YAML for a given session type          |
| `read_session_hardware_state_tool`              | Loads a hardware-state YAML for an acquisition system             |
| `read_data_asset_tool`                          | Loads a read-asset YAML for a given data asset                    |
| `read_task_parameters_tool`                     | Reads every field of the Unity Task Parameters window             |
| `read_task_templates_directory_tool`            | Returns the configured task templates directory path              |
| `read_template_tool`                            | Loads a TaskTemplate YAML, live or per-session snapshot           |
| `read_working_directory_tool`                   | Returns the configured platform working directory path            |
| `refresh_monitors_tool`                         | Re-detects the Unity Editor host monitors and returns a snapshot  |
| `set_credentials_tool`                          | Copies a credentials file into the platform credentials directory |
| `set_data_root_tool`                            | Sets the local Sollertia platform data root                       |
| `set_task_templates_directory_tool`             | Sets the path to the task templates directory                     |
| `set_working_directory_tool`                    | Sets the local Sollertia platform working directory               |
| `validate_dataset_descriptions_tool`            | Verifies every emitted dataset column carries a description       |
| `validate_experiment_configuration_tool`        | Validates an experiment configuration YAML against its schema     |
| `validate_template_tool`                        | Validates a TaskTemplate against its schema and constraints       |
| `write_dataset_data_tool`                       | Creates or replaces a validated dataset.yaml marker file          |
| `write_experiment_configuration_tool`           | Creates or replaces an experiment configuration YAML              |
| `write_session_data_tool`                       | Creates or replaces a validated session_data.yaml file            |
| `write_session_descriptor_tool`                 | Creates or replaces a session's descriptor YAML                   |
| `write_session_hardware_state_tool`             | Creates or replaces a session's hardware-state YAML               |
| `write_data_asset_tool`                         | Creates or replaces a validated read-asset YAML                   |
| `write_task_parameters_tool`                    | Writes a subset of the Task Parameters fields atomically          |
| `write_template_tool`                           | Creates or replaces a live TaskTemplate YAML                      |

***Note,*** tools that interact with Unity (`clone_zone_prefab_tool`, `create_task_tool`, `delete_asset_tool`,
`delete_task_tool`, `enter_play_mode_tool`, `exit_play_mode_tool`, `get_play_state_tool`, `inspect_prefab_tool`,
`inspect_scene_tool`, `list_assets_tool`, `list_scenes_tool`, `open_scene_tool`, `read_task_parameters_tool`,
`refresh_monitors_tool`, `write_task_parameters_tool`) require the Unity Editor to be running on the local machine
with the McpBridge plugin from [sollertia-virtual-reality](https://github.com/Sun-Lab-NBB/sollertia-virtual-reality)
active. These tools relay commands to the Editor via HTTP.

#### Client Registration

MCP server registration and Claude Code skill assets for this library are distributed through the
[sollertia](https://github.com/Sun-Lab-NBB/sollertia) marketplace as part of the **assets** plugin. Install the
plugin from the marketplace to automatically register the MCP server with compatible clients and make all associated
skills available.

___

## API Documentation

See the [API documentation](https://sollertia-shared-assets-api-docs.netlify.app/) for the detailed description of the
methods and classes exposed by components of this library.

___

## Developers

This section provides installation, dependency, and build-system instructions for the developers that want to modify
the source code of this library.

### Installing the Project

***Note,*** this installation method requires **mamba version 2.3.2 or above**. Currently, all automation pipelines
require that mamba is installed through the [miniforge3](https://github.com/conda-forge/miniforge) installer.

1. Download this repository to the local machine using the preferred method, such as git-cloning.
2. If the downloaded distribution is stored as a compressed archive, unpack it using the appropriate decompression
   tool.
3. `cd` to the root directory of the prepared project distribution.
4. Install the core development dependencies into the ***base*** mamba environment via the
   `mamba install tox uv tox-uv` command.
5. Use the `tox -e create` command to create the project-specific development environment followed by `tox -e install`
   command to install the project into that environment as a library.

### Additional Dependencies

In addition to installing the project and all user dependencies, install the following dependencies:

1. [Python](https://www.python.org/downloads/) distributions, one for each version supported by the developed project.
   Currently, this library supports Python 3.14 only. It is recommended to use a tool like
   [pyenv](https://github.com/pyenv/pyenv) to install and manage the required versions.

### Development Automation

This project uses `tox` for development automation. The following tox environments are available:

| Environment    | Description                                                 |
|----------------|-------------------------------------------------------------|
| `lint`         | Runs ruff formatting, ruff linting, and mypy type checking  |
| `stubs`        | Generates py.typed marker and .pyi stub files               |
| `{py314}-test` | Runs the test suite via pytest and aggregates coverage data |
| `coverage`     | Aggregates test coverage and applies the 100% coverage gate |
| `docs`         | Builds the API documentation via Sphinx                     |
| `build`        | Builds sdist and wheel distributions                        |
| `upload`       | Uploads distributions to PyPI via twine                     |
| `deploy`       | Uploads the built documentation to the Netlify site         |
| `install`      | Builds and installs the project into its mamba environment  |
| `uninstall`    | Uninstalls the project from its mamba environment           |
| `create`       | Creates the project's mamba development environment         |
| `remove`       | Removes the project's mamba development environment         |
| `provision`    | Recreates the mamba environment from scratch                |
| `export`       | Exports the mamba environment as a .yml file                |
| `import`       | Creates or updates the mamba environment from a .yml file   |

Run any environment using `tox -e ENVIRONMENT`. For example, `tox -e lint`.

***Note,*** all pull requests for this project have to successfully complete the `tox` task before being merged. To
expedite the task's runtime, use the `tox --parallel` command to run some tasks in parallel.

### Adding New Session Types

A session type identifies the high-level activity performed during acquisition (e.g., training, experiment,
window-checking). Each type has its own descriptor dataclass that captures the type-specific task parameters and
outcome metadata, persisted as `session_descriptor.yaml` inside the session's `raw_data` directory. The descriptor
filename is flat across all types, only the parsing class varies, and it is dispatched via `DESCRIPTOR_REGISTRY`.

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
module of its own subpackage, so add the descriptor to the subpackage of the system that runs the new session type.
Use `LickTrainingDescriptor` or `RunTrainingDescriptor` in `mesoscope_vr/runtime_data.py` as reference. The descriptor
must declare an `incomplete: bool = True` field, which the session-inspection tooling reads to decide whether a
session is complete. The import-time `_assert_descriptor_contract` check fails if it is missing. Export the new class
from the subpackage's `__init__.py`, and re-export it from the top-level `src/sollertia_shared_assets/__init__.py`
(and its `__all__`).

**Step 3: Register the descriptor**

In `registries.py` (the registry hub):

1. Import the new descriptor class from its system subpackage.
2. Register it in `DESCRIPTOR_REGISTRY` under the new `SessionTypes` key.

**Step 4: Update required-asset checks (if applicable)**

The required-asset policy lives in `SessionData.required_raw_assets` (`data_hierarchy/session_data.py`), and the
session inventory tool delegates to it. The policy is data-driven rather than a per-session-type branch. Every session
requires `session_descriptor.yaml` and `system_configuration.yaml`. The `experiment_configuration.yaml` asset is
required whenever the session has an `experiment_name`, and `vr_configuration.yaml` is required for any session type
listed in `SESSION_TYPES_USING_VR_TASK` (`registries.py`). If the new session type uses VR, add it to that frozenset.
If it requires some other extra asset, extend `required_raw_assets` accordingly.

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
association, and the import-time checks that guard them are defined, fully populated, in the top-level `registries.py`
module. System-level hardware and software configuration classes live in the acquisition runtime package
(sollertia-experiment).

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

1. `<system>/runtime_data.py` defines a `<System>HardwareState` dataclass inheriting from `YamlConfig` that records
   the configuration of every active hardware module on the new system, plus the system's per-session-type
   descriptors. Each descriptor must declare an `incomplete: bool = True` field, enforced by the import-time
   `_assert_descriptor_contract` check. Use `mesoscope_vr/runtime_data.py` as reference.
2. `<system>/experiment_configuration.py` defines a `<System>ExperimentConfiguration` dataclass inheriting from
   `YamlConfig` that captures the runtime experiment parameters for the new system. Every
   `<System>ExperimentConfiguration` shares one contract of three fields and one classmethod. The `experiment_states`
   field holds a mapping of `ExperimentState`, the experiment state machine that every experiment runs as, and the
   `trial_structures` field holds the trials the experiment runs, whose concrete trial classes vary per system. The
   `unity_scene_name` field names the linear infinite corridor task the experiment runs, and the `from_task_template`
   classmethod builds the configuration from a task template. Fields beyond that contract are system-specific. Use
   `mesoscope_vr/experiment_configuration.py` as reference.
3. `<system>/raw_data.py` defines a `<System>RawData` `@dataclass(slots=True)` that holds the absolute paths to all
   system-specific raw assets and exposes a `build(cls, root: Path) -> <System>RawData` classmethod that resolves
   every field against the session's `raw_data` directory. Optionally add `<System>RawDataFiles` and/or
   `<System>Directories` `StrEnum` classes that enumerate any canonical filenames or subdirectories unique to the
   new system's `raw_data`. Use `mesoscope_vr/raw_data.py` as reference.

Beyond the subpackage `__init__.py`, re-export the new system's classes from the top-level
`src/sollertia_shared_assets/__init__.py` (and its `__all__`), mirroring the Mesoscope-VR exports, so downstream
libraries can import them by name.

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
reference. The generic `write_experiment_configuration_tool` authors or repairs a full payload directly.

**Step 5: Update downstream libraries**

Coordinate with sollertia-experiment (which owns the system-level hardware/software configuration classes and the
acquisition runtime) and sollertia-forgery (data processing) as needed.

### Adding a New Trial Class

A trial class defines the runtime parameters of one trial type an experiment runs (reward sizes, durations,
thresholds). Trial classes are acquisition-system-specific: each system declares its own classes in its subpackage,
next to that system's experiment configuration. The spatial layout of a trial (its cues and zones) lives on the
matching `TrialStructure` in the paired Unity task template, not on the trial class.

**Step 1: Define the trial class**

In the owning system's `<system>/experiment_configuration.py`, add a standalone `@dataclass(frozen=True, slots=True)`
whose name is prefixed with the system name (mirror `MesoscopeWaterRewardTrial` and `MesoscopeGasPuffTrial`). The class
carries its runtime parameters plus the trial-kind discriminator, and declares no spatial fields.

**Step 2: Wire the trial-kind discriminator**

Every trial class carries a discriminator drawn from its system's `TrialKind` enum, and that discriminator is what
routes a stored trial back to the class that wrote it on deserialization. Four edits are required:

1. Add a new member to the system's `TrialKind` enum (Mesoscope-VR's carries `WATER` and `PUFF`).
2. Declare `trial_kind: TrialKind = TrialKind.<NEW>` on the new class, with the matching `__post_init__` rejection
   that raises when the field holds any other member.
3. Add the `(TrialKind.<NEW>, <NewTrial>)` pair to the module's `_TRIAL_CLASSES` tuple, which drives
   `_restore_trial_kind` and `_unique_trial_fields`.
4. Add the class to the `isinstance` acceptance tuple in `<System>ExperimentConfiguration.__post_init__`, which
   rejects at load anything outside it.

Skipping this step ships a trial class that serializes but cannot be deserialized: every configuration containing it
raises at load.

**Step 3: Export the trial class**

Export the new class from the system subpackage's `__init__.py`, and re-export it from the top-level
`src/sollertia_shared_assets/__init__.py` (and its `__all__`), mirroring the existing trial classes.

**Step 4: Add the class to the experiment-configuration trial union**

Add the new class to the `trial_structures` type-union annotation of each `<System>ExperimentConfiguration` that uses
it (for example, `dict[str, MesoscopeWaterRewardTrial | MesoscopeGasPuffTrial | <NewTrial>]`). The MCP
trial-vocabulary introspection derives a system's trial types from this annotation, so a class absent from the union
does not surface in the tooling.

**Step 5: Map a trigger to the trial class**

Update that configuration's `from_task_template` so the trial's `TriggerType` instantiates the new class (the trigger
may itself be new, as covered by "Adding a New Trigger Type"). A trigger that no branch handles raises, so every
trigger the template can carry on this system needs a branch.

***Note,*** the import-time `_assert_experiment_configuration_contract` check confirms the contract fields and the
`from_task_template` builder, but it does not verify the trial-kind discriminator, the trial union, or the trigger
mapping. Cover a new trial class in the experiment-configuration tests.

### Adding a New Trigger Type

A `TriggerType` identifies the corridor condition that resolves a trial (an interaction, an occupancy event, and so
on). The enum is platform-wide, and each acquisition system maps only the subset of trigger types it supports to its
runtime trial classes.

**Step 1: Extend the TriggerType enum**

In `configuration/vr_configuration.py`, add a new member to `TriggerType`.

**Step 2: Map the trigger on each supporting system**

For every acquisition system that supports the new trigger, add the matching branch to that system's
`from_task_template`, instantiating the runtime trial class the trigger maps to (which may itself be new, as covered
by "Adding a New Trial Class"). A system that does not support the trigger adds no branch, so its `from_task_template`
raises for that trigger, which is the intended "unsupported on this system" signal. A new `TriggerType` member
therefore does not require a branch in every system.

**Step 3: Update downstream libraries**

A new trigger type also requires Unity-side assets in sollertia-virtual-reality, namely the zone prefab, the
task-generation pipeline, and the fixtures that pin the trigger enum. The unity plugin's `/zone-prefabs`,
`/task-generator`, and `/unity-tests` skills own that work, which is out of scope for this library.

### Adding a New Read Asset

A **read asset** is metadata the platform reads from an external, human-maintained source (for example, the surgery
log Google Sheet). The concrete architecture decision is that every read asset is translated by the acquisition
library (sollertia-experiment) into a typed dataclass and cached on disk in a standardized format. Downstream
consumers (notably sollertia-forgery) then interact only with that on-disk dataclass and never touch the external
source. Because the dataclass is the canonical format, it is reusable regardless of the upstream storage, as the
acquisition library translates whatever source it reads (Google Sheets or otherwise) into it.

This applies only to assets the platform **reads**. Assets the platform only **writes** to an external source (for
example, the water-restriction log) have no on-disk representation to standardize, so they need no dataclass and no
registry entry. They are owned entirely by the writing library.

`ReadAssets` (in `enums.py`) enumerates the supported read-asset formats and `READ_ASSET_REGISTRY` (in
`registries.py`) maps each to its on-disk dataclass. The contract dataclasses themselves live in the `data_classes/`
package. Unlike the acquisition-system registries, this is a contract surface curated by Sollertia platform
maintainers: each entry is a durable translation contract, and adding one is a platform-contract decision rather
than a routine extension. The import-time parity check (`_assert_registry_coverage`) enforces that every
`ReadAssets` member has a registered dataclass.

**Step 1: Add the contract dataclass**

In `data_classes/`, add a new module holding the concrete on-disk representation as a dataclass inheriting from
`YamlConfig` (use `data_classes/surgery_data.py`'s `SurgeryData` as reference). Contract modules export plain
dataclasses and never consume the dispatch registries. Export the new class from `data_classes/__init__.py`, and
re-export it from the top-level `src/sollertia_shared_assets/__init__.py` (and its `__all__`).

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
representation, and the dataclass keeps every downstream consumer storage-agnostic.

### AI-Assisted Development

Claude Code skills and other AI development assets for this project are distributed through two marketplaces:

- [sollertia](https://github.com/Sun-Lab-NBB/sollertia) marketplace:
  - **assets** plugin, which registers the `slsa mcp` server with compatible MCP clients. It also provides
    configuration and data skills for working directory setup, session discovery, session data, descriptors, hardware
    state, subject metadata, task templates, experiment configuration, library extension, and MCP environment setup.
    The server also fronts the Unity Editor relay that the **unity** plugin's skills drive.
  - **unity** plugin, which provides Unity Editor skills that drive the `McpBridge` relay tools served by the
    `slsa mcp` server, document the MQTT contract and `CreateTask` pipeline, and guide manufacturing of new trigger
    zone prefabs.
- [ataraxis](https://github.com/Sun-Lab-NBB/ataraxis) marketplace:
  - **automation** plugin, which provides shared development skills that enforce Sollertia Platform coding
    conventions (Python style, README style, commit messages, pyproject.toml, tox configuration) and general-purpose
    codebase exploration tools.

Install all three plugins to make the full skill set available to compatible AI coding agents. The **unity** plugin
depends on the **assets** plugin for the backing `slsa mcp` server that drives the Unity Editor relay.

### Automation Troubleshooting

Many packages used in `tox` automation pipelines (uv, mypy, ruff) and `tox` itself may experience runtime failures. In
most cases, this is related to their caching behavior. If an unintelligible error is encountered with any of the
automation components, deleting the corresponding cache directories (`.tox`, `.ruff_cache`, `.mypy_cache`, etc.)
manually or via a CLI command typically resolves the issue.

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

This project is licensed under the Apache 2.0 License: see the [LICENSE](LICENSE) file for details.

___

## Acknowledgments

- All Sun lab [members](https://neuroai.github.io/sunlab/people) for providing the inspiration and comments during the
  development of this library.
- The creators of all other dependencies and projects listed in the [pyproject.toml](pyproject.toml) file.
