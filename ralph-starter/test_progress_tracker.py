#!/usr/bin/env python3
"""
Test script for Progress Tracker UI (OB-013)

Verifies that the progress tracker displays correctly with different states.
"""

from progress_tracker import get_progress_tracker


def test_progress_tracker():
    """Test the progress tracker with different states."""
    tracker = get_progress_tracker()

    print("=" * 60)
    print("PROGRESS TRACKER TEST (OB-013)")
    print("=" * 60)

    # Test 1: Empty state (nothing done)
    print("\n1. No progress:")
    print("-" * 60)
    state_empty = {
        "ssh_key_generated": False,
        "ssh_key_added_to_github": False,
        "repo_created": False,
        "git_configured": False,
        "first_commit": False,
        "environment_setup": False,
    }
    print(tracker.get_progress_message(state_empty))

    # Test 2: Partial progress (SSH key done, currently on GitHub step)
    print("\n2. Partial progress (SSH done, working on GitHub):")
    print("-" * 60)
    state_partial = {
        "ssh_key_generated": True,
        "ssh_key_added_to_github": False,
        "repo_created": False,
        "git_configured": False,
        "first_commit": False,
        "environment_setup": False,
    }
    print(tracker.get_progress_message(state_partial, current_step="ssh_key_added_to_github"))

    # Test 3: Halfway through
    print("\n3. Halfway through:")
    print("-" * 60)
    state_half = {
        "ssh_key_generated": True,
        "ssh_key_added_to_github": True,
        "repo_created": True,
        "git_configured": False,
        "first_commit": False,
        "environment_setup": False,
    }
    print(tracker.get_progress_message(state_half, current_step="git_configured"))

    # Test 4: Almost complete
    print("\n4. Almost complete:")
    print("-" * 60)
    state_almost = {
        "ssh_key_generated": True,
        "ssh_key_added_to_github": True,
        "repo_created": True,
        "git_configured": True,
        "first_commit": True,
        "environment_setup": False,
    }
    print(tracker.get_progress_message(state_almost, current_step="environment_setup"))

    # Test 5: Complete
    print("\n5. Complete:")
    print("-" * 60)
    state_complete = {
        "ssh_key_generated": True,
        "ssh_key_added_to_github": True,
        "repo_created": True,
        "git_configured": True,
        "first_commit": True,
        "environment_setup": True,
    }
    print(tracker.get_celebration_message(state_complete))

    # Test 6: Compact progress
    print("\n6. Compact progress display:")
    print("-" * 60)
    for desc, state in [
        ("Nothing", state_empty),
        ("25%", state_partial),
        ("50%", state_half),
        ("83%", state_almost),
        ("100%", state_complete)
    ]:
        compact = tracker.get_compact_progress(state)
        print(f"{desc:15} {compact}")

    # Test 7: Next step detection
    print("\n7. Next step detection:")
    print("-" * 60)
    next_id, next_label = tracker.get_next_step(state_half)
    print(f"Next step: {next_id} - {next_label}")

    # Test 8: Completion check
    print("\n8. Completion check:")
    print("-" * 60)
    print(f"Half complete? {tracker.is_setup_complete(state_half)}")
    print(f"Fully complete? {tracker.is_setup_complete(state_complete)}")

    # Test 9: Progress footer
    print("\n9. Message with progress footer:")
    print("-" * 60)
    message = "Ralph says: 'You doing great! Keep going!'"
    print(tracker.add_progress_footer(message, state_half))

    print("\n" + "=" * 60)
    print("TEST COMPLETE ✅")
    print("=" * 60)


if __name__ == "__main__":
    test_progress_tracker()
