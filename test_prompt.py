#!/usr/bin/env python3
"""
Test script for prompt_user_confirmation function.
Run this manually to test the interactive prompt.
"""

import sys
sys.path.insert(0, '.')
from scripts.run_22_oem_sequential import prompt_user_confirmation

# Test prompt with Carrier (first OEM)
print("Testing prompt_user_confirmation with Carrier (OEM 1/22)...")
result = prompt_user_confirmation('Carrier', 0, 22)
print(f'\nUser choice: {result}')

# Test with a multi-word OEM name
print("\n\nTesting prompt_user_confirmation with Briggs & Stratton (OEM 3/22)...")
result2 = prompt_user_confirmation('Briggs & Stratton', 2, 22)
print(f'\nUser choice: {result2}')
