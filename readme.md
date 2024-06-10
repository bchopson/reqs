reqs
====

Helps with Python requirements (reqs) files:

- `reqs bootstrap`:
    - Install uv (default) or upgrade pip & install pip-tools to active venv
    - Ensures reqs will compile lock files using the version of Python the project is using
- `reqs compile`:
    - Compile .in reqs files into .txt "lock" files
    - Considers file modification times and file dependencies (when -r or -c used)
- `reqs sync`:
    - Compile (default, optional)
    - Sync active virtualenv with lock files
    - When "sync_pipx" is true: will make the project's scripts available on the local system by
        installing/upgrading as an editable package with pipx.


# Install

Intended to be installed at the user level, not per app.

- `pipx install reqs-cli` (recommended)
- `[uv] pip install --user reqs-cli`


# Configuration

Configure using `pyproject.toml`:


```toml
# The options shown are the default values and DO NOT need to be specified
# if the default is sufficient.

[tool.reqs]
# Path to the directory containing the .in and .txt requirements files.  Relative to pyproject.toml.
dpath = 'requirements'

# Use pipx to install an editable version of the project.  True for tools like reqs and env-config
# that a developer would want available for different projects.  False for most client projects
# deployed on servers.
sync_pipx = false
```
