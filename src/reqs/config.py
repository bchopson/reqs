import dataclasses as dc
from pathlib import Path
import tomllib
import warnings


DEFAULT_DEPENDS = {
    'base.in': [],
    'ci.in': ['base.txt'],
    'dev.in': ['base.txt', 'ci.txt'],
}


def find_upwards(d: Path, filename: str):
    root = Path(d.root)

    while d != root:
        attempt = d / filename
        if attempt.exists():
            return attempt
        d = d.parent

    return None


def deep_get(d: dict, dotted_path: str, default=None):
    keys = dotted_path.split('.')
    for key in keys:
        if key not in d:
            return default
        d = d[key]
    return d


@dc.dataclass
class Depends:
    fname: str
    depends_on: list[str]

    def __post_init__(self):
        if self.depends_on in ('', False):
            self.depends_on = []
        elif isinstance(self.depends_on, str):
            self.depends_on = [self.depends_on]


def default_depends(reqs_dpath: Path):
    in_fpaths = sorted(reqs_dpath.glob('*.in'))
    names = {path.name for path in in_fpaths}

    if names == {'base.in', 'dev.in', 'ci.in'}:
        return DEFAULT_DEPENDS

    if len(in_fpaths) > 1:
        # TODO: this warning is thrown even when dependencies have been specified
        warnings.warn(
            'More than one .in file and no dependencies specified in the config.',
            stacklevel=3,
        )

    return {path.name: '' for path in in_fpaths}


@dc.dataclass
class Config:
    pkg_dpath: Path
    reqs_dpath: Path
    sync_pipx: bool
    depends: list[Depends]

    def as_dict(self):
        return dc.asdict(self)

    def __str__(self):
        return dataclass_repr(self)


def dataclass_repr(obj, indent=0):
    lines = []
    for field in dc.fields(obj):
        value = getattr(obj, field.name)

        if dc.is_dataclass(value):
            lines.append('  ' * indent + field.name + ':')
            lines.append(dataclass_repr(value, indent + 1))
        elif isinstance(value, list) and value and dc.is_dataclass(value[0]):
            lines.append('  ' * indent + field.name + ':')
            for item in value:
                lines.append(dataclass_repr(item, indent + 1))
        else:
            lines.append('  ' * indent + field.name + ': ' + str(value))
    return '\n'.join(lines)


def load(start_at: Path):
    pp_fpath = find_upwards(start_at, 'pyproject.toml')
    if pp_fpath is None:
        relative_path = start_at.relative_to(Path.cwd())
        raise Exception(f'No pyproject.toml found in {relative_path} or parents')

    with pp_fpath.open('rb') as fo:
        proj_config = tomllib.load(fo)

    pkg_dpath = pp_fpath.parent
    reqs_dpath = pkg_dpath.joinpath(
        deep_get(proj_config, 'tool.reqs.dpath', 'requirements'),
    )
    depends = deep_get(proj_config, 'tool.reqs.depends', default_depends(reqs_dpath))
    return Config(
        pkg_dpath=pkg_dpath,
        reqs_dpath=reqs_dpath,
        sync_pipx=deep_get(proj_config, 'tool.reqs.sync_pipx', False),
        depends=[Depends(k, v) for k, v in depends.items()],
    )
