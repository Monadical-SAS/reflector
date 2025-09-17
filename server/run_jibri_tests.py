#!/usr/bin/env python
"""Simple test runner for Jibri tests that doesn't require Docker."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import test functions after path is set
exec(open("tests/test_jibri_events.py").read(), globals())


def run_tests():
    tests = [
        ("test_parse_room_created_event", test_parse_room_created_event),
        ("test_parse_participant_joined_event", test_parse_participant_joined_event),
        (
            "test_parse_unknown_event_returns_none",
            test_parse_unknown_event_returns_none,
        ),
        (
            "test_parse_events_file_with_complete_session",
            test_parse_events_file_with_complete_session,
        ),
        ("test_parse_events_file_missing_file", test_parse_events_file_missing_file),
    ]

    passed = 0
    failed = 0

    for name, test_func in tests:
        try:
            test_func()
            print(f"✓ {name}")
            passed += 1
        except AssertionError as e:
            print(f"✗ {name}: {e}")
            failed += 1
        except Exception as e:
            print(f"✗ {name}: Unexpected error: {e}")
            failed += 1

    print(f"\nResults: {passed} passed, {failed} failed")
    return failed == 0


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
