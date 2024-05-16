import logging
from os import environ
from pathlib import Path
import shlex
import subprocess


log = logging.getLogger(__name__)


def run(*args, **kwargs):
    kwargs.setdefault('check', True)
    args = args + kwargs.pop('args', ())

    # Shlex doesn't handle Path objects
    args = [arg if not isinstance(arg, Path) else str(arg) for arg in args]
    log.debug(f'Run: {shlex.join(args)}\nkwargs: {kwargs}')

    return subprocess.run(args, **kwargs)


def venv_bin(bin_name: str, *args, **kwargs):
    venv_path = environ.get('VIRTUAL_ENV')
    if not venv_path:
        raise Exception(
            'No VIRTUAL_ENV environment variable set.  reqs only works in virtual envs.',
        )
    return Path(venv_path).joinpath('bin', bin_name)


def uv(*args, **kwargs):
    uv = venv_bin('uv')
    run(uv, args=args, **kwargs)


def pip(*args, **kwargs):
    uv = venv_bin('uv')
    if uv.exists():
        pip_bin = uv
        args = 'pip', *args
    else:
        pip_bin = venv_bin('pip')
        log.debug(f'{uv} not present, falling back to {pip_bin}')

    run(pip_bin, args=args, **kwargs)


def pip_sync(*args, **kwargs):
    uv = venv_bin('uv')
    if uv.exists():
        sync_bin = uv
        args = 'pip', 'sync', *args
    else:
        sync_bin = venv_bin('pip-sync')

    run(sync_bin, args=args, **kwargs)


def pip_compile(*args, **kwargs):
    uv = venv_bin('uv')
    if uv.exists():
        compile_bin = uv
        args = 'pip', 'compile', *args
    else:
        compile_bin = venv_bin('pip-compile')
        log.debug(f'{uv} not present, falling back to {compile_bin}')

    run(compile_bin, args=args, **kwargs)


def pipx_install(cmd, *args, **kwargs):
    run('pipx', 'install', *args, **kwargs)


def reqs_stale(txt_fpath: Path, dep_fpaths: list[Path]):
    if not txt_fpath.exists():
        return True

    return any(txt_fpath.stat().st_mtime < dep_fpath.stat().st_mtime for dep_fpath in dep_fpaths)


def reqs_compile(force: bool, reqs_dpath: Path, in_fname: str, *dep_fnames: list[str]):
    in_fpath: Path = reqs_dpath / in_fname
    txt_fpath: Path = in_fpath.with_suffix('.txt')

    dep_fpaths: list[Path] = [in_fpath]
    dep_fpaths.extend(reqs_dpath / fname for fname in dep_fnames)

    if force or reqs_stale(txt_fpath, dep_fpaths):
        print(f'Compiling: {in_fname}')
        pip_compile(
            '--quiet',
            '--strip-extras',
            '--annotate',
            '--generate-hashes',
            '--no-header',
            '--output-file',
            txt_fpath,
            in_fpath,
        )
        return

    print(f'Up-to-date: {txt_fpath.name}')
