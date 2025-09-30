import importlib.machinery
import importlib.util
import os
import pathlib

import pytest


def load_module_from_path(path, name="owasp_check"):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None:
        raise ImportError(f"Could not load spec for {path}")
    module = importlib.util.module_from_spec(spec)
    loader = getattr(spec, "loader", None)
    if loader is None:
        raise ImportError(f"No loader available for {path}")
    loader.exec_module(module)
    return module


pytestmark = pytest.mark.functional


@pytest.mark.timeout(300)
def test_run_owasp_checks_smoke(start_fastapi_server):
    """Smoke-run the OWASP checks as a pytest test.

    - Skips if requests isn't available.
    - Skips if the backend at TEST_BASE_URL isn't reachable.
    - Loads tests/OWASPCheck.py dynamically so imports work regardless of package layout.
    """
    requests = pytest.importorskip("requests")

    try:
        from backend.app.core.config import settings

        base_url = settings.TEST_BASE_URL.rstrip("/")
    except Exception:
        # Fallback to a sensible default when settings cannot be imported
        base_url = "http://localhost:8000"

    # Quick reachability check
    try:
        r = requests.get(base_url + "/", timeout=3)
    except Exception:
        pytest.skip(f"Backend not running at {base_url}; skipping OWASP checks")

    # Prefer OWASP helper from tools/owasp to avoid pytest collection; fall back
    # to backend/tests/OWASPCheck.py for compatibility.
    repo_root = pathlib.Path(__file__).resolve().parents[2]
    tools_owasp = repo_root / "tools" / "owasp" / "OWASPCheck.py"
    tests_dir = pathlib.Path(__file__).parent
    fallback_owasp = tests_dir / "OWASPCheck.py"

    if tools_owasp.exists():
        owasp_path = tools_owasp
    else:
        owasp_path = fallback_owasp

    assert owasp_path.exists(), f"OWASPCheck.py not found at {owasp_path}"

    module = load_module_from_path(str(owasp_path), name="tests.OWASPCheck")
    OWASPSecurityTester = getattr(module, "OWASPSecurityTester", None)
    assert (
        OWASPSecurityTester is not None
    ), "OWASPSecurityTester not found in OWASPCheck.py"

    tester = OWASPSecurityTester(base_url=base_url)
    summary = tester.run_comprehensive_security_test()
    assert isinstance(summary, dict)
    assert "total_issues" in summary


def test_check_advanced_tools_availability():
    """Import and execute the check_advanced_dependencies() function from the advanced script."""
    adv_path = pathlib.Path(__file__).parent / "test_advanced_security.py"
    assert adv_path.exists(), f"advanced script not found at {adv_path}"
    module = load_module_from_path(str(adv_path), name="tests.advanced_security")
    func = getattr(module, "check_advanced_dependencies", None)
    assert (
        func is not None
    ), "check_advanced_dependencies not found in test_advanced_security.py"
    status = func()
    assert isinstance(status, dict)
