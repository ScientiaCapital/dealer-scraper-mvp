#!/usr/bin/env python3
"""
Automated test for prompt_user_confirmation function.
Tests input validation and return values.
"""

import sys
from io import StringIO
sys.path.insert(0, '.')
from scripts.run_22_oem_sequential import prompt_user_confirmation

def test_with_input(user_input, expected_output):
    """Test the prompt function with simulated user input."""
    # Simulate user input
    sys.stdin = StringIO(user_input)
    try:
        result = prompt_user_confirmation('Carrier', 0, 22)
        sys.stdin = sys.__stdin__  # Reset stdin
        return result == expected_output, result
    except Exception as e:
        sys.stdin = sys.__stdin__  # Reset stdin
        return False, str(e)

print("Testing prompt_user_confirmation function...")
print("=" * 60)

# Test cases
test_cases = [
    ("y\n", "y", "Accept with 'y'"),
    ("yes\n", "y", "Accept with 'yes'"),
    ("n\n", "n", "Reject with 'n'"),
    ("no\n", "n", "Reject with 'no'"),
    ("skip\n", "skip", "Skip with 'skip'"),
    ("s\n", "skip", "Skip with 's'"),
    ("invalid\ny\n", "y", "Invalid then valid input"),
    ("  yes  \n", "y", "Accept with whitespace"),
    ("YES\n", "y", "Accept with uppercase"),
]

passed = 0
failed = 0

for user_input, expected, description in test_cases:
    success, result = test_with_input(user_input, expected)
    status = "✓ PASS" if success else "✗ FAIL"
    print(f"{status}: {description}")
    if success:
        passed += 1
    else:
        failed += 1
        print(f"  Expected: {expected}, Got: {result}")

print("=" * 60)
print(f"Results: {passed} passed, {failed} failed")

if failed == 0:
    print("✅ All tests passed!")
    sys.exit(0)
else:
    print("❌ Some tests failed!")
    sys.exit(1)
