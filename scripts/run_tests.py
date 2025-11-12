#!/usr/bin/env python3
"""
Comprehensive Test Runner for ExamsTutor AI API
Epic 3.2: Testing & Quality Assurance

Usage:
    python scripts/run_tests.py --all
    python scripts/run_tests.py --unit
    python scripts/run_tests.py --integration
    python scripts/run_tests.py --performance
    python scripts/run_tests.py --security
    python scripts/run_tests.py --coverage
"""
import sys
import argparse
import subprocess
from pathlib import Path
from datetime import datetime


def run_command(cmd, description):
    """Run a command and return success status"""
    print(f"\n{'='*70}")
    print(f"{description}")
    print(f"{'='*70}\n")

    try:
        result = subprocess.run(
            cmd,
            shell=True,
            check=True,
            capture_output=False
        )
        print(f"\n✅ {description}: PASSED\n")
        return True
    except subprocess.CalledProcessError as e:
        print(f"\n❌ {description}: FAILED\n")
        return False


def main():
    parser = argparse.ArgumentParser(description="Run ExamsTutor AI API tests")
    parser.add_argument("--all", action="store_true", help="Run all tests")
    parser.add_argument("--unit", action="store_true", help="Run unit tests only")
    parser.add_argument("--integration", action="store_true", help="Run integration tests")
    parser.add_argument("--performance", action="store_true", help="Run performance tests")
    parser.add_argument("--security", action="store_true", help="Run security tests")
    parser.add_argument("--coverage", action="store_true", help="Generate coverage report")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--fast", action="store_true", help="Skip slow tests")

    args = parser.parse_args()

    # If no specific test type selected, show help
    if not any([args.all, args.unit, args.integration, args.performance, args.security, args.coverage]):
        parser.print_help()
        return

    start_time = datetime.now()
    results = []

    # Build pytest command
    pytest_args = []

    if args.verbose:
        pytest_args.append("-vv")

    if args.fast:
        pytest_args.append("-m 'not slow'")

    # Run tests based on arguments
    if args.all or args.unit:
        cmd = f"pytest tests/unit/ {' '.join(pytest_args)}"
        success = run_command(cmd, "UNIT TESTS")
        results.append(("Unit Tests", success))

    if args.all or args.integration:
        cmd = f"pytest tests/integration/ {' '.join(pytest_args)}"
        success = run_command(cmd, "INTEGRATION TESTS")
        results.append(("Integration Tests", success))

    if args.all or args.performance:
        cmd = f"pytest tests/performance/ -m performance {' '.join(pytest_args)}"
        success = run_command(cmd, "PERFORMANCE TESTS")
        results.append(("Performance Tests", success))

    if args.all or args.security:
        cmd = f"pytest tests/security/ -m security {' '.join(pytest_args)}"
        success = run_command(cmd, "SECURITY TESTS")
        results.append(("Security Tests", success))

    if args.all or args.coverage:
        cmd = "pytest --cov=src --cov-report=term-missing --cov-report=html --cov-fail-under=80"
        success = run_command(cmd, "COVERAGE REPORT")
        results.append(("Coverage Report", success))

        if success:
            print("\n📊 Coverage report generated: htmlcov/index.html\n")

    # Print summary
    elapsed_time = datetime.now() - start_time

    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70 + "\n")

    for test_type, success in results:
        status = "✅ PASSED" if success else "❌ FAILED"
        print(f"  {test_type:<25} {status}")

    total_tests = len(results)
    passed_tests = sum(1 for _, success in results if success)
    failed_tests = total_tests - passed_tests

    print(f"\n{'='*70}")
    print(f"Total: {total_tests} | Passed: {passed_tests} | Failed: {failed_tests}")
    print(f"Time: {elapsed_time.total_seconds():.2f}s")
    print(f"{'='*70}\n")

    # Exit with error if any tests failed
    sys.exit(0 if failed_tests == 0 else 1)


if __name__ == "__main__":
    main()
