from contextlib import contextmanager
import logging
import os
from pathlib import Path
from unittest import mock

from reqs import cli
from reqs.libs.testing import Package


pkgs_dpath = Path(__file__).parent


@contextmanager
def env_del(*keys):
    current_env = dict(os.environ)
    for key in keys:
        del os.environ[key]
    yield
    for key in keys:
        os.environ[key] = current_env[key]


class TestCLI:
    def test_compile_no_mocking(self):
        package = Package('pkg1')
        package.txt_unlink()
        assert len(package.txt_reqs()) == 0

        package.invoke(cli, 'compile')
        assert len(package.txt_reqs()) == 3

    def test_upgrade(self, tmp_path):
        package = Package(tmp_path)
        # Packages chosen b/c pytest uses them and the pip cache will already have the
        # package downloaded.  Also b/c they currently have no transitive deps.
        package.reqs_create('base.in', 'pluggy == 1.4.0')
        package.reqs_create('dev.in', '-r base.txt', 'iniconfig == 1.1.1')

        package.invoke(cli, 'compile')
        assert 'pluggy==1.4.0' in package.reqs_text('dev.txt')
        assert 'iniconfig==1.1.1' in package.reqs_text('dev.txt')

        package.reqs_create('base.in', 'pluggy')
        package.reqs_create('dev.in', '-r base.txt', 'iniconfig')

        package.invoke(cli, '--verbose', 'upgrade', 'pluggy', 'iniconfig')
        dev_reqs = package.reqs_text('dev.txt')
        assert 'pluggy==1.4.0' not in dev_reqs and 'pluggy==' in dev_reqs
        assert 'iniconfig==1.1.1' not in dev_reqs and 'iniconfig==' in dev_reqs

    @mock.patch.object(cli, 'compile_all')
    @mock.patch.object(cli, 'conf_prep')
    def test_compile_force(self, m_conf_prep, m_compile_all):
        Package('pkg1').invoke(cli, 'compile')
        m_compile_all.assert_called_once_with(
            False,
            m_conf_prep.return_value,
        )

        Package('pkg1').invoke(cli, 'compile', '--force')
        m_compile_all.assert_called_with(
            True,
            m_conf_prep.return_value,
        )

    @mock.patch.object(cli, 'compile_all')
    def test_path_calc_from_pkg_directory(self, m_compile_all):
        """Ensure relative path calculation is done from package directory and not cwd"""
        result = Package('pkg1').invoke(cli, 'compile', '--force', pkg_chdir='foo')

        assert not result.stderr
        assert not result.stdout

    @mock.patch.object(cli, 'pip')
    @mock.patch.object(cli, 'pip_sync')
    @mock.patch.object(cli, 'compile_all')
    def test_sync(self, m_compile_all, m_pip_sync, m_pip, caplog):
        caplog.set_level(logging.INFO)

        package = Package('pkg1')
        result = package.invoke(cli, 'sync', pkg_chdir='foo', VIRTUAL_ENV='pkg1')

        assert not result.stderr
        assert [rec.message for rec in caplog.records] == [
            'Installing requirements/dev.txt to venv @ pkg1',
        ]
        m_compile_all.assert_called_once_with(
            False,
            mock.ANY,
        )
        assert m_pip_sync.mock_calls == [
            mock.call('--quiet', package.reqs_dpath / 'dev.txt'),
        ]
        assert m_pip.mock_calls == [
            mock.call('install', '--quiet', '-e', package.dpath),
        ]

    @mock.patch.object(cli, 'pipx_install')
    @mock.patch.object(cli, 'pip')
    @mock.patch.object(cli, 'pip_sync')
    @mock.patch.object(cli, 'compile_all')
    def test_sync_no_venv_no_compile_with_pipx(
        self,
        m_compile_all,
        m_pip_sync,
        m_pip,
        m_pipx_install,
    ):
        package = Package('pkg2')

        with env_del('VIRTUAL_ENV'):
            result = package.invoke(cli, 'sync', '--no-compile')

        assert not result.stderr
        assert not result.stdout
        assert m_compile_all.mock_calls == []
        assert m_pip_sync.mock_calls == []
        assert m_pip.mock_calls == []
        assert m_pipx_install.mock_calls == [mock.call('install', '--force', '-e', package.dpath)]
