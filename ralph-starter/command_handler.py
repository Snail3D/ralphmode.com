#!/usr/bin/env python3
"""
Command Handler - TL-006: Preserve Actual Directive While Translating Display

This module extracts the ACTUAL directive/intent from user input BEFORE translation.
The translation is for DISPLAY only - the real directive still gets processed.

Flow:
1. User says: "Fix this shit now!"
2. Command Handler extracts: directive="fix_urgently", priority="high", action="fix"
3. Translation Engine shows: "*Mr. Worms storms in, jaw clenched* 'Fix this now!'"
4. Ralph processes the ACTUAL urgency, not just the theatrical version

This ensures urgent commands are still processed urgently, questions get answered,
and the meaning is preserved even when the display is theatrical.
"""

import logging
import re
from typing import Dict, Optional, List, Tuple
from dataclasses import dataclass
from enum import Enum


class DirectiveType(Enum):
    """Types of directives that can be extracted from user input."""
    QUESTION = "question"           # User is asking something
    COMMAND_URGENT = "command_urgent"  # Do this NOW
    COMMAND_NORMAL = "command_normal"  # Do this when you can
    COMMAND_LOW = "command_low"      # Just a suggestion/idea
    STATUS_CHECK = "status_check"    # What's the status?
    APPROVAL = "approval"            # Yes/OK/Approved
    REJECTION = "rejection"          # No/Stop/Cancel
    FEEDBACK = "feedback"            # Praise or criticism
    CLARIFICATION = "clarification"  # Explaining something
    UNKNOWN = "unknown"              # Can't determine type


class Priority(Enum):
    """Priority levels for directives."""
    CRITICAL = "critical"  # Drop everything
    HIGH = "high"         # Do this soon
    NORMAL = "normal"     # Normal priority
    LOW = "low"          # When you have time
    NONE = "none"        # No priority (questions, feedback, etc.)


@dataclass
class Directive:
    """
    A directive extracted from user input.

    This is what Ralph ACTUALLY processes, separate from the theatrical display.
    """
    # Core intent
    directive_type: DirectiveType
    priority: Priority

    # Extracted content
    original_text: str          # The original user input (with swears)
    sanitized_text: str         # Sanitized version (no swears)
    action_keywords: List[str]  # Action words: fix, add, remove, etc.
    subject: Optional[str]      # What the directive is about

    # Context flags
    is_urgent: bool            # Contains urgency markers
    is_question: bool          # Asking a question
    is_approval: bool          # Approving something
    needs_response: bool       # Expects a reply

    # Emotional context
    tone: Optional[str]        # frustrated, pleased, calm, etc.
    emotional_intensity: str   # mild, moderate, intense

    def __repr__(self):
        return (f"Directive(type={self.directive_type.value}, "
                f"priority={self.priority.value}, "
                f"subject='{self.subject}', urgent={self.is_urgent})")


class CommandHandler:
    """
    Extracts directives and intent from user input.

    TL-006: The translation is for DISPLAY only. This handler extracts the
    ACTUAL directive so Ralph can respond appropriately.
    """

    # Urgency markers
    URGENCY_MARKERS = [
        r'\bnow\b',
        r'\basap\b',
        r'\bimmediately\b',
        r'\bright now\b',
        r'\bquickly\b',
        r'\bfast\b',
        r'\bhurry\b',
        r'\brushing\b',
        r'\bfirst\b',
        r'\basap\b',
        r'\btoday\b',
        r'\bthis second\b',
    ]

    # Question markers
    QUESTION_MARKERS = [
        r'\?$',  # Ends with question mark
        r'^(what|where|when|why|how|who|which)\b',
        r'^(is|are|can|could|would|should|do|does|did)\b',
        r'\b(status|progress|update)\b.*\?',
    ]

    # Action keywords (command verbs)
    ACTION_KEYWORDS = [
        'fix', 'add', 'remove', 'delete', 'update', 'change', 'modify',
        'create', 'build', 'make', 'implement', 'deploy', 'test',
        'refactor', 'optimize', 'improve', 'debug', 'check', 'review',
        'install', 'configure', 'setup', 'start', 'stop', 'restart',
        'investigate', 'analyze', 'explore', 'document', 'explain',
    ]

    # Status check keywords
    STATUS_KEYWORDS = [
        'status', 'progress', 'update', 'how\'s', 'what\'s happening',
        'where are we', 'any progress', 'how\'s it going',
    ]

    # Approval keywords
    APPROVAL_KEYWORDS = [
        'yes', 'ok', 'okay', 'good', 'approved', 'go ahead', 'proceed',
        'sounds good', 'looks good', 'do it', 'sure', 'fine', 'agreed',
    ]

    # Rejection keywords
    REJECTION_KEYWORDS = [
        'no', 'stop', 'cancel', 'don\'t', 'wait', 'hold on', 'pause',
        'reject', 'nevermind', 'abort',
    ]

    def __init__(self):
        """Initialize the command handler."""
        # Compile regex patterns for efficiency
        self.urgency_regex = [re.compile(pattern, re.IGNORECASE) for pattern in self.URGENCY_MARKERS]
        self.question_regex = [re.compile(pattern, re.IGNORECASE) for pattern in self.QUESTION_MARKERS]

    def extract_directive(
        self,
        user_input: str,
        sanitized_input: Optional[str] = None,
        detected_tone: Optional[str] = None
    ) -> Directive:
        """
        Extract the actual directive from user input.

        This is called BEFORE translation, so Ralph knows what to actually do,
        even if the display is theatrical.

        Args:
            user_input: The original user input (may contain swears)
            sanitized_input: The sanitized version (swears removed)
            detected_tone: Pre-detected tone (if available)

        Returns:
            Directive object with extracted intent
        """
        if not user_input or not user_input.strip():
            return self._create_empty_directive(user_input)

        # Use sanitized input for analysis (cleaner)
        text = sanitized_input if sanitized_input else user_input
        text_lower = text.lower()

        # Detect question
        is_question = self._is_question(text)

        # Detect urgency
        is_urgent = self._is_urgent(text)

        # Detect approval/rejection
        is_approval = self._is_approval(text_lower)
        is_rejection = self._is_rejection(text_lower)

        # Extract action keywords
        action_keywords = self._extract_action_keywords(text_lower)

        # Extract subject (what the directive is about)
        subject = self._extract_subject(text, action_keywords)

        # Determine directive type
        directive_type = self._determine_directive_type(
            is_question, is_urgent, is_approval, is_rejection,
            action_keywords, text_lower
        )

        # Determine priority
        priority = self._determine_priority(
            directive_type, is_urgent, action_keywords, text_lower
        )

        # Detect emotional intensity (for urgency/frustration)
        emotional_intensity = self._detect_emotional_intensity(
            user_input, is_urgent, detected_tone
        )

        # Determine if response is needed
        needs_response = (
            is_question or
            directive_type in [DirectiveType.COMMAND_URGENT, DirectiveType.STATUS_CHECK] or
            is_approval or is_rejection
        )

        return Directive(
            directive_type=directive_type,
            priority=priority,
            original_text=user_input,
            sanitized_text=text,
            action_keywords=action_keywords,
            subject=subject,
            is_urgent=is_urgent,
            is_question=is_question,
            is_approval=is_approval,
            needs_response=needs_response,
            tone=detected_tone,
            emotional_intensity=emotional_intensity
        )

    def _is_question(self, text: str) -> bool:
        """Check if the text is a question."""
        for regex in self.question_regex:
            if regex.search(text):
                return True
        return False

    def _is_urgent(self, text: str) -> bool:
        """Check if the text contains urgency markers."""
        for regex in self.urgency_regex:
            if regex.search(text):
                return True

        # Also check for multiple exclamation marks
        if text.count('!') >= 2:
            return True

        return False

    def _is_approval(self, text_lower: str) -> bool:
        """Check if the text is an approval."""
        # Short affirmative responses
        if text_lower.strip() in self.APPROVAL_KEYWORDS:
            return True

        for keyword in self.APPROVAL_KEYWORDS:
            if text_lower.startswith(keyword + ' ') or text_lower.startswith(keyword + ','):
                return True

        return False

    def _is_rejection(self, text_lower: str) -> bool:
        """Check if the text is a rejection."""
        # Short negative responses
        if text_lower.strip() in self.REJECTION_KEYWORDS:
            return True

        for keyword in self.REJECTION_KEYWORDS:
            if text_lower.startswith(keyword + ' ') or text_lower.startswith(keyword + ','):
                return True
            # Also check for exclamation mark emphasis
            if text_lower.startswith(keyword + '!'):
                return True

        return False

    def _extract_action_keywords(self, text_lower: str) -> List[str]:
        """Extract action keywords (verbs) from the text."""
        found_actions = []

        for action in self.ACTION_KEYWORDS:
            # Use word boundaries to avoid partial matches
            pattern = r'\b' + re.escape(action) + r'\b'
            if re.search(pattern, text_lower):
                found_actions.append(action)

        return found_actions

    def _extract_subject(self, text: str, action_keywords: List[str]) -> Optional[str]:
        """
        Extract the subject of the directive (what it's about).

        Examples:
        - "Fix the login bug" -> "login bug"
        - "Add dark mode" -> "dark mode"
        - "What's the status on deployment?" -> "deployment"
        """
        # Simple heuristic: take words after action keyword
        if action_keywords:
            # Find first action keyword
            for action in action_keywords:
                pattern = r'\b' + re.escape(action) + r'\b\s+(.+?)(?:\.|$)'
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    subject = match.group(1).strip()
                    # Remove common articles/prepositions
                    subject = re.sub(r'^(the|a|an|this|that)\s+', '', subject, flags=re.IGNORECASE)
                    return subject

        # For questions, extract what comes after question word
        question_match = re.search(r'^(what|where|when|why|how|who).*?\b(is|are|about)\s+(.+?)(?:\?|$)',
                                  text, re.IGNORECASE)
        if question_match:
            subject = question_match.group(3).strip()
            subject = re.sub(r'^(the|a|an|this|that)\s+', '', subject, flags=re.IGNORECASE)
            return subject

        # Fallback: use the whole text (truncated)
        return text[:50] if len(text) > 50 else text

    def _determine_directive_type(
        self,
        is_question: bool,
        is_urgent: bool,
        is_approval: bool,
        is_rejection: bool,
        action_keywords: List[str],
        text_lower: str
    ) -> DirectiveType:
        """Determine the type of directive."""
        # Priority order matters
        if is_question:
            return DirectiveType.QUESTION

        if is_approval:
            return DirectiveType.APPROVAL

        if is_rejection:
            return DirectiveType.REJECTION

        # Check for status check
        for keyword in self.STATUS_KEYWORDS:
            if keyword in text_lower:
                return DirectiveType.STATUS_CHECK

        # Commands with action keywords
        if action_keywords:
            if is_urgent:
                return DirectiveType.COMMAND_URGENT
            elif any(word in text_lower for word in ['maybe', 'consider', 'could', 'might', 'suggestion']):
                return DirectiveType.COMMAND_LOW
            else:
                return DirectiveType.COMMAND_NORMAL

        # Feedback (praise or criticism without action)
        if any(word in text_lower for word in ['good', 'great', 'excellent', 'nice', 'bad', 'poor', 'terrible']):
            return DirectiveType.FEEDBACK

        # Check if it's clarification (explaining something)
        if any(word in text_lower for word in ['because', 'i mean', 'what i meant', 'to clarify']):
            return DirectiveType.CLARIFICATION

        return DirectiveType.UNKNOWN

    def _determine_priority(
        self,
        directive_type: DirectiveType,
        is_urgent: bool,
        action_keywords: List[str],
        text_lower: str
    ) -> Priority:
        """Determine the priority level of the directive."""
        # Questions and feedback have no priority
        if directive_type in [DirectiveType.QUESTION, DirectiveType.FEEDBACK,
                             DirectiveType.CLARIFICATION, DirectiveType.UNKNOWN]:
            return Priority.NONE

        # Approvals/rejections are critical (immediate response needed)
        if directive_type in [DirectiveType.APPROVAL, DirectiveType.REJECTION]:
            return Priority.CRITICAL

        # Status checks are high priority
        if directive_type == DirectiveType.STATUS_CHECK:
            return Priority.HIGH

        # Command priority based on urgency and keywords
        if directive_type == DirectiveType.COMMAND_URGENT:
            return Priority.CRITICAL if 'now' in text_lower or 'asap' in text_lower else Priority.HIGH

        if directive_type == DirectiveType.COMMAND_LOW:
            return Priority.LOW

        # Normal commands
        if is_urgent:
            return Priority.HIGH

        # Check for priority keywords
        if any(word in text_lower for word in ['first', 'priority', 'important', 'critical']):
            return Priority.HIGH

        return Priority.NORMAL

    def _detect_emotional_intensity(
        self,
        original_text: str,
        is_urgent: bool,
        detected_tone: Optional[str]
    ) -> str:
        """
        Detect the emotional intensity of the message.

        Returns: 'mild', 'moderate', or 'intense'
        """
        # Check for swear words (in original text)
        swear_count = sum(1 for pattern in [
            r'\bf+u+c+k+', r'\bs+h+i+t+', r'\bd+a+m+n+', r'\ba+s+s+',
            r'\bb+i+t+c+h+', r'\bb+a+s+t+a+r+d+'
        ] if re.search(pattern, original_text, re.IGNORECASE))

        # Check for caps and exclamation marks
        caps_ratio = sum(1 for c in original_text if c.isupper()) / max(len(original_text), 1)
        exclamation_count = original_text.count('!')

        # Determine intensity
        if swear_count >= 2 or exclamation_count >= 3 or caps_ratio > 0.5:
            return 'intense'

        if swear_count >= 1 or exclamation_count >= 2 or is_urgent or detected_tone == 'frustrated':
            return 'moderate'

        return 'mild'

    def _create_empty_directive(self, user_input: str) -> Directive:
        """Create an empty directive for blank input."""
        return Directive(
            directive_type=DirectiveType.UNKNOWN,
            priority=Priority.NONE,
            original_text=user_input,
            sanitized_text=user_input,
            action_keywords=[],
            subject=None,
            is_urgent=False,
            is_question=False,
            is_approval=False,
            needs_response=False,
            tone=None,
            emotional_intensity='mild'
        )


# Global instance
_command_handler = None


def get_command_handler() -> CommandHandler:
    """Get or create global command handler instance."""
    global _command_handler
    if _command_handler is None:
        _command_handler = CommandHandler()
    return _command_handler


def extract_directive(
    user_input: str,
    sanitized_input: Optional[str] = None,
    detected_tone: Optional[str] = None
) -> Directive:
    """
    Convenience function: Extract directive from user input.

    Args:
        user_input: The original user input
        sanitized_input: Optional sanitized version
        detected_tone: Optional pre-detected tone

    Returns:
        Directive object with extracted intent
    """
    handler = get_command_handler()
    return handler.extract_directive(user_input, sanitized_input, detected_tone)


if __name__ == "__main__":
    # Test the command handler
    print("Testing Command Handler (TL-006)...\n")
    print("=" * 70)

    test_inputs = [
        "Fix the login bug now!",
        "What's the status on deployment?",
        "Add dark mode to the app",
        "This is taking way too fucking long",
        "Great work on the feature!",
        "Maybe we should consider refactoring this?",
        "Stop! Don't deploy yet",
        "Okay, approved",
        "Check the database connection",
    ]

    handler = CommandHandler()

    for user_input in test_inputs:
        print(f"\nInput: {user_input}")
        print("-" * 70)

        # Extract directive
        directive = handler.extract_directive(user_input)

        print(f"Directive Type: {directive.directive_type.value}")
        print(f"Priority: {directive.priority.value}")
        print(f"Subject: {directive.subject}")
        print(f"Action Keywords: {directive.action_keywords}")
        print(f"Is Urgent: {directive.is_urgent}")
        print(f"Is Question: {directive.is_question}")
        print(f"Needs Response: {directive.needs_response}")
        print(f"Emotional Intensity: {directive.emotional_intensity}")
        print("=" * 70)
