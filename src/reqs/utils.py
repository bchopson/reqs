from pathlib import Path
import subprocess


def run(*args, check=True, **kwargs):
    args = args + kwargs.pop('args', ())
    return subprocess.run(args, **kwargs)


def pip(*args, **kwargs):
    run('pip', args=args, **kwargs)


def pip_sync(*args, **kwargs):
    run('pip-sync', args=args, **kwargs)


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
        run(
            'pip-compile',
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
