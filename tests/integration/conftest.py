from __future__ import print_function
import os
import io
import re
import shlex
import subprocess

import pytest

########################################################################
#                                                                      #
# Set up the required components for an integration test. Components   #
# such as PostgreSQL and Apache are assumed to already be installed on #
# the system. The system is assumed to be Debian. See                  #
# tests/docker/Dockerfile.                                             #
#                                                                      #
########################################################################


def pytest_configure(config):
    subprocess.check_call(['/create-db.sh'])
    subprocess.check_call(['env'])
    os.environ['TARGETURL'] = "http://localhost:8000/"
    subprocess.check_call(['/start-services.sh'])

def pytest_unconfigure(config):
    subprocess.check_call(['/stop-services.sh'])


########################################################################
#                                                                      #
# All to do with discovering all NAV binaries and building fixtures to #
# generate tests for each of them                                      #
#                                                                      #
########################################################################
TESTARGS_PATTERN = re.compile(
    r'^# +-\*-\s*testargs:\s*(?P<args>.*?)\s*(-\*-)?\s*$',
    re.MULTILINE)
NOTEST_PATTERN = re.compile(
    r'^# +-\*-\s*notest\s*(-\*-)?\s*$', re.MULTILINE)
BINDIR = './bin'


def pytest_generate_tests(metafunc):
    if 'binary' in metafunc.fixturenames:
        binaries = _nav_binary_tests()
        ids = [b[0] for b in binaries]
        metafunc.parametrize("binary", _nav_binary_tests(), ids=ids)


def _nav_binary_tests():
    for binary in _nav_binary_list():
        for args in _scan_testargs(binary):
            if args:
                yield args


def _nav_binary_list():
    files = sorted(os.path.join(BINDIR, f)
                   for f in os.listdir(BINDIR)
                   if not _is_excluded(f))
    return (f for f in files if os.path.isfile(f))


def _is_excluded(filename):
    return (filename.endswith('~') or filename.startswith('.') or
            filename.startswith('Makefile'))


def _scan_testargs(filename):
    """
    Scans filename for testargs comments and returns a list of elements
    suitable for invocation of this binary with the given testargs
    """
    print("Getting test args from {}".format(filename))
    contents = io.open(filename, encoding="utf-8").read()
    matches = TESTARGS_PATTERN.findall(contents)
    if matches:
        retval = []
        for testargs, _ in matches:
            testargs = shlex.split(testargs)
            retval.append([filename] + testargs)
        return retval
    else:
        matches = NOTEST_PATTERN.search(contents)
        if not matches:
            return [[filename]]
        else:
            return []

##################
#                #
# Other fixtures #
#                #
##################

@pytest.fixture()
def localhost():
    from nav.models.manage import Netbox
    box = Netbox(ip='127.0.0.1', sysname='localhost.example.org',
                 organization_id='myorg', room_id='myroom', category_id='SRV',
                 read_only='public', snmp_version=2)
    box.save()
    yield box
    print("teardown test device")
    box.delete()
