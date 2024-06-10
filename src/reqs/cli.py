from collections.abc import Iterable as Iter
import logging
from os import environ
from pathlib import Path
import sys

import click

from . import config
from .utils import DepHandler, pip, pip_sync, pipx_install


log = logging.getLogger()


def conf_prep() -> config.Config:
    cwd = Path.cwd()
    conf: config.Config = config.load(cwd)
    dpath_relative: str = conf.reqs_dpath.relative_to(conf.pkg_dpath)
    log.debug(f'Requirements directory: {dpath_relative}')

    return conf


def compile_all(force: bool, conf: config.Config, upgrade_packages: Iter[str] = ()):
    DepHandler(conf.reqs_dpath).compile_all(force, upgrade_packages)


@click.group()
@click.option('--quiet', is_flag=True)
@click.option('--verbose', is_flag=True)
def reqs(quiet: bool, verbose: bool):
    level = logging.WARNING if quiet else (logging.DEBUG if verbose else logging.INFO)
    logging.getLogger('reqs').setLevel(level)
    logging.basicConfig(level=level, format='%(levelname)8s %(message)s')


@reqs.command()
@click.option('--uv/--no-uv', 'use_uv', default=True)
def bootstrap(use_uv: bool):
    """Install uv (default) or pip-tools to compile .in files"""
    if use_uv:
        log.info('Installing and/or upgrading uv')
        pip('install', '--quiet', '-U', 'uv')
    else:
        log.info('Upgrading pip and installing pip-tools')
        pip('install', '--quiet', '-U', 'pip', 'pip-tools')


@reqs.command('config')
def _config():
    """Show reqs config"""
    conf = conf_prep()
    print(conf)
    pip('--version')
    print(sys.executable)
    print('PATH:', environ.get('PATH'))


@reqs.command()
@click.option('--force', is_flag=True, help='Force compile regardless of file timestamps')
def compile(force: bool):
    """Compile .in to .txt when needed"""
    conf = conf_prep()
    compile_all(force, conf)


@reqs.command()
@click.argument('packages', nargs=-1)
def upgrade(packages: list[str]):
    """Upgrade package(s) to latest version"""
    conf = conf_prep()
    compile_all(True, conf, packages)


@reqs.command()
@click.argument('req_fname', default='dev.txt')
@click.option('--compile/--no-compile', default=True)
@click.option('--force', is_flag=True, help='Force compile regardless of file timestamps')
def sync(req_fname: str, compile: bool, force: bool):
    """Update active venv and maybe pipx to match spec"""
    conf = conf_prep()

    if compile:
        compile_all(force, conf)

    if venv_path := environ.get('VIRTUAL_ENV'):
        # Install reqs into active venv
        reqs_fpath = conf.reqs_dpath / req_fname
        log.info(f'Installing {reqs_fpath.relative_to(conf.pkg_dpath)} to venv @ {venv_path}')
        pip_sync('--quiet', reqs_fpath)
        pip('install', '--quiet', '-e', conf.pkg_dpath)
    else:
        log.warning('Virtualenv not activated, skipping venv sync')

    if conf.sync_pipx:
        # TODO: enable configuring python version to use with pipx
        # Use install instead of upgrade so that pipx venv is refreshed even if pkg version number
        # has not changed (which will be common with editable installs).
        pipx_install('install', '--force', '-e', conf.pkg_dpath)


if __name__ == '__main__':
    reqs()
