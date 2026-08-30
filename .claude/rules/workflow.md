**Adding a new session type or acquisition system:**

Invoke `assets:library-extension`.

**Modifying configuration dataclasses:**

1. Read the relevant module: shared primitives live under `src/sollertia_shared_assets/configuration/`,
   system-specific experiment configurations under the system's subpackage (e.g.,
   `mesoscope_vr/experiment_configuration.py`)
2. Preserve the `YamlConfig` inheritance on the classes that carry it (`TaskTemplate`,
   `<System>ExperimentConfiguration`), because downstream libraries serialize and deserialize these. The nested
   building blocks (`ExperimentState`, `Cue`, `VREnvironment`, `TrialStructure`, the runtime trial classes) are plain
   frozen dataclasses
3. Update `__post_init__` validation when adding fields with cross-field constraints
4. Run `tox -e lint` and verify no field renames break sollertia-experiment or sollertia-forgery

**Modifying session or descriptor dataclasses:**

1. Read the relevant module: `SessionData` and the hierarchy views live under
   `src/sollertia_shared_assets/data_hierarchy/`, per-system descriptors and raw-data layouts under the system's
   subpackage (e.g., `mesoscope_vr/runtime_data.py`, `mesoscope_vr/raw_data.py`)
2. New canonical filenames require an entry in `RawDataFiles` (`data_hierarchy/session_data.py`) or a system-specific
   `*RawDataFiles` enum (`<system>/raw_data.py`). A new tracker filename belongs in `ProcessingTrackers`
   (`data_hierarchy/session_data.py`), and a new dataset-hierarchy filename in `DatasetFiles`
   (`data_hierarchy/dataset_data.py`)
3. New canonical subdirectories require an entry in `Directories` or a system-specific `*Directories` enum
4. New required `raw_data` assets require updating `SessionData.required_raw_assets` in `data_hierarchy/session_data.py`
   (for a session type that runs the corridor task, add it to the `SESSION_TYPES_USING_VR_TASK` gate in
   `registries.py`)

**Adding or modifying MCP tools:**

1. Add the `@mcp.tool()`-decorated function to the appropriate module under `src/sollertia_shared_assets/interfaces/`.
   Invoke `assets:library-extension` for a new `*_tools.py` module, since it owns the glob-import registration seam
   and the coverage-gate exemption that lets a tool module ship without a mirrored test package
2. Use `ok_response(...)` and `error_response(...)` from `mcp_instance` for all responses
3. Document the response key shape in the `Returns` docstring section, since it is part of the public contract
4. Update the README's MCP tool table, ensuring each row description matches the source docstring summary, and
   re-run `tox -e docs` to regenerate the API documentation

**Running tests, linting, the docs build, and the release tasks:**

```bash
tox -e lint                # purge stubs, ruff format, ruff check over ./src and ./tests, mypy over ./src
tox -e stubs               # generate .pyi stubs after lint passes
tox -e py314-test          # run pytest with coverage
tox -e coverage            # combine coverage data, render the reports, apply the 100% gate
tox -e docs                # build Sphinx HTML documentation
tox -e build               # build sdist + wheel
tox -e upload              # publish the built distributions to PyPI
tox -e deploy              # publish the built documentation to the project's Netlify site
```

The `tox` envlist runs `uninstall → export → lint → stubs → py314-test → coverage → docs → build → install` end to end.
The `coverage` task applies the `fail_under = 100` gate declared in `pyproject.toml`, so an uncovered statement fails
the run. The `upload` and `deploy` tasks stay outside the envlist and run manually as release steps, `upload` after
`tox -e build` and `deploy` after `tox -e docs`. The `deploy` task reads the target site from the tracked
`.netlify-site` file at the project root.
