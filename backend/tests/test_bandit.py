import json
import os

import pytest


def _load_baseline(path):
    if not os.path.exists(path):
        return {}
    with open(path, "r") as f:
        return json.load(f)


def test_bandit_baseline(tmp_path):
    """
    Run bandit programmatically (if installed) and compare results against a baseline.
    This test will be skipped if bandit is not available in the test environment.
    """
    try:
        import bandit
        from bandit.core import config as b_config
        from bandit.core import manager as b_manager
    except Exception:
        pytest.skip(
            "bandit not installed in test environment; skipping static security scan"
        )

    # locate project root
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    bconf = b_config.BanditConfig()
    mgr = b_manager.BanditManager(bconf, "file")
    # run on the backend package
    try:
        mgr.discover_files([os.path.join(repo_root, "backend")])
        mgr.run_tests()
    except Exception as exc:
        # If bandit raises, surface it as test failure (important to know static analyzer errors)
        pytest.fail(f"bandit failed to run: {exc}")

    # summarise results
    issues = []
    for res in mgr.get_issue_list():
        issues.append(
            {
                "filename": res.filename,
                "test_name": res.test_name,
                "issue_severity": res.issue_severity,
                "issue_confidence": res.issue_confidence,
                "line_number": res.lineno,
                "text": res.text,
            }
        )

    # load baseline expectations
    baseline_path = os.path.join(repo_root, "security", "bandit_baseline.json")
    baseline = _load_baseline(baseline_path)

    # If there are new high or medium severity findings that are not in baseline, fail
    new_issues = []
    for i in issues:
        if i["issue_severity"] in ("HIGH", "MEDIUM"):
            key = f"{i['filename']}:{i['line_number']}:{i['test_name']}"
            if key not in baseline.get("allowed", []):
                new_issues.append(i)

    if new_issues:
        pretty = json.dumps(new_issues, indent=2)
        pytest.fail(f"New bandit findings detected:\n{pretty}")
