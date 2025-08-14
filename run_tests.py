#!/usr/bin/env python3
"""
VespAI Test Runner

Simple test runner for VespAI that runs all test modules explicitly.
"""

import subprocess
import sys
import os
import glob

def run_tests():
    """Find and run all test files in the tests directory."""
    # Add project root to Python path
    project_root = os.path.dirname(os.path.abspath(__file__))
    
    # Find all test files
    test_files = []
    tests_dir = os.path.join(project_root, 'tests')
    for root, dirs, files in os.walk(tests_dir):
        for file in files:
            if file.startswith('test_') and file.endswith('.py'):
                test_files.append(os.path.join(root, file))
    
    if not test_files:
        print("No test files found!")
        return 1
    
    print(f"Found {len(test_files)} test file(s)")
    
    all_passed = True
    for test_file in test_files:
        print(f"\n{'='*60}")
        print(f"Running tests in: {os.path.relpath(test_file)}")
        print(f"{'='*60}")
        
        try:
            result = subprocess.run([sys.executable, test_file], 
                                  capture_output=False, 
                                  check=True)
        except subprocess.CalledProcessError:
            all_passed = False
            print(f"Tests FAILED in {os.path.relpath(test_file)}")
    
    if all_passed:
        print(f"\n{'='*60}")
        print("ALL TESTS PASSED!")
        print(f"{'='*60}")
        return 0
    else:
        print(f"\n{'='*60}")
        print("SOME TESTS FAILED!")
        print(f"{'='*60}")
        return 1

if __name__ == '__main__':
    exit_code = run_tests()
    sys.exit(exit_code)