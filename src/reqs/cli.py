import logging
from os import environ
from pathlib import Path
from pprint import pprint

import click

from . import config
from .utils import pip, pip_sync, pipx_install, reqs_compile


log = logging.getLogger()


def conf_prep() -> config.Config:
    cwd = Path.cwd()
    conf: config.Config = config.load(cwd)
    dpath_relative: str = conf.reqs_dpath.relative_to(conf.pkg_dpath)
    print(f'Requirements directory: {dpath_relative}')

    return conf


def _compile(force: bool, conf: config.Config):
    for dep in conf.depends:
        reqs_compile(force, conf.reqs_dpath, dep.fname, *dep.depends_on)


@click.group()
def reqs():
    pass


@reqs.command()
def bootstrap():
    """Upgrade pip & install pip-tools"""
    print('Upgrading pip and installing pip-tools')
    pip('install', '--quiet', '-U', 'pip', 'pip-tools')


@reqs.command('config')
def _config():
    """Show reqs config"""
    conf = conf_prep()
    print(conf)
    print('pip', '--version:', pip('--version'))


@reqs.command()
@click.option('--force', is_flag=True, help='Force compile regardless of file timestamps')
def compile(force: bool):
    """Compile .in to .txt when needed"""
    conf = conf_prep()
    _compile(force, conf)


@reqs.command()
@click.argument('req_fname', default='dev.txt')
@click.option('--compile/--no-compile', default=True)
@click.option('--force', is_flag=True, help='Force compile regardless of file timestamps')
def sync(req_fname: str, compile: bool, force: bool):
    """Update active venv and maybe pipx to match spec"""
    conf = conf_prep()

    if compile:
        _compile(force, conf)

    if 'VIRTUAL_ENV' in environ:
        # Install reqs into active venv
        reqs_fpath = conf.reqs_dpath / req_fname
        print(f'Installing {reqs_fpath.relative_to(conf.pkg_dpath)}')
        pip_sync(reqs_fpath)
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
