#! /usr/bin/env python

# Copyright (c) 2010-2026 Brian Haskin Jr.
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

import argparse
import sys
import unittest

# Try to import coverage, but make it optional
try:
    import coverage
    HAS_COVERAGE = True
except ImportError:
    HAS_COVERAGE = False


def main():
    # Parse command-line arguments
    parser = argparse.ArgumentParser(
        description='Run pyrimaa test suite with optional code coverage'
    )
    parser.add_argument(
        '--coverage',
        action='store_true',
        help='Enable code coverage reporting (terminal output)'
    )
    parser.add_argument(
        '--coverage-html',
        action='store_true',
        help='Generate HTML coverage report (implies --coverage)'
    )
    parser.add_argument(
        '--coverage-xml',
        action='store_true',
        help='Generate XML coverage report for CI/CD (implies --coverage)'
    )
    parser.add_argument(
        '-v', '--verbosity',
        type=int,
        default=2,
        choices=[0, 1, 2],
        help='Test output verbosity: 0=quiet, 1=normal, 2=verbose (default: 2)'
    )
    args = parser.parse_args()

    # Determine if coverage is requested
    coverage_requested = args.coverage or args.coverage_html or args.coverage_xml

    # Check if coverage is available when requested
    if coverage_requested and not HAS_COVERAGE:
        print("ERROR: coverage.py not installed.", file=sys.stderr)
        print("Install with: uv pip install coverage", file=sys.stderr)
        print(
            "Or install dev dependencies: uv pip install -e \".[dev]\"",
            file=sys.stderr,
        )
        sys.exit(1)

    # Initialize coverage if requested
    cov = None
    if coverage_requested:
        cov = coverage.Coverage()
        cov.start()

    # Run tests
    loader = unittest.TestLoader()
    suite = loader.discover("pyrimaa.tests")
    runner = unittest.TextTestRunner(verbosity=args.verbosity)
    result = runner.run(suite)

    # Stop coverage and generate reports
    if cov is not None:
        cov.stop()
        cov.save()

        # Always show terminal report if coverage was enabled
        print("\n" + "="*70)
        print("Coverage Report")
        print("="*70)
        cov.report()

        # Generate HTML report if requested
        if args.coverage_html:
            print("\nGenerating HTML coverage report...")
            cov.html_report()
            print("HTML report generated in htmlcov/index.html")

        # Generate XML report if requested
        if args.coverage_xml:
            print("\nGenerating XML coverage report...")
            cov.xml_report()
            print("XML report generated in coverage.xml")

    # Exit with appropriate code (0 = success, 1 = test failures)
    sys.exit(0 if result.wasSuccessful() else 1)


if __name__ == "__main__":
    main()
