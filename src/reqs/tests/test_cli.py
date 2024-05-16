from contextlib import contextmanager
from dataclasses import dataclass
import logging
import os
from pathlib import Path
from unittest import mock

from click.testing import CliRunner, Result

from reqs import cli


pkgs_dpath = Path(__file__).parent


@contextmanager
def chdir(path: Path):
    cwd = Path.cwd()
    try:
        os.chdir(path)
        yield
    finally:
        os.chdir(cwd)


@contextmanager
def env_del(*keys):
    current_env = dict(os.environ)
    for key in keys:
        del os.environ[key]
    yield
    for key in keys:
        os.environ[key] = current_env[key]


@dataclass
class Invoke:
    result: Result
    pkg_dpath: Path


def invoke(pkg_name, *args, pkg_chdir=None, **env) -> Result:
    runner = CliRunner(mix_stderr=False)

    pkg_dpath = pkgs_dpath / pkg_name
    from_dpath = pkg_dpath / pkg_chdir if pkg_chdir else pkg_dpath
    with chdir(from_dpath):
        result = runner.invoke(cli.reqs, args, env=env, catch_exceptions=False)

    assert result.exit_code == 0, (result.stdout, result.stderr)
    return Invoke(result, pkg_dpath)


class TestCLI:
    @mock.patch.object(cli, 'reqs_compile')
    def test_compile(self, m_reqs_compile):
        inv: Invoke = invoke('pkg1', 'compile')
        reqs_dpath = inv.pkg_dpath / 'requirements'

        assert not inv.result.stderr
        assert not inv.result.stdout
        assert m_reqs_compile.mock_calls == [
            mock.call(False, reqs_dpath, 'base.in'),
            mock.call(False, reqs_dpath, 'dev.in', 'base.txt'),
            mock.call(False, reqs_dpath, 'ci.in', 'dev.txt'),
        ]

    @mock.patch.object(cli, 'reqs_compile')
    def test_compile_force(self, m_reqs_compile):
        inv: Invoke = invoke('pkg1', 'compile', '--force')
        reqs_dpath = inv.pkg_dpath / 'requirements'

        assert m_reqs_compile.mock_calls == [
            mock.call(True, reqs_dpath, 'base.in'),
            mock.call(True, reqs_dpath, 'dev.in', 'base.txt'),
            mock.call(True, reqs_dpath, 'ci.in', 'dev.txt'),
        ]

    @mock.patch.object(cli, 'reqs_compile')
    def test_path_calc_from_pkg_directory(self, m_reqs_compile):
        """Ensure relative path calculation is done from package directory and not cwd"""
        inv: Invoke = invoke('pkg1', 'compile', '--force', pkg_chdir='foo')

        assert not inv.result.stderr
        assert not inv.result.stdout

    @mock.patch.object(cli, 'pip')
    @mock.patch.object(cli, 'pip_sync')
    @mock.patch.object(cli, 'reqs_compile')
    def test_sync(self, m_reqs_compile, m_pip_sync, m_pip, caplog):
        caplog.set_level(logging.INFO)

        inv: Invoke = invoke('pkg1', 'sync', pkg_chdir='foo', VIRTUAL_ENV='pkg1')
        reqs_dpath = inv.pkg_dpath / 'requirements'

        assert not inv.result.stderr
        assert [rec.message for rec in caplog.records] == [
            'Installing requirements/dev.txt to venv @ pkg1',
        ]
        assert m_reqs_compile.mock_calls == [
            mock.call(False, reqs_dpath, 'base.in'),
            mock.call(False, reqs_dpath, 'dev.in', 'base.txt'),
            mock.call(False, reqs_dpath, 'ci.in', 'dev.txt'),
        ]
        assert m_pip_sync.mock_calls == [
            mock.call('--quiet', reqs_dpath / 'dev.txt'),
        ]
        assert m_pip.mock_calls == [
            mock.call('install', '--quiet', '-e', inv.pkg_dpath),
        ]

    @mock.patch.object(cli, 'pipx_install')
    @mock.patch.object(cli, 'pip')
    @mock.patch.object(cli, 'pip_sync')
    @mock.patch.object(cli, 'reqs_compile')
    def test_sync_no_venv_no_compile_with_pipx(
        self,
        m_reqs_compile,
        m_pip_sync,
        m_pip,
        m_pipx_install,
    ):
        with env_del('VIRTUAL_ENV'):
            inv: Invoke = invoke('pkg2', 'sync', '--no-compile')

        assert not inv.result.stderr
        assert not inv.result.stdout
        assert m_reqs_compile.mock_calls == []
        assert m_pip_sync.mock_calls == []
        assert m_pip.mock_calls == []
        assert m_pipx_install.mock_calls == [mock.call('install', '--force', '-e', inv.pkg_dpath)]
