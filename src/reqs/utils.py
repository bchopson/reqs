from collections.abc import Iterable as Iter
from dataclasses import dataclass
import logging
import os
from os import environ
from pathlib import Path
import shlex
import subprocess

from pip_requirements_parser import RequirementsFile


log = logging.getLogger()


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


@dataclass
class Dep:
    path: Path
    compiled: bool = False
    needs: list[Path] = None

    @property
    def path_txt(self):
        return self.path.with_suffix('.txt')

    def _opt_line_needs(self, opt_line):
        yield from (
            *opt_line.options.get('constraints', ()),
            *opt_line.options.get('requirements', ()),
        )

    def __post_init__(self):
        req_file = RequirementsFile.from_file(self.path)
        needs = []
        for opt_line in req_file.options:
            needs.extend(self._opt_line_needs(opt_line))

        self.needs = [
            self.path.parent.joinpath(need_path) if not Path(need_path).is_absolute() else need_path
            for need_path in needs
        ]
        if self.path.suffix == '.txt':
            self.compiled = True

    def txt_stale(self):
        txt_fpath = self.path_txt
        if not txt_fpath.exists():
            return True

        txt_mtime = txt_fpath.stat().st_mtime
        if self.path.stat().st_mtime >= txt_mtime:
            return True

        if not self.needs:
            return

        # If our txt file was modified before any of our needs then it has become stale.
        if txt_mtime <= max(need.stat().st_mtime for need in self.needs):
            return True

    def compile(self, force: bool, upgrade_packages: Iter[str]):
        if self.compiled:
            log.debug('already compiled: %s', self.path)
            return

        if force or self.txt_stale():
            log.info('compiling: %s', self.path.name)

            extra_args = []
            for pkg in upgrade_packages:
                extra_args.append('--upgrade-package')
                extra_args.append(pkg)

            pip_compile(
                '--quiet',
                '--strip-extras',
                '--annotate',
                '--generate-hashes',
                '--no-header',
                '--output-file',
                self.path.with_suffix('.txt'),
                self.path,
                *extra_args,
            )
        else:
            log.info('already current: %s', self.path.name)

        self.compiled = True


class DepHandler:
    def __init__(self, reqs_dpath: Path):
        self.reqs_dpath: Path = reqs_dpath

    def compile_all(self, force: bool = False, upgrade_packages: Iter[str] = ()):
        reqs_files: dict[Path, Dep] = {p: Dep(p) for p in sorted(self.reqs_dpath.glob('*.in'))}

        if not reqs_files:
            log.warning('No .in files found at: %s', self.reqs_dpath)
            return

        os.chdir(self.reqs_dpath.parent)
        for dep in list(reqs_files.values()):
            self._compile(reqs_files, dep, force, upgrade_packages)

    def _compile(
        self,
        reqs_files: dict[Path, Dep],
        dep: Dep,
        force: bool,
        upgrade_packages: Iter[str],
    ):
        for needs_fpath in dep.needs:
            # TODO: I don't know that this is needed
            needs_in_fpath = needs_fpath.with_suffix('.in')
            if needs_fpath.suffix == '.txt' and needs_in_fpath.exists():
                needs_fpath = needs_in_fpath

            if not needs_fpath.exists():
                raise RuntimeError(
                    f'{dep.path.relative_to(self.reqs_dpath)} references a non-existant path:'
                    f' {needs_fpath.relative_to(self.reqs_dpath)}',
                )

            need_dep: Dep = reqs_files.get(needs_fpath) or Dep(needs_fpath)
            reqs_files[needs_fpath] = need_dep
            self._compile(reqs_files, need_dep, force, upgrade_packages)

        dep.compile(force, upgrade_packages)
