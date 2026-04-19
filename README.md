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
[sollertia-unity-tasks](https://github.com/Sun-Lab-NBB/sollertia-unity-tasks), enabling agents to generate task prefabs,
manage scenes, and control Play Mode.

___

## Table of Contents

- [Dependencies](#dependencies)
- [Installation](#installation)
- [Usage](#usage)
  - [CLI Commands](#cli-commands)
  - [MCP Server](#mcp-server)
- [API Documentation](#api-documentation)
- [Developers](#developers)
  - [Adding New Acquisition Systems](#adding-new-acquisition-systems)
- [Versioning](#versioning)
- [Authors](#authors)
- [License](#license)
- [Acknowledgments](#acknowledgments)

___

## Dependencies

For users, all library dependencies are installed automatically by all supported installation
methods. For developers, see the [Developers](#developers) section for information on installing
additional development dependencies.

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

| Command                 | Description                                                          |
|-------------------------|----------------------------------------------------------------------|
| `mcp`                   | Starts the MCP server for agentic configuration management           |
| `configure directory`   | Sets the local Sollertia platform working directory                  |
| `configure google`      | Sets the path to the Google service account credentials file         |
| `configure templates`   | Sets the path to the sollertia-unity-tasks task templates directory  |
| `configure project`     | Creates a project directory structure for data acquisition           |
| `configure experiment`  | Creates an experiment configuration from a task template             |

Use `slsa --help`, `slsa configure --help`, or `slsa COMMAND --help` for detailed usage information.

### MCP Server

This library provides an MCP server that exposes configuration management, session and dataset operations, and Unity
Editor relay tools for AI agent integration. The server enables agents to query and configure shared Sollertia platform
workflow components.

#### Starting the Server

Start the MCP server using the CLI:

```bash
slsa mcp
```

#### Available Tools

| Tool                                            | Description                                                                                    |
|-------------------------------------------------|------------------------------------------------------------------------------------------------|
| `check_mount_accessibility_tool`                | Verifies that a filesystem path is accessible and writable                                     |
| `create_experiment_config_tool`                 | Creates an experiment configuration from a task template using sensible defaults               |
| `create_project_tool`                           | Creates a new project directory and its configuration subdirectory                             |
| `create_scene_tool`                             | Creates a new Unity scene by copying ExperimentTemplate and optionally adding a task prefab    |
| `describe_experiment_configuration_schema_tool` | Returns the schema for the experiment configuration of a given acquisition system              |
| `describe_session_descriptor_schema_tool`       | Returns the schema for the descriptor associated with a given session type                     |
| `describe_session_hardware_state_schema_tool`   | Returns the schema for MesoscopeHardwareState                                                  |
| `describe_surgery_schema_tool`                  | Returns the schema for SurgeryData and its nested subclasses                                   |
| `describe_template_schema_tool`                 | Returns the schema for TaskTemplate and nested Cue, Segment, TrialStructure, and VREnvironment |
| `discover_animals_tool`                         | Lists animal subdirectories within a project                                                   |
| `discover_experiments_tool`                     | Discovers all experiment configuration YAML files under the data root                          |
| `discover_projects_tool`                        | Lists all projects accessible to the data acquisition system                                   |
| `discover_session_descriptors_tool`             | Returns the inventory of descriptor, hardware state, and configuration snapshot files          |
| `discover_sessions_tool`                        | Recursively discovers all sessions under the data root                                         |
| `discover_subjects_tool`                        | Discovers subjects by scanning project directories on disk                                     |
| `discover_templates_tool`                       | Lists all task templates in the configured templates directory                                 |
| `enter_play_mode_tool`                          | Enters Play Mode in the Unity Editor                                                           |
| `exit_play_mode_tool`                           | Exits Play Mode in the Unity Editor                                                            |
| `generate_task_prefab_tool`                     | Generates a Task prefab in Unity from a YAML task template                                     |
| `get_acquisition_environment_status_tool`       | Reports the status of the working directory, templates directory, and Google credentials       |
| `get_batch_session_status_overview_tool`        | Aggregates session lifecycle status across every session under the data root                   |
| `get_play_state_tool`                           | Returns the current Unity Editor play state and active scene name                              |
| `get_project_overview_tool`                     | Returns aggregate counts for animals, sessions, experiments, and datasets                      |
| `get_session_status_tool`                       | Returns lifecycle status for a single session                                                  |
| `inspect_prefab_tool`                           | Returns the full hierarchy, components, transforms, and collider details of a prefab           |
| `list_scenes_tool`                              | Lists all Unity scene assets and identifies the currently active scene                         |
| `list_supported_acquisition_systems_tool`       | Enumerates the acquisition systems supported by the Sollertia platform                         |
| `list_supported_session_types_tool`             | Enumerates the session types supported by the Sollertia platform                               |
| `list_supported_trial_types_tool`               | Enumerates the trial classes supported by experiment configurations                            |
| `list_supported_trigger_types_tool`             | Enumerates the trigger type values supported by trial structures                               |
| `list_unity_assets_tool`                        | Lists Unity assets of a given type within a search path                                        |
| `open_scene_tool`                               | Opens a Unity scene in the Editor                                                              |
| `read_experiment_configuration_tool`            | Loads the experiment configuration YAML for a project                                          |
| `read_google_credentials_tool`                  | Returns the configured path to the Google service account credentials file                     |
| `read_session_data_tool`                        | Loads the SessionData YAML for a session                                                       |
| `read_session_descriptor_tool`                  | Detects the appropriate descriptor class and loads the descriptor YAML                         |
| `read_session_experiment_configuration_tool`    | Loads the per-session snapshot of the experiment configuration                                 |
| `read_session_hardware_state_tool`              | Loads the MesoscopeHardwareState YAML for a session                                            |
| `read_subject_drugs_tool`                       | Loads the DrugData payload for a subject from the cached SurgeryData YAML                      |
| `read_subject_implants_tool`                    | Loads the list of ImplantData for a subject from the cached SurgeryData YAML                   |
| `read_subject_injections_tool`                  | Loads the list of InjectionData for a subject from the cached SurgeryData YAML                 |
| `read_subject_procedure_tool`                   | Loads the ProcedureData payload for a subject from the cached SurgeryData YAML                 |
| `read_subject_surgery_tool`                     | Loads the full SurgeryData payload for a subject                                               |
| `read_subject_tool`                             | Loads SubjectData for a subject from the cached SurgeryData YAML                               |
| `read_task_templates_directory_tool`            | Returns the configured path to the task templates directory                                    |
| `read_template_tool`                            | Loads a TaskTemplate YAML by name from the configured templates directory                      |
| `read_working_directory_tool`                   | Returns the configured Sollertia platform working directory path                               |
| `set_google_credentials_tool`                   | Sets the path to the Google service account credentials file                                   |
| `set_task_templates_directory_tool`             | Sets the path to the task templates directory                                                  |
| `set_working_directory_tool`                    | Sets the local Sollertia platform working directory                                            |
| `validate_experiment_configuration_tool`        | Validates an experiment configuration YAML for a project                                       |
| `validate_prefab_against_template_tool`         | Validates that Unity prefab zone positions match the template configuration                    |
| `validate_session_tool`                         | Validates that a session has the expected files for its session type                           |
| `validate_template_tool`                        | Validates a TaskTemplate against its schema and cross-reference constraints                    |
| `write_experiment_configuration_tool`           | Creates or replaces an experiment configuration YAML for a project                             |
| `write_session_descriptor_tool`                 | Creates or replaces a session descriptor YAML for a session                                    |
| `write_session_hardware_state_tool`             | Creates or replaces the MesoscopeHardwareState YAML for a session                              |
| `write_template_tool`                           | Creates or replaces a TaskTemplate YAML in the configured templates directory                  |

***Note,*** tools that interact with Unity (`create_scene_tool`, `enter_play_mode_tool`, `exit_play_mode_tool`,
`generate_task_prefab_tool`, `get_play_state_tool`, `inspect_prefab_tool`, `list_scenes_tool`, `list_unity_assets_tool`,
`open_scene_tool`, `validate_prefab_against_template_tool`) require the Unity Editor to be running on the local machine
with the McpBridge plugin from [sollertia-unity-tasks](https://github.com/Sun-Lab-NBB/sollertia-unity-tasks) active.
These tools relay commands to the Editor via HTTP.

#### Client Registration

MCP server registration and Claude Code skill assets for this library are distributed through the
[sollertia](https://github.com/Sun-Lab-NBB/sollertia) marketplace as part of the **configuration** plugin. Install the
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
Sun lab automation pipelines require that mamba is installed through the
[miniforge3](https://github.com/conda-forge/miniforge) installer.

1. Download this repository to the local machine using the preferred method, such as git-cloning.
2. If the downloaded distribution is stored as a compressed archive, unpack it using the
   appropriate decompression tool.
3. `cd` to the root directory of the prepared project distribution.
4. Install the core Sun lab development dependencies into the ***base*** mamba environment via the
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

### Adding New Acquisition Systems

This library owns the shared vocabulary that identifies acquisition systems (the `AcquisitionSystems` enum) and the
experiment configuration factory registry used to build per-system experiment configuration dataclasses from a
`TaskTemplate`. System-level hardware and software configuration classes live in the acquisition runtime package
(sollertia-experiment), not in this library. The following steps outline how to add support for a new acquisition
system.

**Step 1: Add the system to the AcquisitionSystems enum**

In `configuration/configuration_utilities.py`, add a new entry to the `AcquisitionSystems` enum:

```python
from enum import StrEnum
class AcquisitionSystems(StrEnum):
    MESOSCOPE_VR = "mesoscope"
    NEW_SYSTEM = "new_system"  # Add new system here
```

**Step 2: Create the experiment configuration module**

Create a new file (e.g., `new_system_configuration.py`) in `configuration/` containing an experiment configuration
dataclass inheriting from `YamlConfig` that captures the runtime experiment parameters for the new system. Use
`MesoscopeExperimentConfiguration` in `mesoscope_configuration.py` as a reference.

**Step 3: Update the factory registry**

In `configuration/configuration_utilities.py`:

1. Extend the `ExperimentConfigFactory` type alias so its return type includes the new experiment configuration class
2. Implement a private factory function (e.g., `_create_new_system_experiment_config`) that builds the new experiment
   configuration dataclass from a `TaskTemplate` and the converted trial structures dictionary
3. Register the factory in `_experiment_config_factory_registry` under the new `AcquisitionSystems` key

**Step 4: Update downstream libraries**

Coordinate changes with sollertia-experiment (which owns the system-level hardware/software configuration classes and
the acquisition runtime) and sollertia-forgery (data processing) as needed.

### AI-Assisted Development

Claude Code skills and AI development assets for this project are distributed through two marketplaces:

- [sollertia](https://github.com/Sun-Lab-NBB/sollertia) marketplace: Provides MCP server registration,
  configuration-specific skills for working directory management, system and experiment configuration, session data,
  subject metadata, dataset management, task templates, and MCP environment setup via the **configuration** plugin.
  Install this plugin to register the `slsa mcp` server with compatible MCP clients and make all configuration
  workflow skills available.
- [ataraxis](https://github.com/Sun-Lab-NBB/ataraxis) marketplace: Provides shared development skills that enforce
  Sun Lab coding conventions (Python style, README style, commit messages, pyproject.toml, tox configuration) and
  general-purpose codebase exploration tools via the **automation** plugin.

Install both marketplace plugins to make all associated skills and development tools available to compatible AI coding
agents.

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