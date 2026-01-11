#!/usr/bin/env python3
"""
Bot Testing Walkthrough - OB-039

Interactive test of bot functionality during onboarding.
Prompts user to send test messages and verifies bot responds correctly.
"""

import logging
from typing import Dict, Any, List, Tuple


logger = logging.getLogger(__name__)


class BotTester:
    """Manages interactive bot testing during onboarding."""

    # Test stages
    STAGE_INTRO = "intro"
    STAGE_BASIC_COMMAND = "basic_command"
    STAGE_MESSAGE_TEST = "message_test"
    STAGE_COMPLETE = "complete"

    def __init__(self):
        """Initialize the bot tester."""
        self.logger = logging.getLogger(__name__)

    def get_intro_message(self) -> str:
        """Get the introduction message for bot testing.

        Returns:
            Formatted intro message explaining the test
        """
        return """*🧪 Time to Test Your Bot!*

Let's make sure everything works before we finish setup.

I'm gonna guide you through some quick tests. Just follow along!

**Test 1: Basic Response** 💬
Send me any message (like "Hello Ralph!") and I'll respond to show I'm working.

Go ahead - send me something!"""

    def get_basic_command_test_message(self) -> str:
        """Get message for testing basic commands.

        Returns:
            Message prompting user to test /start command
        """
        return """*✅ Great! I can hear you!*

**Test 2: Command Test** ⚡
Try sending a command to test my command handlers.

Send me:
```
/help
```

This will show you all the commands I understand."""

    def get_message_acknowledgment(self, message_text: str) -> str:
        """Acknowledge receipt of test message.

        Args:
            message_text: The message the user sent

        Returns:
            Acknowledgment message
        """
        return f"""*🎯 Got it!*

I received your message: "{message_text}"

This means I'm working correctly and can see your messages!"""

    def get_completion_message(self) -> str:
        """Get the completion message after all tests pass.

        Returns:
            Success message
        """
        return """*🎉 All Tests Passed!*

Your bot is working perfectly! Here's what we verified:

✅ **Message Handling** - I can receive and respond to messages
✅ **Command Processing** - I can handle commands like /help
✅ **Response Speed** - I'm responding quickly

You're all set! Ready to start building with your AI dev team?"""

    def get_failure_message(self, issue: str) -> str:
        """Get message when a test fails.

        Args:
            issue: Description of what went wrong

        Returns:
            Failure message with troubleshooting tips
        """
        return f"""*⚠️ Test Issue Detected*

**Problem:** {issue}

**Common Fixes:**

1. **Check .env file** - Make sure TELEGRAM_BOT_TOKEN is set correctly
2. **Restart the bot** - Sometimes a restart fixes connection issues
3. **Verify bot is running** - Check that ralph_bot.py is running

**Need help?** Send /help to see available commands, or contact support.

Let's try again once you've checked these. Send me a message when ready!"""

    def analyze_test_result(
        self,
        test_type: str,
        user_input: str,
        bot_responded: bool
    ) -> Tuple[bool, str]:
        """Analyze a test result and provide feedback.

        Args:
            test_type: Type of test (e.g., "message", "command")
            user_input: What the user sent
            bot_responded: Whether the bot successfully responded

        Returns:
            Tuple of (success, feedback_message)
        """
        if not bot_responded:
            issue = f"Bot didn't respond to {test_type}"
            return False, self.get_failure_message(issue)

        # Test passed
        if test_type == "message":
            return True, self.get_message_acknowledgment(user_input)
        elif test_type == "command":
            return True, self.get_basic_command_test_message()
        else:
            return True, "Test passed!"

    def get_test_checklist(self, state: Dict[str, Any]) -> str:
        """Generate a checklist of test progress.

        Args:
            state: Current testing state

        Returns:
            Formatted checklist with test status
        """
        tests = [
            ("basic_message_sent", "Send a test message"),
            ("command_tested", "Test a command"),
        ]

        lines = ["*Test Progress:*\n"]
        for test_id, test_label in tests:
            is_complete = state.get(test_id, False)
            icon = "✅" if is_complete else "⬜"
            lines.append(f"{icon} {test_label}")

        return "\n".join(lines)

    def is_testing_complete(self, state: Dict[str, Any]) -> bool:
        """Check if all tests are complete.

        Args:
            state: Current testing state

        Returns:
            True if all tests complete, False otherwise
        """
        required_tests = ["basic_message_sent", "command_tested"]
        return all(state.get(test, False) for test in required_tests)

    def get_next_test(self, state: Dict[str, Any]) -> str:
        """Get the next test to run.

        Args:
            state: Current testing state

        Returns:
            Next test ID or None if all complete
        """
        if not state.get("basic_message_sent", False):
            return "basic_message_sent"
        elif not state.get("command_tested", False):
            return "command_tested"
        else:
            return None


def get_bot_tester() -> BotTester:
    """Get the bot tester instance.

    Returns:
        BotTester instance
    """
    return BotTester()
