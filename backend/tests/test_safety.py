import json
import os
import shutil
import subprocess
from datetime import datetime

import pytest


def test_safety_scan():
    """Run safety against the project's requirements file.

    - Skips if `requirements.txt` is missing or `safety` is not installed.
    - Fails if safety reports vulnerabilities.
    """
    # Make this expensive / environment-dependent scan opt-in. Check the
    # central settings (so it can be configured via .env or environment).
    try:
        from backend.app.core.config import reload_settings, settings

        # Ensure settings reflect the current process environment (pytest may import config earlier)
        try:
            reload_settings()
        except Exception:
            pass
        if not getattr(settings, "RUN_SECURITY_TESTS", False):
            pytest.skip(
                "security scans are opt-in; set RUN_SECURITY_TESTS=1 in .env to enable"
            )
    except Exception:
        # If config cannot be imported, fall back to env var behavior
        _env_val = os.environ.get("RUN_SECURITY_TESTS", "")
        if str(_env_val).lower() not in ("1", "true", "yes", "on"):
            pytest.skip("security scans are opt-in; set RUN_SECURITY_TESTS=1 to enable")

    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    req_file = os.path.join(repo_root, "requirements.txt")
    if not os.path.exists(req_file):
        pytest.skip("requirements.txt not found; skipping safety scan")

    # Prefer the installed safety CLI if available
    safety_cmd = shutil.which("safety")
    if not safety_cmd:
        try:
            import safety  # noqa: F401

            safety_cmd = shutil.which("safety")
        except Exception:
            safety_cmd = None

    # If safety isn't on PATH, try common virtualenv locations under the repo
    if not safety_cmd:
        possible = [
            os.path.join(repo_root, ".venv", "bin", "safety"),
            os.path.join(repo_root, "venv", "bin", "safety"),
            os.path.join(repo_root, "backend", ".venv", "bin", "safety"),
        ]
        for p in possible:
            if os.path.exists(p) and os.access(p, os.X_OK):
                safety_cmd = p
                break

    if not safety_cmd:
        pytest.skip(
            "safety not installed in test environment; skipping dependency vulnerability scan"
        )

    # Run safety in JSON mode against the requirements file
    cmd = [safety_cmd, "check", "--file", req_file, "--json"]
    proc = subprocess.run(cmd, cwd=repo_root, capture_output=True, text=True)

    stdout = (proc.stdout or "").strip()
    stderr = (proc.stderr or "").strip()

    # safety returns exit code 1 when vulnerabilities are found; non-zero otherwise indicates an error
    if proc.returncode not in (0, 1):
        pytest.fail(f"safety failed to run (rc={proc.returncode})\nstderr:\n{stderr}")

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
        # Fallback: sometimes the CLI prints non-JSON text mixed with a JSON blob
        combined = (stdout or "") + "\n" + (stderr or "")
        if combined and ("{" in combined or "[" in combined):
            # try to extract the first {...} or [...] balanced JSON chunk
            start = None
            end = None
            # Prefer object
            if "{" in combined and "}" in combined:
                start = combined.find("{")
                end = combined.rfind("}")
            elif "[" in combined and "]" in combined:
                start = combined.find("[")
                end = combined.rfind("]")
            if start is not None and end is not None and end > start:
                maybe_json = combined[start : end + 1]
                try:
                    data = json.loads(maybe_json)
                except Exception:
                    data = None

    if data is None:
        # If safety signalled vulnerabilities (rc==1) but no JSON parseable output, fail and include raw output
        if proc.returncode == 1:
            pytest.fail(
                f"safety reported vulnerabilities but output could not be parsed. stdout:\n{stdout}\nstderr:\n{stderr}"
            )
        pytest.skip("safety produced no JSON output; skipping detailed checks")

    # Normalize vulnerability list
    vulns = []
    if isinstance(data, dict):
        # Common keys: 'vulnerabilities' or 'results'
        for key in ("vulnerabilities", "results", "discovered_vulnerabilities"):
            if key in data and isinstance(data[key], list):
                vulns = data[key]
                break
        # some versions return a top-level list encoded as dict; handle gracefully
        if not vulns:
            for v in data.get("dependencies", []):
                if isinstance(v, dict):
                    vulns.append(v)
    elif isinstance(data, list):
        vulns = data

    # Filter out ignored vulnerabilities (safety policy or defaults may ignore unpinned requirements)
    significant = [v for v in vulns if not v.get("ignored")]

    # If this run was enabled via the settings env flag, save a JSON artifact for later review.
    try:
        from backend.app.core.config import settings

        save_artifact = getattr(settings, "RUN_SECURITY_TESTS", False)
    except Exception:
        save_artifact = os.environ.get("RUN_SECURITY_TESTS", "") in (
            "1",
            "true",
            "yes",
            "on",
        )

    if save_artifact:
        try:
            artifact_dir = os.path.join(repo_root, "security")
            os.makedirs(artifact_dir, exist_ok=True)
            ts = datetime.utcnow().strftime("%Y%m%d_%H%M%SZ")
            artifact_path = os.path.join(artifact_dir, f"safety_results_{ts}.json")
            with open(artifact_path, "w", encoding="utf-8") as f:
                json.dump(
                    {
                        "timestamp_utc": ts,
                        "returncode": proc.returncode,
                        "stdout": stdout,
                        "stderr": stderr,
                        "parsed": data,
                        "significant_count": len(significant),
                        "total_count": len(vulns),
                    },
                    f,
                    indent=2,
                    ensure_ascii=False,
                )
        except Exception:
            # Artifact saving is best-effort; don't fail the test because of IO issues
            artifact_path = None
    else:
        artifact_path = None
    if significant:
        # Build a compact summary for the test failure
        lines = []
        for v in significant:
            name = (
                v.get("package_name") or v.get("name") or v.get("package") or "unknown"
            )
            ver = v.get("installed_version") or v.get("version") or ""
            advisory = v.get("advisory") or v.get("description") or v.get("cve") or ""
            sev = v.get("severity") or v.get("id") or ""
            lines.append(f"{name} {ver} {sev}: {advisory}")
        summary = "\n".join(lines[:50])
        # Include artifact path in failure message when available
        if artifact_path:
            pytest.fail(
                f"safety detected {len(significant)} vulnerable dependencies:\n{summary}\n\nDetailed results saved to: {artifact_path}"
            )
        pytest.fail(
            f"safety detected {len(significant)} vulnerable dependencies:\n{summary}"
        )
    # If only ignored vulns were found, consider the scan clean for CI/test purposes
