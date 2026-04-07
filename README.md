# sollertia-shared-assets

A Python library that provides data acquisition and processing assets shared between Sollertia platform libraries.

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

Sollertia is an AI-assisted scientific data acquisition and processing platform built on the Ataraxis framework and
developed in the Sun (NeuroAI) lab at Cornell University. This library makes the two main Sollertia libraries used for
data acquisition ([sollertia-experiment](https://github.com/Sun-Lab-NBB/sollertia-experiment)) and processing
([sollertia-forgery](https://github.com/Sun-Lab-NBB/sollertia-forgery)) independent of each other.

The library broadly stores two types of assets. First, it stores dataclasses used to save the data acquired with the
Sollertia platform and configure data acquisition and processing runtimes. Second, it provides the low-level tools and
methods used to manage the data at all stages of the Sollertia data workflow: acquisition, processing, and analysis.

___

## Table of Contents

- [Dependencies](#dependencies)
- [Installation](#installation)
- [Usage](#usage)
  - [MCP Server](#mcp-server)
- [API Documentation](#api-documentation)
- [Development](#development)
  - [Adding New Acquisition Systems](#adding-new-acquisition-systems)
- [Versioning](#versioning)
- [Authors](#authors)
- [License](#license)
- [Acknowledgments](#acknowledgments)

___

## Dependencies

All library dependencies are installed automatically by all supported installation methods 
(see the [Installation](#installation) section).

___

## Installation

### Source

Note, installation from source is ***highly discouraged*** for anyone who is not an active project developer.

1. Download this repository to the local machine using the preferred method, such as git-cloning. Use one of the 
   [stable releases](https://github.com/Sun-Lab-NBB/sollertia-shared-assets/releases) that include precompiled binary
   and source code distribution (sdist) wheels.
2. If the downloaded distribution is stored as a compressed archive, unpack it using the appropriate decompression tool.
3. ```cd``` to the root directory of the prepared project distribution.
4. Run ```python -m pip install .``` to install the project. Alternatively, if using a distribution with precompiled
   binaries, use ```python -m pip install WHEEL_PATH```, replacing 'WHEEL_PATH' with the path to the wheel file.

### pip

Use the following command to install the library using pip: ```pip install sollertia-shared-assets```.

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

### MCP Server

This library provides an MCP server that exposes configuration management tools for AI agent integration. The server
enables agents to query and configure shared Sollertia platform workflow components.

#### Starting the Server

Start the MCP server using the CLI:

```bash
sl-configure mcp
```

#### Available Tools

| Tool                                        | Description                                                       |
|---------------------------------------------|-------------------------------------------------------------------|
| `get_working_directory_tool`                | Returns the current Sollertia platform working directory path     |
| `set_working_directory_tool`                | Sets the Sollertia platform working directory                     |
| `get_server_configuration_tool`             | Returns the compute server configuration (password masked)        |
| `create_server_configuration_template_tool` | Creates a server configuration template for manual password entry |
| `get_google_credentials_tool`               | Returns the path to the Google service account credentials file  |
| `set_google_credentials_tool`               | Sets the path to the Google credentials file                      |
| `get_task_templates_directory_tool`         | Returns the path to the sollertia-unity-tasks templates directory |
| `set_task_templates_directory_tool`         | Sets the path to the task templates directory                     |
| `list_available_templates_tool`             | Lists all available task templates                                |
| `get_template_info_tool`                    | Returns detailed information about a specific task template       |

#### Claude Desktop Configuration

Add the following to the Claude Desktop configuration file:

```json
{
  "mcpServers": {
    "sollertia-shared-assets": {
      "command": "sl-configure",
      "args": ["mcp"]
    }
  }
}
```

___

## API Documentation

Developers working on integrating sollertia-shared-assets into other libraries should see the
[API documentation](https://sollertia-shared-assets-api-docs.netlify.app/) for the detailed description of the methods
and classes exposed by components of this library.

**Note!** The API documentation includes important information about the 'configuration' Command-Line Interface (CLI)
exposed by this library.

___

## Development

This section provides guidance for developers extending this library.

### Adding New Acquisition Systems

The library uses registry patterns to support multiple data acquisition systems. Each system requires configuration
dataclasses. The following steps outline how to add support for a new acquisition system.

**Step 1: Add the system to the AcquisitionSystems enum**

In `configuration_utilities.py`, add a new entry to the `AcquisitionSystems` enum:

```python
from enum import StrEnum
class AcquisitionSystems(StrEnum):
    MESOSCOPE_VR = "mesoscope"
    NEW_SYSTEM = "new_system"  # Add new system here
```

**Step 2: Create the system configuration module**

Create a new file (e.g., `new_system_configuration.py`) containing:

- A system configuration dataclass inheriting from `YamlConfig` with hardware and software settings
- An experiment configuration dataclass for runtime experiment parameters
- A `save()` method if custom serialization logic is needed

**Step 3: Update type aliases and registries**

In `configuration_utilities.py`:

1. Extend the `SystemConfiguration` type alias to include the new configuration class
2. Extend the `ExperimentConfiguration` type alias to include the new experiment configuration class
3. Add an entry to `_SYSTEM_CONFIG_CLASSES` mapping the system name to its configuration class
4. Create an experiment factory function and register it in `_EXPERIMENT_CONFIG_FACTORIES`

**Step 4: Update downstream libraries**

Coordinate changes with sollertia-experiment (data acquisition) and sollertia-forgery (data processing) as needed.

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

This project is licensed under the GPL3 License: see the [LICENSE](LICENSE) file for details.

___

## Acknowledgments

- All Sun (NeuroAI) lab [members](https://neuroai.github.io/sunlab/people) for providing the inspiration and comments
  during the development of this library and the broader Sollertia platform.
- The creators of all other dependencies and projects listed in the [pyproject.toml](pyproject.toml) file.

___