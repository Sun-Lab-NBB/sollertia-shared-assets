.. This file provides the instructions for how to display the API documentation generated using sphinx autodoc
   extension. Use it to declare Python documentation sub-directories via appropriate modules (automodule, etc.).

Configuration Assets
====================
.. automodule:: sollertia_shared_assets.configuration
   :members:
   :undoc-members:
   :show-inheritance:

Data Storage Assets
===================
.. automodule:: sollertia_shared_assets.data_classes
   :members:
   :undoc-members:
   :show-inheritance:

Command Line Interfaces
=======================
.. click:: sollertia_shared_assets.interfaces.cli:slsa_cli
   :prog: slsa
   :nested: full
