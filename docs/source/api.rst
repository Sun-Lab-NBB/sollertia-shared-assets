.. This file provides the instructions for how to display the API documentation generated using sphinx autodoc
   extension. Use it to declare Python documentation sub-directories via appropriate modules (automodule, etc.).

Platform Enumerations
=====================

.. automodule:: sollertia_shared_assets.enums
   :members:
   :undoc-members:
   :show-inheritance:

Configuration Assets
====================

.. automodule:: sollertia_shared_assets.configuration
   :members:
   :undoc-members:
   :show-inheritance:

.. The automodule directive above discovers module-level data through the source of the module it documents, so it
   skips a constant the package re-exports, and the constant never reaches the rendered page. These directives name
   the defining module rather than the re-exporting package, because autodoc reads the attribute docstring from that
   module's source and otherwise falls back to the docstring of the value's own type.

.. autodata:: sollertia_shared_assets.configuration.configuration_utilities.CONFIGURATION_DIRECTORY

.. autodata:: sollertia_shared_assets.configuration.configuration_utilities.CREDENTIALS_DIRECTORY

Data Contract Assets
====================

.. automodule:: sollertia_shared_assets.data_classes
   :members:
   :undoc-members:
   :show-inheritance:

Data Hierarchy Assets
=====================

.. automodule:: sollertia_shared_assets.data_hierarchy
   :members:
   :undoc-members:
   :show-inheritance:

.. The automodule directive above discovers module-level data through the source of the module it documents, so it
   skips a constant the package re-exports, and the constant never reaches the rendered page. These directives name
   the defining module rather than the re-exporting package, because autodoc reads the attribute docstring from that
   module's source and otherwise falls back to the docstring of the value's own type.

.. autodata:: sollertia_shared_assets.data_hierarchy.session_data.RAW_DATA_DIRECTORY

.. autodata:: sollertia_shared_assets.data_hierarchy.session_data.PROCESSED_DATA_DIRECTORY

.. autodata:: sollertia_shared_assets.data_hierarchy.project_hierarchy.PERSISTENT_DATA_DIRECTORY

.. autodata:: sollertia_shared_assets.data_hierarchy.project_hierarchy.DATASET_MARKER_FILENAME

Mesoscope-VR Assets
===================

.. automodule:: sollertia_shared_assets.mesoscope_vr
   :members:
   :undoc-members:
   :show-inheritance:

Dispatch Registries
===================

.. automodule:: sollertia_shared_assets.registries
   :members:
   :undoc-members:
   :show-inheritance:

Credentials Toolset
===================

.. automodule:: sollertia_shared_assets.credentials
   :members:
   :undoc-members:
   :show-inheritance:

Command-Line Interface
======================

.. click:: sollertia_shared_assets.interfaces.cli:slsa_cli
   :prog: slsa
   :nested: full
