import os
import json
import shutil
import subprocess
import pytest


def test_safety_scan():
    """Run safety against the project's requirements file.

    - Skips if `requirements.txt` is missing or `safety` is not installed.
    - Fails if safety reports vulnerabilities.
    """
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    req_file = os.path.join(repo_root, 'requirements.txt')
    if not os.path.exists(req_file):
        pytest.skip('requirements.txt not found; skipping safety scan')

    # Prefer the installed safety CLI if available
    safety_cmd = shutil.which('safety')
    if not safety_cmd:
        try:
            import safety  # noqa: F401
            safety_cmd = shutil.which('safety')
        except Exception:
            safety_cmd = None

    if not safety_cmd:
        pytest.skip('safety not installed in test environment; skipping dependency vulnerability scan')

    # Run safety in JSON mode against the requirements file
    cmd = [safety_cmd, 'check', '--file', req_file, '--json']
    proc = subprocess.run(cmd, cwd=repo_root, capture_output=True, text=True)

    stdout = (proc.stdout or '').strip()
    stderr = (proc.stderr or '').strip()

    # safety returns exit code 1 when vulnerabilities are found; non-zero otherwise indicates an error
    if proc.returncode not in (0, 1):
        pytest.fail(f'safety failed to run (rc={proc.returncode})\nstderr:\n{stderr}')

    # Parse JSON output from stdout or stderr
    data = None
    for maybe in (stdout, stderr):
        if not maybe:
            continue
        try:
            data = json.loads(maybe)
            break
        except Exception:
            continue

    if data is None:
        # If safety signalled vulnerabilities (rc==1) but no JSON parseable output, fail and include raw output
        if proc.returncode == 1:
            pytest.fail(f'safety reported vulnerabilities but output could not be parsed. stdout:\n{stdout}\nstderr:\n{stderr}')
        pytest.skip('safety produced no JSON output; skipping detailed checks')

    # Normalize vulnerability list
    vulns = []
    if isinstance(data, dict):
        # Common keys: 'vulnerabilities' or 'results'
        for key in ('vulnerabilities', 'results', 'discovered_vulnerabilities'):
            if key in data and isinstance(data[key], list):
                vulns = data[key]
                break
        # some versions return a top-level list encoded as dict; handle gracefully
        if not vulns:
            for v in data.get('dependencies', []):
                if isinstance(v, dict):
                    vulns.append(v)
    elif isinstance(data, list):
        vulns = data

    if vulns:
        # Build a compact summary for the test failure
        lines = []
        for v in vulns:
            name = v.get('package_name') or v.get('name') or v.get('package') or 'unknown'
            ver = v.get('installed_version') or v.get('version') or ''
            advisory = v.get('advisory') or v.get('description') or v.get('cve') or ''
            sev = v.get('severity') or v.get('id') or ''
            lines.append(f"{name} {ver} {sev}: {advisory}")
        summary = '\n'.join(lines[:50])
        pytest.fail(f'safety detected {len(vulns)} vulnerable dependencies:\n{summary}')
