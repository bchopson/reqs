import dataclasses as dc
from pathlib import Path
import tomllib


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
class Config:
    pkg_dpath: Path
    reqs_dpath: Path
    sync_pipx: bool

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

    if deep_get(proj_config, 'tool.reqs.depends') is not None:
        raise RuntimeError('reqs.depends is no longer needed, please remove.')

    return Config(
        pkg_dpath=pkg_dpath,
        reqs_dpath=reqs_dpath,
        sync_pipx=deep_get(proj_config, 'tool.reqs.sync_pipx', False),
    )
