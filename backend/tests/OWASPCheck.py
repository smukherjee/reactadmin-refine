#!/usr/bin/env python3
"""
OWASP Security Testing Module
Comprehensive security assessment tool for the SpendPlatform application
Based on OWASP Top 10 2021 security vulnerabilities
"""

import base64
import hashlib
import json
import logging
import re
import time
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urljoin, urlparse

import requests

from backend.app.core.config import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("security_test.log"), logging.StreamHandler()],
)
logger = logging.getLogger(__name__)


class Severity(Enum):
    """Security issue severity levels"""

    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INFO = "INFO"


@dataclass
class SecurityIssue:
    """Data class for security issues"""

    category: str
    title: str
    description: str
    severity: Severity
    evidence: str
    recommendation: str
    cwe_id: Optional[str] = None
    owasp_category: Optional[str] = None


class OWASPSecurityTester:
    """
    OWASP Security Testing class
    Tests for common security vulnerabilities based on OWASP Top 10
    """

    def __init__(
        self, base_url: Optional[str] = None, frontend_url: Optional[str] = None
    ):
        # Prefer explicit args, fall back to settings which read from .env or environment
        self.base_url = (base_url or settings.TEST_BASE_URL).rstrip("/")
        self.frontend_url = (frontend_url or settings.FRONTEND_BASE_URL).rstrip("/")
        self.session = requests.Session()
        self.session.timeout = 10
        self.issues: List[SecurityIssue] = []
        self.test_credentials = {
            "superadmin": {"username": "superadmin", "password": "admin123"},
            "client_admin": {"username": "client_admin", "password": "admin123"},
            "user": {"username": "testuser", "password": "user123"},
        }

    def authenticate(self, role: str = "superadmin") -> Optional[str]:
        """Authenticate and return access token"""
        try:
            creds = self.test_credentials.get(role)
            if not creds:
                logger.error(f"No credentials found for role: {role}")
                return None

            response = self.session.post(
                f"{self.base_url}/auth/login",
                data=creds,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )

            if response.status_code == 200:
                token_data = response.json()
                token = token_data.get("access_token")
                self.session.headers.update({"Authorization": f"Bearer {token}"})
                logger.info(f"Successfully authenticated as {role}")
                return token
            else:
                logger.error(
                    f"Authentication failed for {role}: {response.status_code}"
                )
                return None

        except Exception as e:
            logger.error(f"Authentication error: {str(e)}")
            return None

    def test_a01_broken_access_control(self) -> List[SecurityIssue]:
        """A01:2021 – Broken Access Control"""
        issues = []
        logger.info("Testing A01: Broken Access Control")

        # Test 1: Vertical privilege escalation
        regular_user_token = self.authenticate("user")
        if regular_user_token:
            admin_endpoints = [
                "/clients",
                "/roles",
                "/screen-permissions/screens",
                "/users",
            ]

            for endpoint in admin_endpoints:
                try:
                    response = self.session.get(f"{self.base_url}{endpoint}")
                    if response.status_code == 200:
                        issues.append(
                            SecurityIssue(
                                category="Broken Access Control",
                                title=f"Vertical Privilege Escalation on {endpoint}",
                                description=f"Regular user can access admin endpoint {endpoint}",
                                severity=Severity.HIGH,
                                evidence=f"HTTP {response.status_code} response for {endpoint}",
                                recommendation="Implement proper role-based access control",
                                cwe_id="CWE-269",
                                owasp_category="A01:2021",
                            )
                        )
                except Exception as e:
                    logger.debug(f"Access control test error for {endpoint}: {e}")

        # Test 2: Horizontal privilege escalation
        try:
            # Try to access another client's data
            response = self.session.get(f"{self.base_url}/invoices?client_id=999")
            if response.status_code == 200 and response.json():
                issues.append(
                    SecurityIssue(
                        category="Broken Access Control",
                        title="Horizontal Privilege Escalation",
                        description="Can access other client's data by manipulating client_id",
                        severity=Severity.CRITICAL,
                        evidence=f"Accessed client_id=999 data: {len(response.json())} records",
                        recommendation="Validate client_id against authenticated user's permissions",
                        cwe_id="CWE-639",
                        owasp_category="A01:2021",
                    )
                )
        except Exception as e:
            logger.debug(f"Horizontal privilege escalation test error: {e}")

        return issues

    def test_a02_cryptographic_failures(self) -> List[SecurityIssue]:
        """A02:2021 – Cryptographic Failures"""
        issues = []
        logger.info("Testing A02: Cryptographic Failures")

        # Test 1: Weak password hashing
        try:
            # Check if passwords are properly hashed
            response = self.session.get(f"{self.base_url}/users")
            if response.status_code == 200:
                users = response.json()
                for user in users:
                    if "password" in user and user["password"]:
                        # Check if password looks like plaintext or weak hash
                        password = str(user["password"])
                        if len(password) < 50:  # Proper hashes should be longer
                            issues.append(
                                SecurityIssue(
                                    category="Cryptographic Failures",
                                    title="Weak Password Storage",
                                    description="Password appears to be stored with weak hashing",
                                    severity=Severity.HIGH,
                                    evidence=f"Password length: {len(password)} characters",
                                    recommendation="Use bcrypt, scrypt, or Argon2 for password hashing",
                                    cwe_id="CWE-916",
                                    owasp_category="A02:2021",
                                )
                            )
        except Exception as e:
            logger.debug(f"Password hashing test error: {e}")

        # Test 2: HTTP instead of HTTPS
        if self.base_url.startswith("http://"):
            issues.append(
                SecurityIssue(
                    category="Cryptographic Failures",
                    title="Unencrypted HTTP Communication",
                    description="Application uses HTTP instead of HTTPS",
                    severity=Severity.MEDIUM,
                    evidence=f"Base URL: {self.base_url}",
                    recommendation="Implement HTTPS with proper TLS configuration",
                    cwe_id="CWE-319",
                    owasp_category="A02:2021",
                )
            )

        return issues

    def test_a03_injection(self) -> List[SecurityIssue]:
        """A03:2021 – Injection"""
        issues = []
        logger.info("Testing A03: Injection Attacks")

        # SQL Injection test payloads
        sql_payloads = [
            "'; DROP TABLE users; --",
            "' OR '1'='1",
            "' UNION SELECT * FROM users --",
            "admin'--",
            "' OR 1=1#",
        ]

        # Test SQL injection on login
        for payload in sql_payloads:
            try:
                response = self.session.post(
                    f"{self.base_url}/auth/login",
                    data={"username": payload, "password": "test"},
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                )

                # Check for SQL error messages or unexpected success
                if any(
                    error in response.text.lower()
                    for error in [
                        "sql",
                        "mysql",
                        "postgresql",
                        "sqlite",
                        "oracle",
                        "syntax error",
                        "database",
                    ]
                ):
                    issues.append(
                        SecurityIssue(
                            category="Injection",
                            title="SQL Injection Vulnerability",
                            description="SQL injection detected in login endpoint",
                            severity=Severity.CRITICAL,
                            evidence=f"Payload: {payload}, Response contains SQL errors",
                            recommendation="Use parameterized queries and input validation",
                            cwe_id="CWE-89",
                            owasp_category="A03:2021",
                        )
                    )
                    break

            except Exception as e:
                logger.debug(f"SQL injection test error: {e}")

        # Test NoSQL injection if applicable
        nosql_payloads = ['{"$ne": null}', '{"$gt": ""}', '{"$regex": ".*"}']

        return issues

    def test_a04_insecure_design(self) -> List[SecurityIssue]:
        """A04:2021 – Insecure Design"""
        issues = []
        logger.info("Testing A04: Insecure Design")

        # Test for missing rate limiting
        try:
            start_time = time.time()
            request_count = 0

            # Send rapid requests to test rate limiting
            for i in range(20):
                response = self.session.post(
                    f"{self.base_url}/auth/login",
                    data={"username": "invalid", "password": "invalid"},
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                )
                request_count += 1

                if response.status_code == 429:  # Rate limited
                    break

            elapsed_time = time.time() - start_time

            if request_count >= 20 and elapsed_time < 10:
                issues.append(
                    SecurityIssue(
                        category="Insecure Design",
                        title="Missing Rate Limiting",
                        description="No rate limiting detected on authentication endpoint",
                        severity=Severity.MEDIUM,
                        evidence=f"Sent {request_count} requests in {elapsed_time:.2f} seconds",
                        recommendation="Implement rate limiting to prevent brute force attacks",
                        cwe_id="CWE-307",
                        owasp_category="A04:2021",
                    )
                )

        except Exception as e:
            logger.debug(f"Rate limiting test error: {e}")

        return issues

    def test_a05_security_misconfiguration(self) -> List[SecurityIssue]:
        """A05:2021 – Security Misconfiguration"""
        issues = []
        logger.info("Testing A05: Security Misconfiguration")

        # Test for verbose error messages
        try:
            response = self.session.get(f"{self.base_url}/nonexistent-endpoint")
            if response.status_code == 500:
                if any(
                    info in response.text.lower()
                    for info in [
                        "traceback",
                        "stack trace",
                        "exception",
                        "error details",
                    ]
                ):
                    issues.append(
                        SecurityIssue(
                            category="Security Misconfiguration",
                            title="Verbose Error Messages",
                            description="Application exposes detailed error information",
                            severity=Severity.LOW,
                            evidence="500 error contains stack trace or detailed error info",
                            recommendation="Configure proper error handling to hide implementation details",
                            cwe_id="CWE-209",
                            owasp_category="A05:2021",
                        )
                    )
        except Exception as e:
            logger.debug(f"Error message test error: {e}")

        # Test for default credentials
        default_creds = [
            {"username": "admin", "password": "admin"},
            {"username": "admin", "password": "password"},
            {"username": "root", "password": "root"},
            {"username": "admin", "password": "123456"},
        ]

        for creds in default_creds:
            try:
                response = self.session.post(
                    f"{self.base_url}/auth/login",
                    data=creds,
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                )

                if response.status_code == 200:
                    issues.append(
                        SecurityIssue(
                            category="Security Misconfiguration",
                            title="Default Credentials",
                            description=f"Default credentials work: {creds['username']}/{creds['password']}",
                            severity=Severity.HIGH,
                            evidence=f"Successful login with {creds['username']}/{creds['password']}",
                            recommendation="Change default credentials and enforce strong password policy",
                            cwe_id="CWE-1188",
                            owasp_category="A05:2021",
                        )
                    )

            except Exception as e:
                logger.debug(f"Default credentials test error: {e}")

        return issues

    def test_a06_vulnerable_components(self) -> List[SecurityIssue]:
        """A06:2021 – Vulnerable and Outdated Components"""
        issues = []
        logger.info("Testing A06: Vulnerable and Outdated Components")

        # Check server headers for version information
        try:
            response = self.session.get(f"{self.base_url}/")
            headers = response.headers

            # Check for server version disclosure
            if "Server" in headers:
                server_header = headers["Server"]
                if any(
                    version_pattern in server_header.lower()
                    for version_pattern in [
                        "apache/",
                        "nginx/",
                        "microsoft-iis/",
                        "uvicorn/",
                    ]
                ):
                    issues.append(
                        SecurityIssue(
                            category="Vulnerable Components",
                            title="Server Version Disclosure",
                            description="Server version information exposed in headers",
                            severity=Severity.LOW,
                            evidence=f"Server header: {server_header}",
                            recommendation="Configure server to hide version information",
                            cwe_id="CWE-200",
                            owasp_category="A06:2021",
                        )
                    )

            # Check for X-Powered-By header
            if "X-Powered-By" in headers:
                issues.append(
                    SecurityIssue(
                        category="Vulnerable Components",
                        title="Technology Stack Disclosure",
                        description="X-Powered-By header reveals technology stack",
                        severity=Severity.LOW,
                        evidence=f"X-Powered-By: {headers['X-Powered-By']}",
                        recommendation="Remove or configure X-Powered-By header",
                        cwe_id="CWE-200",
                        owasp_category="A06:2021",
                    )
                )

        except Exception as e:
            logger.debug(f"Component version test error: {e}")

        return issues

    def test_a07_identification_auth_failures(self) -> List[SecurityIssue]:
        """A07:2021 – Identification and Authentication Failures"""
        issues = []
        logger.info("Testing A07: Identification and Authentication Failures")

        # Test weak password policy
        weak_passwords = ["123", "password", "admin", "test"]

        # Test session management
        try:
            # Login and get token
            token = self.authenticate("superadmin")
            if token:
                # Test if session expires properly
                time.sleep(2)  # Wait briefly

                # Make request with token
                response = self.session.get(f"{self.base_url}/users")
                if response.status_code == 200:
                    # Token should ideally have expiry time validation
                    # This is a basic check - more sophisticated tests would be needed
                    logger.info(
                        "Token validation passed - further session security tests needed"
                    )

        except Exception as e:
            logger.debug(f"Session management test error: {e}")

        # Test for account enumeration
        try:
            # Test with valid username
            response1 = self.session.post(
                f"{self.base_url}/auth/login",
                data={"username": "superadmin", "password": "wrongpassword"},
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )

            # Test with invalid username
            response2 = self.session.post(
                f"{self.base_url}/auth/login",
                data={"username": "nonexistentuser", "password": "wrongpassword"},
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )

            # Compare response times and messages
            if abs(len(response1.text) - len(response2.text)) > 50:
                issues.append(
                    SecurityIssue(
                        category="Authentication Failures",
                        title="Username Enumeration",
                        description="Different responses for valid/invalid usernames",
                        severity=Severity.MEDIUM,
                        evidence=f"Response length difference: {abs(len(response1.text) - len(response2.text))}",
                        recommendation="Provide consistent error messages for authentication failures",
                        cwe_id="CWE-204",
                        owasp_category="A07:2021",
                    )
                )

        except Exception as e:
            logger.debug(f"Username enumeration test error: {e}")

        return issues

    def test_a08_software_data_integrity(self) -> List[SecurityIssue]:
        """A08:2021 – Software and Data Integrity Failures"""
        issues = []
        logger.info("Testing A08: Software and Data Integrity Failures")

        # Test for missing integrity checks
        try:
            # Check if there are any file upload endpoints
            response = self.session.post(
                f"{self.base_url}/upload", files={"file": ("test.txt", "test content")}
            )
            # This is a placeholder - actual file upload testing would be more complex

        except Exception as e:
            logger.debug(f"File integrity test error: {e}")

        return issues

    def test_a09_security_logging_monitoring(self) -> List[SecurityIssue]:
        """A09:2021 – Security Logging and Monitoring Failures"""
        issues = []
        logger.info("Testing A09: Security Logging and Monitoring Failures")

        # This would typically require access to log files
        # For now, we'll check if failed authentication attempts are logged
        try:
            # Make failed login attempt
            response = self.session.post(
                f"{self.base_url}/auth/login",
                data={"username": "attacker", "password": "malicious"},
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )

            # Check if proper logging headers are present
            if "X-Request-ID" not in response.headers:
                issues.append(
                    SecurityIssue(
                        category="Logging and Monitoring",
                        title="Missing Request Tracking",
                        description="No request ID for tracking security events",
                        severity=Severity.LOW,
                        evidence="Missing X-Request-ID header",
                        recommendation="Implement request tracking and comprehensive security logging",
                        cwe_id="CWE-778",
                        owasp_category="A09:2021",
                    )
                )

        except Exception as e:
            logger.debug(f"Logging test error: {e}")

        return issues

    def test_a10_server_side_request_forgery(self) -> List[SecurityIssue]:
        """A10:2021 – Server-Side Request Forgery (SSRF)"""
        issues = []
        logger.info("Testing A10: Server-Side Request Forgery")

        # Test for SSRF in any URL parameter endpoints
        ssrf_payloads = [
            "http://localhost:8080/admin",
            "http://127.0.0.1:22",
            "file:///etc/passwd",
            "http://metadata.google.internal/",
        ]

        # This would need specific endpoints that accept URLs
        # Placeholder for SSRF testing logic

        return issues

    def run_comprehensive_security_test(self) -> Dict[str, Any]:
        """Run all OWASP security tests"""
        logger.info("Starting comprehensive OWASP security assessment")
        start_time = datetime.now()

        # Clear previous issues
        self.issues = []

        # Run all OWASP Top 10 tests
        test_methods = [
            self.test_a01_broken_access_control,
            self.test_a02_cryptographic_failures,
            self.test_a03_injection,
            self.test_a04_insecure_design,
            self.test_a05_security_misconfiguration,
            self.test_a06_vulnerable_components,
            self.test_a07_identification_auth_failures,
            self.test_a08_software_data_integrity,
            self.test_a09_security_logging_monitoring,
            self.test_a10_server_side_request_forgery,
        ]

        for test_method in test_methods:
            try:
                issues = test_method()
                self.issues.extend(issues)
            except Exception as e:
                logger.error(f"Error in {test_method.__name__}: {str(e)}")

        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        # Generate summary
        severity_counts = {
            Severity.CRITICAL.value: 0,
            Severity.HIGH.value: 0,
            Severity.MEDIUM.value: 0,
            Severity.LOW.value: 0,
            Severity.INFO.value: 0,
        }

        for issue in self.issues:
            severity_counts[issue.severity.value] += 1

        summary = {
            "test_start_time": start_time.isoformat(),
            "test_end_time": end_time.isoformat(),
            "duration_seconds": duration,
            "total_issues": len(self.issues),
            "severity_breakdown": severity_counts,
            "issues": [
                {
                    "category": issue.category,
                    "title": issue.title,
                    "description": issue.description,
                    "severity": issue.severity.value,
                    "evidence": issue.evidence,
                    "recommendation": issue.recommendation,
                    "cwe_id": issue.cwe_id,
                    "owasp_category": issue.owasp_category,
                }
                for issue in self.issues
            ],
        }

        logger.info(f"Security assessment completed in {duration:.2f} seconds")
        logger.info(f"Found {len(self.issues)} security issues")

        return summary

    def generate_report(self, output_file: str = "security_report.json") -> str:
        """Generate detailed security report"""
        summary = self.run_comprehensive_security_test()
        # Save JSON report into repository-local security/reports for CI artifact collection
        from pathlib import Path

        tests_dir = Path(__file__).parent
        repo_root = tests_dir.parent  # backend
        reports_dir = repo_root / "security" / "reports"
        reports_dir.mkdir(parents=True, exist_ok=True)

        json_file = str(reports_dir / output_file)
        with open(json_file, "w") as f:
            json.dump(summary, f, indent=2)

        # Generate HTML report next to the JSON file
        html_file = json_file.replace(".json", ".html")
        self._generate_html_report(summary, html_file)

        logger.info(f"Security reports generated: {json_file}, {html_file}")
        return json_file

    def _generate_html_report(self, summary: Dict[str, Any], html_file: str):
        """Generate HTML security report"""
        html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>OWASP Security Assessment Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; background-color: #f5f5f5; }}
        .container {{ max-width: 1200px; margin: 0 auto; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
        .header {{ text-align: center; border-bottom: 2px solid #333; padding-bottom: 20px; margin-bottom: 30px; }}
        .summary {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin-bottom: 30px; }}
        .summary-card {{ background: #f8f9fa; padding: 20px; border-radius: 8px; text-align: center; border-left: 4px solid #007bff; }}
        .severity-critical {{ border-left-color: #dc3545; background-color: #f8d7da; }}
        .severity-high {{ border-left-color: #fd7e14; background-color: #fff3cd; }}
        .severity-medium {{ border-left-color: #ffc107; background-color: #fff3cd; }}
        .severity-low {{ border-left-color: #28a745; background-color: #d4edda; }}
        .issue {{ margin-bottom: 20px; padding: 20px; border-radius: 8px; border-left: 4px solid #ccc; }}
        .issue.critical {{ border-left-color: #dc3545; background-color: #f8d7da; }}
        .issue.high {{ border-left-color: #fd7e14; background-color: #fff3cd; }}
        .issue.medium {{ border-left-color: #ffc107; background-color: #fff3cd; }}
        .issue.low {{ border-left-color: #28a745; background-color: #d4edda; }}
        .issue-title {{ font-size: 18px; font-weight: bold; margin-bottom: 10px; }}
        .issue-meta {{ font-size: 12px; color: #666; margin-bottom: 10px; }}
        .issue-description {{ margin-bottom: 10px; }}
        .issue-evidence {{ background: #f1f1f1; padding: 10px; border-radius: 4px; font-family: monospace; margin-bottom: 10px; }}
        .issue-recommendation {{ background: #e7f3ff; padding: 10px; border-radius: 4px; }}
        .footer {{ margin-top: 40px; text-align: center; color: #666; font-size: 12px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>OWASP Security Assessment Report</h1>
            <p>SpendPlatform v2 Security Analysis</p>
            <p>Generated on: {summary['test_end_time']}</p>
            <p>Test Duration: {summary['duration_seconds']:.2f} seconds</p>
        </div>
        
        <div class="summary">
            <div class="summary-card">
                <h3>Total Issues</h3>
                <h2>{summary['total_issues']}</h2>
            </div>
            <div class="summary-card severity-critical">
                <h3>Critical</h3>
                <h2>{summary['severity_breakdown']['CRITICAL']}</h2>
            </div>
            <div class="summary-card severity-high">
                <h3>High</h3>
                <h2>{summary['severity_breakdown']['HIGH']}</h2>
            </div>
            <div class="summary-card severity-medium">
                <h3>Medium</h3>
                <h2>{summary['severity_breakdown']['MEDIUM']}</h2>
            </div>
            <div class="summary-card severity-low">
                <h3>Low</h3>
                <h2>{summary['severity_breakdown']['LOW']}</h2>
            </div>
        </div>
        
        <h2>Security Issues</h2>
"""

        for issue in summary["issues"]:
            severity_class = issue["severity"].lower()
            html_content += f"""
        <div class="issue {severity_class}">
            <div class="issue-title">{issue['title']}</div>
            <div class="issue-meta">
                <strong>Category:</strong> {issue['category']} | 
                <strong>Severity:</strong> {issue['severity']} | 
                <strong>OWASP:</strong> {issue.get('owasp_category', 'N/A')} |
                <strong>CWE:</strong> {issue.get('cwe_id', 'N/A')}
            </div>
            <div class="issue-description">{issue['description']}</div>
            <div class="issue-evidence"><strong>Evidence:</strong> {issue['evidence']}</div>
            <div class="issue-recommendation"><strong>Recommendation:</strong> {issue['recommendation']}</div>
        </div>
"""

        html_content += """
        <div class="footer">
            <p>This report was generated using automated OWASP security testing tools.</p>
            <p>Manual security testing and code review are recommended for comprehensive assessment.</p>
        </div>
    </div>
</body>
</html>
"""

        with open(html_file, "w") as f:
            f.write(html_content)


if __name__ == "__main__":
    # Initialize the security tester
    tester = OWASPSecurityTester()

    # Generate comprehensive security report
    report_file = tester.generate_report("owasp_security_report.json")

    print(f"Security assessment completed!")
    print(
        f"Reports generated in: /Users/sujoymukherjee/code/spendplatform-v2/securitytesting/"
    )
    print(f"- JSON Report: owasp_security_report.json")
    print(f"- HTML Report: owasp_security_report.html")
    print(f"- Log File: security_test.log")
