import subprocess
import os

THIS_DIR = os.path.dirname(__file__)
MOD_DIR = os.path.join(THIS_DIR, '..')


def test_flake8():
    retcode = subprocess.call([
        'flake8', '--ignore=E123,E125,E126,E128,E711',
        '--exclude=__version__.py', MOD_DIR
    ])
    assert retcode == 0
