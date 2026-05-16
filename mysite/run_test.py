#!/usr/bin/env python
"""
Simple test runner for Easy Transport Selenium tests.
Usage: python run_tests.py
"""
import subprocess
import sys

def run_tests():
    print("🚀 Running Easy Transport Selenium Tests...")
    print("="*60)
    
    # Run pytest with verbose output
    result = subprocess.run([
        sys.executable, "-m", "pytest", 
        "tests/", 
        "-v", 
        "--html=reports/full_test_report.html",
        "--self-contained-html",
        "-s",  # Show print statements
        "--tb=short"
    ], cwd="selenium_tests")
    
    print("="*60)
    if result.returncode == 0:
        print("✅ All tests passed! Report: reports/full_test_report.html")
    else:
        print("❌ Some tests failed. Check report for details.")
    
    return result.returncode

if __name__ == "__main__":
    sys.exit(run_tests())