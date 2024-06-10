import logging
import os
from pathlib import Path
import time

from reqs.utils import Dep, DepHandler

from ..libs.testing import Package as _Package
from ..libs.testing import logs


tests_dpath = Path(__file__).parent


class Package(_Package):
    def dep_handler(self, keep=None):
        self.txt_unlink(keep)
        return DepHandler(self.reqs_dpath)

    def dep_from(self, fname):
        return Dep(self.reqs_fpath(fname))

    def touch_shift(self, fname, *, shift=1):
        path = self.reqs_fpath(fname)

        path.touch()

        to_time = time.time() + shift

        # Apply the new access and modification times using os.utime
        os.utime(path, (to_time, to_time))


class TestDep:
    def test_needs(self):
        pkg1 = Package('pkg1')
        dep = pkg1.dep_from('charlie.in')
        assert not dep.needs

        dep = pkg1.dep_from('bravo.in')
        assert dep.needs == [pkg1.reqs_fpath('charlie.txt')]

        dep = pkg1.dep_from('alpha.in')
        assert dep.needs == [pkg1.reqs_fpath('bravo.txt'), pkg1.reqs_fpath('charlie.txt')]

    def test_txt_stale(self):
        pkg1 = Package('pkg1')
        pkg1.txt_unlink()

        # No .txt file
        dep = pkg1.dep_from('charlie.in')
        assert dep.txt_stale()

        # .txt file newer
        dep.path_txt.touch()
        assert not dep.txt_stale()

        # .txt file older
        dep.path.touch()
        assert dep.txt_stale()

        # No .txt file
        dep = pkg1.dep_from('bravo.in')
        pkg1.touch_shift('bravo.txt')

        # bravo's txt file newer than its .in
        assert not dep.txt_stale()

        pkg1.touch_shift('charlie.txt')

        # bravo's txt file is now older than charlie.txt
        assert dep.txt_stale()

        # No .txt file
        dep = pkg1.dep_from('alpha.in')
        pkg1.touch_shift('alpha.txt')

        # bravo's txt file is older than alpha's
        pkg1.touch_shift('charlie.txt', shift=-1)
        assert not dep.txt_stale()

        # charlies's txt file is newer than alpha's, making alpha's stale
        pkg1.touch_shift('charlie.txt')
        assert dep.txt_stale()


class TestDepHandler:
    def test_no_files(self, caplog):
        dh = Package('pkg2').dep_handler()
        dh.compile_all()
        assert caplog.records[0].message == f'No .in files found at: {dh.reqs_dpath}'

    def test_files_with_no_options(self):
        pkg = Package('pkg4')
        dh = pkg.dep_handler()
        dh.compile_all()
        assert pkg.txt_names() == ['base.txt', 'foo.txt']

    def test_dependent(self):
        pkg = Package('pkg1')
        pkg.dep_handler().compile_all()
        assert '#   -r requirements/charlie.txt' in pkg.reqs_text('alpha.txt')
        assert '#   -c requirements/bravo.txt' in pkg.reqs_text('alpha.txt')
        assert 'via -r requirements/charlie.txt' in pkg.reqs_text('bravo.txt')
        assert 'via -r requirements/charlie.in' in pkg.reqs_text('charlie.txt')

    def test_transient_deps_modified(self, caplog):
        pkg = Package('pkg1')
        dh = pkg.dep_handler()
        dh.compile_all(force=True)

        pkg.touch_shift('charlie.in')
        caplog.clear()
        caplog.set_level(logging.INFO)
        dh.compile_all()

        assert logs(caplog) == [
            'compiling: charlie.in',
            'compiling: bravo.in',
            'compiling: alpha.in',
        ]

        assert '#   -r requirements/charlie.txt' in pkg.reqs_text('alpha.txt')
        assert 'via -r requirements/charlie.txt' in pkg.reqs_text('bravo.txt')
        assert 'via -r requirements/charlie.in' in pkg.reqs_text('charlie.txt')

    def test_txt_only_dep(self, caplog):
        caplog.set_level(logging.INFO)

        pkg = Package('pkg5')
        dh = pkg.dep_handler(keep='charlie.txt')
        dh.compile_all(force=True)

        assert logs(caplog) == [
            'compiling: bravo.in',
            'compiling: alpha.in',
        ]

        assert '#   -r requirements/charlie.txt' in pkg.reqs_text('alpha.txt')
        assert 'via -r requirements/charlie.txt' in pkg.reqs_text('bravo.txt')
