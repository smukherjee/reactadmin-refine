#!/usr/bin/env python3
"""
Advanced Security Testing Runner
Enhanced security testing with advanced tools integration
"""

import sys
import os
import json
from pathlib import Path
from datetime import datetime

# Add paths for imports
sys.path.insert(0, os.path.dirname(__file__))

def check_advanced_dependencies():
    """Check which advanced security tools are available"""
    tools_status = {
        "bandit": {"available": False, "description": "Static security analysis"},
        "safety": {"available": False, "description": "Dependency vulnerability scanning"},
        "cryptography": {"available": False, "description": "Cryptographic testing"},
        "jwt": {"available": False, "description": "JWT token analysis"},
        "beautifulsoup4": {"available": False, "description": "HTML parsing for XSS detection"}
    }
    
    # Check each tool
    for tool in tools_status.keys():
        try:
            if tool == "jwt":
                import jwt
                tools_status[tool]["available"] = True
                tools_status[tool]["version"] = jwt.__version__
            elif tool == "beautifulsoup4":
                import bs4
                tools_status[tool]["available"] = True
                tools_status[tool]["version"] = bs4.__version__
            elif tool == "cryptography":
                import cryptography
                tools_status[tool]["available"] = True
                tools_status[tool]["version"] = cryptography.__version__
            else:
                __import__(tool)
                tools_status[tool]["available"] = True
                if hasattr(sys.modules[tool], '__version__'):
                    tools_status[tool]["version"] = sys.modules[tool].__version__
        except ImportError:
            pass
    
    return tools_status

def install_missing_tools():
    """Install missing advanced security tools"""
    print("Installing advanced security testing tools...")
    
    try:
        import subprocess
        result = subprocess.run([
            sys.executable, "-m", "pip", "install", "-r", "../requirements.txt"
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✓ Advanced security tools installed successfully")
            return True
        else:
            print(f"✗ Installation failed: {result.stderr}")
            return False
    except Exception as e:
        print(f"✗ Installation error: {str(e)}")
        return False

def run_basic_owasp_tests():
    """Run basic OWASP security tests"""
    try:
        from OWASPCheck import OWASPSecurityTester
        
        print("Running basic OWASP security tests...")
        tester = OWASPSecurityTester()
        report_file = tester.generate_report(f"owasp_basic_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        print(f"✓ Basic OWASP report generated: {report_file}")
        return report_file
    except Exception as e:
        print(f"✗ Basic OWASP tests failed: {str(e)}")
        return None

def run_advanced_security_tests():
    """Run advanced security tests with enhanced tools"""
    try:
        # Import the advanced tester
        from AdvancedSecurityTester import AdvancedSecurityTester
        
        print("Running advanced security tests...")
        tester = AdvancedSecurityTester()
        
        # Check available tools
        tools_status = tester.check_advanced_dependencies()
        available_count = sum(1 for tool in tools_status.values() if tool)
        
        print(f"Available advanced tools: {available_count}/{len(tools_status)}")
        
        # Generate advanced report
        report_file = tester.generate_advanced_report(f"advanced_security_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        print(f"✓ Advanced security report generated: {report_file}")
        return report_file
        
    except ImportError as e:
        print(f"⚠️  Advanced testing module not available: {str(e)}")
        return None
    except Exception as e:
        print(f"✗ Advanced security tests failed: {str(e)}")
        return None

def run_comprehensive_security_assessment():
    """Run comprehensive security assessment with both basic and advanced tests"""
    print("=" * 80)
    print("COMPREHENSIVE SECURITY ASSESSMENT - SPENDPLATFORM V2")
    print("=" * 80)
    print()
    
    # Check dependencies
    print("1. Checking available security tools...")
    tools_status = check_advanced_dependencies()
    
    available_tools = []
    missing_tools = []
    
    for tool, info in tools_status.items():
        if info["available"]:
            version = info.get("version", "unknown")
            print(f"   ✓ {tool} ({info['description']}) - v{version}")
            available_tools.append(tool)
        else:
            print(f"   ✗ {tool} ({info['description']}) - Not installed")
            missing_tools.append(tool)
    
    print()
    
    # Show installation advice for missing tools
    if missing_tools:
        print("Missing tools can be installed by enabling them in requirements.txt")
        print("Currently enabled: bandit, safety, cryptography, pyjwt, beautifulsoup4")
        print()
    
    # Run basic OWASP tests
    print("2. Running basic OWASP security tests...")
    basic_report = run_basic_owasp_tests()
    print()
    
    # Run advanced tests if tools are available
    advanced_report = None
    if len(available_tools) >= 2:  # At least 2 advanced tools available
        print("3. Running advanced security tests...")
        advanced_report = run_advanced_security_tests()
        print()
    else:
        print("3. Skipping advanced tests (insufficient tools available)")
        print("   Install advanced tools by enabling them in requirements.txt")
        print()
    
    # Generate combined summary
    print("4. Generating combined security assessment...")
    
    combined_summary = {
        "assessment_timestamp": datetime.now().isoformat(),
        "tools_available": available_tools,
        "tools_missing": missing_tools,
        "basic_report": basic_report,
        "advanced_report": advanced_report,
        "recommendations": []
    }
    
    # Add recommendations based on available tools
    if "bandit" in available_tools:
        combined_summary["recommendations"].append("✓ Static code analysis available - Review Bandit findings")
    else:
        combined_summary["recommendations"].append("⚠️  Install Bandit for static code analysis")
    
    if "safety" in available_tools:
        combined_summary["recommendations"].append("✓ Dependency scanning available - Check for vulnerable packages")
    else:
        combined_summary["recommendations"].append("⚠️  Install Safety for dependency vulnerability scanning")
    
    if "cryptography" in available_tools:
        combined_summary["recommendations"].append("✓ Cryptographic analysis available - Review crypto implementation")
    else:
        combined_summary["recommendations"].append("⚠️  Install cryptography library for crypto analysis")
    
    # Save combined summary
    summary_file = f"comprehensive_security_assessment_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(summary_file, 'w') as f:
        json.dump(combined_summary, f, indent=2)
    
    print(f"✓ Combined assessment saved: {summary_file}")
    print()
    
    # Display summary
    print("=" * 80)
    print("SECURITY ASSESSMENT SUMMARY")
    print("=" * 80)
    print(f"Available Tools: {len(available_tools)}/{len(tools_status)}")
    print(f"Basic OWASP Tests: {'✓ Completed' if basic_report else '✗ Failed'}")
    print(f"Advanced Tests: {'✓ Completed' if advanced_report else '✗ Skipped/Failed'}")
    print()
    
    print("RECOMMENDATIONS:")
    for rec in combined_summary["recommendations"]:
        print(f"  {rec}")
    print()
    
    print("GENERATED REPORTS:")
    if basic_report:
        print(f"  📄 Basic OWASP Report: {basic_report}")
        print(f"  🌐 Basic HTML Report: {basic_report.replace('.json', '.html')}")
    if advanced_report:
        print(f"  📊 Advanced Report: {advanced_report}")
        print(f"  📈 Advanced HTML Report: {advanced_report.replace('.json', '.html')}")
    print(f"  📋 Combined Summary: {summary_file}")
    print()
    
    return True

def main():
    """Main entry point for advanced security testing"""
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command == "check":
            print("Checking advanced security tools...")
            tools_status = check_advanced_dependencies()
            for tool, info in tools_status.items():
                status = "✓ Available" if info["available"] else "✗ Missing"
                version = f" (v{info.get('version', 'unknown')})" if info["available"] else ""
                print(f"{tool}: {status}{version} - {info['description']}")
            return
        
        elif command == "install":
            install_missing_tools()
            return
            
        elif command == "basic":
            run_basic_owasp_tests()
            return
            
        elif command == "advanced":
            run_advanced_security_tests()
            return
    
    # Default: run comprehensive assessment
    run_comprehensive_security_assessment()

if __name__ == "__main__":
    main()