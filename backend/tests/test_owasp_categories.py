import os
import pathlib
import importlib.util
import pytest


def load_owasp_module():
    # Prefer tools/owasp/OWASPCheck.py so the helpers are not collected as tests
    repo_root = pathlib.Path(__file__).resolve().parents[2]
    tools_owasp = repo_root / 'tools' / 'owasp' / 'OWASPCheck.py'
    tests_dir = pathlib.Path(__file__).parent
    if tools_owasp.exists():
        owasp_path = tools_owasp
    else:
        owasp_path = tests_dir / 'OWASPCheck.py'

    spec = importlib.util.spec_from_file_location('owasp', str(owasp_path))
    if spec is None:
        raise ImportError(f"Could not load spec for {owasp_path}")
    module = importlib.util.module_from_spec(spec)
    loader = getattr(spec, 'loader', None)
    if loader is None:
        raise ImportError(f"No loader available for {owasp_path}")
    loader.exec_module(module)
    return module


pytestmark = pytest.mark.functional


@pytest.fixture(scope='module')
def tester(start_fastapi_server):
    requests = pytest.importorskip('requests')
    base_url = os.getenv('TEST_BASE_URL', 'http://localhost:8000')
    # quick reachability check
    try:
        r = requests.get(base_url + '/', timeout=3)
    except Exception:
        pytest.skip(f"Backend not reachable at {base_url}; skipping OWASP category tests")

    module = load_owasp_module()
    OWASPSecurityTester = getattr(module, 'OWASPSecurityTester')
    return OWASPSecurityTester(base_url=base_url)


def _assert_no_high_critical(issues):
    bad = [i for i in issues if i.severity.value in ('CRITICAL', 'HIGH')]
    if bad:
        msgs = [f"{i.title} ({i.severity.value}): {i.evidence}" for i in bad]
        pytest.fail('\n'.join(msgs))


def test_broken_access_control(tester):
    issues = tester.test_a01_broken_access_control()
    _assert_no_high_critical(issues)


def test_injection_checks(tester):
    issues = tester.test_a03_injection()
    _assert_no_high_critical(issues)


def test_rate_limiting_and_insecure_design(tester):
    issues = tester.test_a04_insecure_design()
    _assert_no_high_critical(issues)


def test_security_misconfiguration(tester):
    issues = tester.test_a05_security_misconfiguration()
    _assert_no_high_critical(issues)


def test_vulnerable_components(tester):
    issues = tester.test_a06_vulnerable_components()
    _assert_no_high_critical(issues)


def test_identification_and_auth_failures(tester):
    issues = tester.test_a07_identification_auth_failures()
    _assert_no_high_critical(issues)


def test_software_and_data_integrity(tester):
    issues = tester.test_a08_software_data_integrity()
    _assert_no_high_critical(issues)


def test_logging_and_monitoring(tester):
    issues = tester.test_a09_security_logging_monitoring()
    _assert_no_high_critical(issues)


def test_ssrf(tester):
    issues = tester.test_a10_server_side_request_forgery()
    _assert_no_high_critical(issues)
