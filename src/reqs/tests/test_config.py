from pathlib import Path

from reqs import config


tests_dpath = Path(__file__).parent


def load(*start_at):
    return config.load(tests_dpath.joinpath(*start_at))


class TestConfig:
    def test_depends_default(self):
        c: config.Config = load('pkg1')
        assert c.pkg_dpath == tests_dpath.joinpath('pkg1')
        assert c.reqs_dpath == tests_dpath.joinpath('pkg1', 'requirements')
        assert not c.sync_pipx
        assert c.depends == [
            config.Depends('base.in', []),
            config.Depends('ci.in', ['base.txt']),
            config.Depends('dev.in', ['base.txt', 'ci.txt']),
        ]

    def test_depends_explicit(self):
        c: config.Config = load('pkg2')
        assert c.reqs_dpath == tests_dpath.joinpath('pkg2', 'reqs')
        assert c.sync_pipx
        assert c.depends == [
            config.Depends('common.in', []),
            config.Depends('dev.in', ['common.txt']),
        ]

    def test_base_only(self):
        c: config.Config = load('pkg3')
        assert c.depends == [
            config.Depends('base.in', []),
        ]

    def test_warning(self):
        with pytest.warns(UserWarning, match=r'More than one \.in file'):
            c: config.Config = load('pkg4')

        assert c.depends == [
            config.Depends('base.in', []),
            config.Depends('foo.in', []),
        ]
