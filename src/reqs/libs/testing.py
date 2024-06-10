from contextlib import contextmanager
import os
from pathlib import Path
from unittest import mock

from click.testing import CliRunner, Result

import reqs.tests


tests_dpath = Path(reqs.tests.__file__).parent


def mock_patch_obj(*args, **kwargs):
    kwargs.setdefault('autospec', True)
    kwargs.setdefault('spec_set', True)
    return mock.patch.object(*args, **kwargs)


def mock_patch(*args, **kwargs):
    kwargs.setdefault('autospec', True)
    kwargs.setdefault('spec_set', True)
    return mock.patch(*args, **kwargs)


def logs(caplog):
    return [rec.message for rec in caplog.records]


@contextmanager
def chdir(path: Path):
    cwd = Path.cwd()
    try:
        os.chdir(path)
        yield
    finally:
        os.chdir(cwd)


class Package:
    def __init__(self, pkg_name_or_root: str | Path):
        if Path(pkg_name_or_root).is_absolute():
            self.dpath: Path = pkg_name_or_root
        else:
            self.dpath: Path = tests_dpath / pkg_name_or_root
        self.reqs_dpath = self.dpath / 'requirements'

    def invoke(self, cli, *args, pkg_chdir=None, **env) -> Result:
        runner = CliRunner(mix_stderr=False)

        from_dpath = self.dpath / pkg_chdir if pkg_chdir else self.dpath
        with chdir(from_dpath):
            result = runner.invoke(cli.reqs, args, env=env, catch_exceptions=False)

        assert result.exit_code == 0, (result.stdout, result.stderr)
        return result

    def txt_reqs(self) -> list[Path]:
        return sorted(self.reqs_dpath.glob('*.txt'))

    def txt_names(self):
        return [p.name for p in self.txt_reqs()]

    def txt_unlink(self, keep=None):
        keep = keep or ()

        for txt_fpath in self.txt_reqs():
            if txt_fpath.name in keep:
                continue
            txt_fpath.unlink()

    def reqs_fpath(self, fname: str):
        return self.reqs_dpath / fname

    def reqs_text(self, fname: str):
        return self.reqs_dpath.joinpath(fname).read_text()

    def reqs_create(self, fname: str, *lines):
        reqs_fpath = self.reqs_fpath(fname)
        self.reqs_dpath.mkdir(exist_ok=True)
        self.dpath.joinpath('pyproject.toml').touch()

        reqs_fpath.write_text('\n'.join(lines))
