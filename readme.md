reqs
====

Bootstrap, compile, and sync Python requirements files

# Install

Intended to be used with pipx

- manually & first install: `pipx install -e .../apps/reqs-pkg`; or
- when developing: `cd .../apps/reqs-pkg;` [`reqs`](../reqs-pkg/) `sync`


## Usage

- `reqs bootstrap`: Upgrade pip & install pip-tools
- `reqs compile`:  Compile .in to .txt when needed (based on file modification times)
- `reqs sync`: Compile and then update active venv and maybe pipx to match spec


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

[tool.reqs.depends]
# Define dependencies between files so `reqs compile` knows when a .in needs to be compiled and
# what order to use when compiling multiple files.
'base.in' = ''
'dev.in' = 'base.txt'
```
