#!/usr/bin/env python3
"""
Security Testing Runner
Executes OWASP security tests and integrates with the reporting system
"""

import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

# Add the backend src path to Python path for imports
backend_path = Path(__file__).parent.parent / "backend" / "src"
sys.path.insert(0, str(backend_path))

try:
    # Prefer tools/owasp/ copy first when running as a developer tool
    repo_root = Path(__file__).resolve().parents[2]
    tools_owasp = repo_root / "tools" / "owasp"
    sys.path.insert(0, str(tools_owasp))
    from OWASPCheck import OWASPSecurityTester

    from backend.app.core.config import settings
except Exception:
    # Fall back to local tests directory
    sys.path.insert(0, os.path.dirname(__file__))
    from OWASPCheck import OWASPSecurityTester

    from backend.app.core.config import settings


def check_dependencies():
    """Check if required dependencies are installed"""
    try:
        import requests

        print("✓ Required dependencies are available")
        return True
    except ImportError:
        print("✗ Missing required dependencies")
        print("Please install dependencies with: pip install -r ../requirements.txt")
        print(
            "(Security testing dependencies are now integrated in main requirements.txt)"
        )
        return False


def check_application_status():
    """Check if the application is running"""
    import requests

    try:
        # Check backend
        response = requests.get(f"{settings.TEST_BASE_URL}/", timeout=5)
        backend_running = response.status_code in [
            200,
            404,
        ]  # 404 is OK if no root endpoint

        # Check frontend (optional)
        try:
            frontend_response = requests.get(
                f"{settings.FRONTEND_BASE_URL}/", timeout=5
            )
            frontend_running = frontend_response.status_code == 200
        except Exception:
            frontend_running = False

        return backend_running, frontend_running

    except requests.exceptions.RequestException:
        return False, False


def run_security_tests():
    """Run the comprehensive security tests"""
    print("=" * 70)
    print("OWASP SECURITY ASSESSMENT - SPENDPLATFORM V2")
    print("=" * 70)
    print()

    # Check dependencies
    print("1. Checking dependencies...")
    if not check_dependencies():
        return False
    print()

    # Check application status
    print("2. Checking application status...")
    backend_running, frontend_running = check_application_status()

    if not backend_running:
        print(f"✗ Backend application is not running on {settings.TEST_BASE_URL}")
        print("  Please start the backend server first:")
        # Attempt to extract port for user guidance; fall back to 8000
        try:
            port = settings.TEST_BASE_URL.split(":")[-1]
        except Exception:
            port = "8000"
        print(
            f"  cd backend/src && python -m uvicorn main:app --reload --host 0.0.0.0 --port {port}"
        )
        return False
    else:
        print(f"✓ Backend application is running at {settings.TEST_BASE_URL}")

    if not frontend_running:
        print(f"⚠ Frontend application is not running on {settings.FRONTEND_BASE_URL}")
        print("  This is optional but recommended for comprehensive testing")
    else:
        print(f"✓ Frontend application is running at {settings.FRONTEND_BASE_URL}")
    print()

    # Initialize and run security tests
    print("3. Initializing OWASP Security Tester...")
    tester = OWASPSecurityTester(
        base_url=settings.TEST_BASE_URL,
        frontend_url=(
            settings.FRONTEND_BASE_URL
            if frontend_running
            else settings.FRONTEND_BASE_URL
        ),
    )
    print()

    print("4. Running comprehensive security assessment...")
    print("   This may take several minutes...")
    print()

    try:
        # Generate the security report
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = f"owasp_security_report_{timestamp}.json"

        json_report = tester.generate_report(report_file)

        # Load the report for summary
        with open(json_report, "r") as f:
            report_data = json.load(f)

        # Display summary
        print("=" * 70)
        print("SECURITY ASSESSMENT SUMMARY")
        print("=" * 70)
        print(f"Test Duration: {report_data['duration_seconds']:.2f} seconds")
        print(f"Total Issues Found: {report_data['total_issues']}")
        print()
        print("Severity Breakdown:")
        print(f"  🔴 Critical: {report_data['severity_breakdown']['CRITICAL']}")
        print(f"  🟠 High:     {report_data['severity_breakdown']['HIGH']}")
        print(f"  🟡 Medium:   {report_data['severity_breakdown']['MEDIUM']}")
        print(f"  🟢 Low:      {report_data['severity_breakdown']['LOW']}")
        print(f"  ℹ️  Info:     {report_data['severity_breakdown']['INFO']}")
        print()

        # Show critical and high issues
        critical_high_issues = [
            issue
            for issue in report_data["issues"]
            if issue["severity"] in ["CRITICAL", "HIGH"]
        ]

        if critical_high_issues:
            print("CRITICAL & HIGH SEVERITY ISSUES:")
            print("-" * 50)
            for issue in critical_high_issues:
                print(f"🚨 {issue['severity']}: {issue['title']}")
                print(f"   Category: {issue['category']}")
                print(f"   Description: {issue['description']}")
                print()

        print("=" * 70)
        print("REPORTS GENERATED:")
        print("=" * 70)
        base_name = report_file.replace(".json", "")
        print(f"📄 JSON Report: securitytesting/{report_file}")
        print(f"🌐 HTML Report: securitytesting/{base_name}.html")
        print(f"📝 Log File: securitytesting/security_test.log")
        print()

        # Integration with main reporting system
        integrate_with_main_reports(report_data, timestamp)

        return True

    except Exception as e:
        print(f"❌ Error during security testing: {str(e)}")
        import traceback

        traceback.print_exc()
        return False


def integrate_with_main_reports(security_data, timestamp):
    """Integrate security report with main application reporting system"""
    print("5. Integrating with main reporting system...")

    try:
        # Create a summary for the main reports endpoint
        security_summary = {
            "report_type": "security_assessment",
            "timestamp": timestamp,
            "total_issues": security_data["total_issues"],
            "critical_issues": security_data["severity_breakdown"]["CRITICAL"],
            "high_issues": security_data["severity_breakdown"]["HIGH"],
            "test_duration": security_data["duration_seconds"],
            "owasp_categories_tested": [
                "A01:2021 – Broken Access Control",
                "A02:2021 – Cryptographic Failures",
                "A03:2021 – Injection",
                "A04:2021 – Insecure Design",
                "A05:2021 – Security Misconfiguration",
                "A06:2021 – Vulnerable Components",
                "A07:2021 – Authentication Failures",
                "A08:2021 – Software/Data Integrity",
                "A09:2021 – Logging/Monitoring Failures",
                "A10:2021 – Server-Side Request Forgery",
            ],
        }

        # Save integration summary
        integration_file = f"/Users/sujoymukherjee/code/spendplatform-v2/securitytesting/security_summary_{timestamp}.json"
        with open(integration_file, "w") as f:
            json.dump(security_summary, f, indent=2)

        print(f"✓ Security summary saved: {integration_file}")

        # Note about integration with backend reporting
        print()
        print("📊 INTEGRATION NOTES:")
        print("   - Security report data is now available for integration")
        print(
            "   - Consider adding a new endpoint in backend/src/routers/reporting.py:"
        )
        print("   - GET /reports/security-assessment")
        print("   - This would expose security metrics via the main API")

    except Exception as e:
        print(f"⚠️  Warning: Could not integrate with main reporting system: {str(e)}")


if __name__ == "__main__":
    print("Starting OWASP Security Assessment...")
    print()

    success = run_security_tests()

    if success:
        print("🎉 Security assessment completed successfully!")
        print()
        print("NEXT STEPS:")
        print("1. Review the HTML report for detailed findings")
        print("2. Address critical and high severity issues first")
        print("3. Consider implementing automated security testing in CI/CD")
        print("4. Schedule regular security assessments")
        sys.exit(0)
    else:
        print("❌ Security assessment failed!")
        print("Please check the error messages above and try again.")
        sys.exit(1)
