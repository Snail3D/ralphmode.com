#!/usr/bin/env python3
"""
SP-001: Spam Pattern Detection for Ralph Mode Bot
SP-002: Abuse Detection for Ralph Mode Bot

Detects and filters spam patterns in feedback submissions:
- Gibberish (entropy analysis)
- Repeated submissions (same text)
- Promotional content (URLs, ads)
- Off-topic submissions (not about Ralph Mode)

Detects abusive content:
- Profanity and slurs
- Threats and harassment
- Personal attacks

Auto-rejects spam with reason and logs for admin review.
Flags abusive content and notifies admins.
"""

import os
import re
import logging
import hashlib
from datetime import datetime, timedelta
from typing import Optional, Dict, Tuple
from collections import Counter
import math

from database import get_db, Feedback

logger = logging.getLogger(__name__)


class SpamDetector:
    """
    Detects spam patterns in feedback submissions.

    Features:
    - Gibberish detection using entropy analysis
    - Repeated submission detection (same content hash)
    - Promotional content detection (URLs, ads, marketing)
    - Off-topic detection (not about Ralph Mode bot)
    """

    # Spam detection thresholds
    MIN_ENTROPY_THRESHOLD = 2.5  # Below this = gibberish
    MIN_WORD_LENGTH = 3  # Minimum valid word length
    MAX_REPEATED_CHARS = 5  # Max consecutive same characters

    # Promotional keywords (case-insensitive)
    PROMOTIONAL_KEYWORDS = [
        "buy now", "click here", "limited time", "act now", "order now",
        "special offer", "discount", "sale", "free trial", "subscribe now",
        "visit our", "check out", "follow us", "join us", "sign up",
        "get started", "click link", "promo code", "coupon", "deal",
        "earn money", "work from home", "make money", "crypto", "bitcoin",
        "investment", "trading", "forex", "casino", "viagra", "pharmacy"
    ]

    # Ralph Mode related keywords (on-topic)
    RALPH_KEYWORDS = [
        "ralph", "bot", "telegram", "ai", "dev", "developer", "team",
        "feature", "bug", "error", "code", "implement", "build", "deploy",
        "worker", "gomer", "stool", "mona", "gus", "mr. worms", "worms",
        "simpsons", "springfield", "feedback", "session", "chat", "message",
        "groq", "llm", "voice", "screenshot", "commit", "git", "quality",
        "subscription", "tier", "rate limit", "improvement", "suggestion"
    ]

    def __init__(self, lookback_hours: int = 24):
        """
        Initialize spam detector.

        Args:
            lookback_hours: How far back to check for duplicate submissions (default: 24 hours)
        """
        self.lookback_hours = lookback_hours

    def detect_spam(self, content: str, user_id: int) -> Tuple[bool, Optional[str]]:
        """
        Detect if feedback content is spam.

        Args:
            content: Feedback text content
            user_id: Database user ID

        Returns:
            Tuple of (is_spam: bool, reason: str or None)
            - (True, "reason") if spam detected
            - (False, None) if content is legitimate
        """
        # 1. Check for gibberish
        if self._is_gibberish(content):
            logger.warning(f"Gibberish detected from user {user_id}: {content[:50]}...")
            return (True, "Gibberish content detected (low entropy)")

        # 2. Check for repeated submissions
        if self._is_repeated_submission(content, user_id):
            logger.warning(f"Repeated submission detected from user {user_id}")
            return (True, "Duplicate submission (already submitted recently)")

        # 3. Check for promotional content
        if self._is_promotional(content):
            logger.warning(f"Promotional content detected from user {user_id}: {content[:50]}...")
            return (True, "Promotional/spam content detected")

        # 4. Check for off-topic content
        if self._is_off_topic(content):
            logger.warning(f"Off-topic content detected from user {user_id}: {content[:50]}...")
            return (True, "Off-topic content (not about Ralph Mode)")

        # All checks passed - content is legitimate
        return (False, None)

    def _is_gibberish(self, content: str) -> bool:
        """
        Detect gibberish using entropy analysis.

        Gibberish has low entropy (repetitive patterns, random characters).
        Real text has higher entropy (varied word usage).

        Args:
            content: Text to analyze

        Returns:
            True if gibberish detected
        """
        # Clean content
        text = content.strip().lower()

        if len(text) < 10:
            # Too short to analyze reliably
            return False

        # Check for excessive repeated characters
        # e.g., "aaaaaaaa", "hehehehehehe"
        max_consecutive = max(
            (len(list(group)) for char, group in __import__('itertools').groupby(text) if char.isalnum()),
            default=0
        )
        if max_consecutive > self.MAX_REPEATED_CHARS:
            logger.debug(f"Excessive repeated characters detected: {max_consecutive}")
            return True

        # Calculate character-level entropy
        char_counts = Counter(text)
        total_chars = len(text)

        entropy = 0.0
        for count in char_counts.values():
            probability = count / total_chars
            entropy -= probability * math.log2(probability)

        logger.debug(f"Content entropy: {entropy:.2f} (threshold: {self.MIN_ENTROPY_THRESHOLD})")

        if entropy < self.MIN_ENTROPY_THRESHOLD:
            return True

        # Check word structure
        # Real text has words with vowels and consonants
        words = re.findall(r'\b[a-z]{3,}\b', text)

        if not words:
            # No valid words found
            return True

        # Check for reasonable vowel/consonant ratio
        vowels = set('aeiou')
        valid_words = 0

        for word in words:
            has_vowel = any(c in vowels for c in word)
            has_consonant = any(c not in vowels for c in word)

            if has_vowel and has_consonant:
                valid_words += 1

        # If less than 30% of words have proper structure, likely gibberish
        if len(words) > 0 and (valid_words / len(words)) < 0.3:
            logger.debug(f"Low valid word ratio: {valid_words}/{len(words)}")
            return True

        return False

    def _is_repeated_submission(self, content: str, user_id: int) -> bool:
        """
        Check if user has submitted identical content recently.

        Uses content hash to efficiently detect duplicates.

        Args:
            content: Feedback content
            user_id: Database user ID

        Returns:
            True if duplicate detected
        """
        # Create content hash
        content_hash = hashlib.sha256(content.strip().lower().encode()).hexdigest()

        try:
            with get_db() as db:
                # Look for recent feedback from same user with same content hash
                cutoff_time = datetime.utcnow() - timedelta(hours=self.lookback_hours)

                existing = db.query(Feedback).filter(
                    Feedback.user_id == user_id,
                    Feedback.created_at >= cutoff_time
                ).all()

                for feedback in existing:
                    existing_hash = hashlib.sha256(
                        feedback.content.strip().lower().encode()
                    ).hexdigest()

                    if existing_hash == content_hash:
                        logger.debug(f"Found duplicate submission from last {self.lookback_hours}h")
                        return True

                return False

        except Exception as e:
            logger.error(f"Error checking for repeated submissions: {e}")
            # If we can't check, don't block (fail open)
            return False

    def _is_promotional(self, content: str) -> bool:
        """
        Detect promotional/advertising content.

        Checks for:
        - Promotional keywords
        - Multiple URLs
        - Marketing patterns

        Args:
            content: Text to analyze

        Returns:
            True if promotional content detected
        """
        text_lower = content.lower()

        # Check for promotional keywords
        keyword_matches = sum(
            1 for keyword in self.PROMOTIONAL_KEYWORDS
            if keyword in text_lower
        )

        if keyword_matches >= 2:
            # Multiple promotional keywords = spam
            logger.debug(f"Multiple promotional keywords detected: {keyword_matches}")
            return True

        # Check for URLs
        url_pattern = r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
        urls = re.findall(url_pattern, content)

        if len(urls) >= 3:
            # Multiple URLs = likely spam
            logger.debug(f"Multiple URLs detected: {len(urls)}")
            return True

        # Check for suspicious patterns
        # E.g., "Click here: http://..." or "Visit: http://..."
        suspicious_patterns = [
            r'click\s+(here|now|link)',
            r'visit\s+(our|my|this)',
            r'check\s+out',
            r'follow\s+(me|us)',
            r'\$\d+',  # Money amounts
            r'\d+%\s+(off|discount)',
        ]

        for pattern in suspicious_patterns:
            if re.search(pattern, text_lower):
                logger.debug(f"Suspicious pattern matched: {pattern}")
                return True

        return False

    def _is_off_topic(self, content: str) -> bool:
        """
        Detect off-topic content (not about Ralph Mode).

        Uses keyword analysis to determine relevance.

        Args:
            content: Text to analyze

        Returns:
            True if content is off-topic
        """
        text_lower = content.lower()

        # Very short messages are hard to judge
        if len(content.strip()) < 20:
            return False  # Give benefit of doubt

        # Count Ralph-related keywords
        ralph_matches = sum(
            1 for keyword in self.RALPH_KEYWORDS
            if keyword in text_lower
        )

        # Extract meaningful words (3+ chars)
        words = re.findall(r'\b[a-z]{3,}\b', text_lower)
        total_words = len(words)

        if total_words < 5:
            # Too short to judge
            return False

        # If no Ralph-related keywords in a substantial message, likely off-topic
        # Exception: very general feedback like "great bot!" is ok
        if ralph_matches == 0 and total_words > 10:
            # Check if it's generic positive/negative feedback
            general_feedback_words = [
                'great', 'good', 'bad', 'awesome', 'terrible', 'love', 'hate',
                'like', 'dislike', 'excellent', 'poor', 'amazing', 'awful',
                'thanks', 'thank', 'perfect', 'broken', 'works', 'working'
            ]

            has_general_feedback = any(word in text_lower for word in general_feedback_words)

            if not has_general_feedback:
                logger.debug(f"No Ralph-related keywords or general feedback in {total_words} words")
                return True

        return False

    def auto_reject_spam(self, feedback_id: int, reason: str) -> bool:
        """
        Auto-reject spam feedback with reason.

        Args:
            feedback_id: Feedback database ID
            reason: Rejection reason

        Returns:
            True if successfully rejected
        """
        try:
            with get_db() as db:
                feedback = db.query(Feedback).filter(Feedback.id == feedback_id).first()

                if not feedback:
                    logger.error(f"Feedback {feedback_id} not found")
                    return False

                # Update status to rejected
                feedback.status = "rejected"
                feedback.rejection_reason = reason
                feedback.rejected_at = datetime.utcnow()

                db.commit()

                # Log for admin review
                self._log_spam_rejection(feedback_id, reason, feedback.user_id, feedback.content)

                logger.info(f"Auto-rejected spam feedback {feedback_id}: {reason}")
                return True

        except Exception as e:
            logger.error(f"Failed to auto-reject spam feedback {feedback_id}: {e}")
            return False

    def _log_spam_rejection(self, feedback_id: int, reason: str, user_id: int, content: str):
        """
        Log spam rejection for admin review.

        Creates a log entry with details for manual review if needed.

        Args:
            feedback_id: Feedback ID
            reason: Rejection reason
            user_id: User ID who submitted
            content: Feedback content (truncated)
        """
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "feedback_id": feedback_id,
            "user_id": user_id,
            "reason": reason,
            "content_preview": content[:100] if content else "",
            "action": "auto_rejected"
        }

        # Log to file for admin review
        log_file = "logs/spam_rejections.log"
        os.makedirs(os.path.dirname(log_file), exist_ok=True)

        try:
            with open(log_file, 'a') as f:
                import json
                f.write(json.dumps(log_entry) + '\n')
        except Exception as e:
            logger.error(f"Failed to write spam rejection log: {e}")


# Singleton instance
_spam_detector = None

def get_spam_detector() -> SpamDetector:
    """
    Get the global spam detector instance.

    Returns:
        SpamDetector instance
    """
    global _spam_detector
    if _spam_detector is None:
        _spam_detector = SpamDetector()
    return _spam_detector


class AbuseDetector:
    """
    SP-002: Detects abusive content in feedback submissions.

    Features:
    - Profanity and slur detection
    - Threat and harassment detection
    - Personal attack detection
    - User warning/flagging system
    - Admin notification for flagged content
    """

    # Profanity and slurs patterns (use word boundaries to avoid false positives)
    # Note: These are detection patterns, not promotion of offensive language
    PROFANITY_PATTERNS = [
        r'\bf+u+c+k',
        r'\bs+h+i+t',
        r'\ba+s+s+h+o+l+e',
        r'\bb+i+t+c+h',
        r'\bc+u+n+t',
        r'\bc+r+a+p',
        r'\bp+i+s+s',
        r'\bd+i+c+k',
        r'\bc+o+c+k',
        r'\bp+u+s+s+y',
        # Common variations and leetspeak
        r'\bf\*+c+k',
        r'\bs\*+h+i+t',
        r'\bf+4+c+k',
        r'\bs+h+1+t',
    ]

    # Mild profanity that's only abuse in certain contexts
    # We check these separately to avoid false positives
    CONTEXT_DEPENDENT_PATTERNS = [
        (r'\bd+a+m+n', [r'you', r'this', r'that']),  # "damn you" is abuse, "damn good" is not
        (r'\bh+e+l+l', [r'go to hell', r'burn in hell', r'hell with you']),  # "go to hell" is abuse, "hell yeah" is not
    ]

    # Threat indicators
    THREAT_PATTERNS = [
        r'\b(kill|murder|hurt|harm|attack|beat|shoot|stab|destroy)\s+(you|them|him|her)',
        r'\b(going\s+to|gonna|will)\s+(kill|hurt|harm|attack|beat)',
        r'\bdie\b',
        r'\bdeath\s+threat',
        r'\bviolence',
        r'\bphysical\s+harm',
        r'\byou\s+(deserve|should)\s+to\s+(die|suffer)',
    ]

    # Harassment indicators
    HARASSMENT_PATTERNS = [
        r'\bstupid\s+(developer|dev|programmer|coder)',
        r'\byou\s+(suck|fail|are\s+trash|are\s+garbage)',
        r'\bpathetic\s+excuse',
        r'\bworthless\s+piece',
        r'\bkill\s+yourself',
        r'\bkys\b',  # Common abbreviation for "kill yourself"
        r'\buninstall\s+life',
        r'\byou\s+should\s+quit',
        r'\bget\s+cancer',
        r'\bhope\s+you\s+(die|suffer)',
    ]

    # Personal attack indicators
    PERSONAL_ATTACK_PATTERNS = [
        r'\bidiot',
        r'\bmoron',
        r'\bretard',
        r'\bloser',
        r'\bfailure',
        r'\bincompetent',
        r'\bpathetic',
        r'\bworthless',
        r'\buseless',
        r'\btrash',
        r'\bgarbage',
    ]

    def detect_abuse(self, content: str, user_id: int) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Detect abusive content in feedback.

        Args:
            content: Feedback text content
            user_id: Database user ID

        Returns:
            Tuple of (is_abuse: bool, reason: str or None, category: str or None)
            - (True, "reason", "category") if abuse detected
            - (False, None, None) if content is acceptable
        """
        text_lower = content.lower()

        # 1. Check for profanity/slurs
        for pattern in self.PROFANITY_PATTERNS:
            if re.search(pattern, text_lower, re.IGNORECASE):
                logger.warning(f"Profanity detected from user {user_id}: {content[:50]}...")
                return (True, "Profanity or slurs detected", "profanity")

        # 1b. Check context-dependent profanity
        for word_pattern, context_patterns in self.CONTEXT_DEPENDENT_PATTERNS:
            if re.search(word_pattern, text_lower, re.IGNORECASE):
                # Check if any abusive context is present
                for context_pattern in context_patterns:
                    if re.search(context_pattern, text_lower, re.IGNORECASE):
                        logger.warning(f"Context-dependent profanity detected from user {user_id}: {content[:50]}...")
                        return (True, "Profanity or slurs detected", "profanity")

        # 2. Check for threats
        for pattern in self.THREAT_PATTERNS:
            if re.search(pattern, text_lower, re.IGNORECASE):
                logger.error(f"THREAT detected from user {user_id}: {content[:50]}...")
                return (True, "Threats or violent content detected", "threat")

        # 3. Check for harassment
        for pattern in self.HARASSMENT_PATTERNS:
            if re.search(pattern, text_lower, re.IGNORECASE):
                logger.warning(f"Harassment detected from user {user_id}: {content[:50]}...")
                return (True, "Harassment or abusive language detected", "harassment")

        # 4. Check for personal attacks
        # Require at least 2 personal attack words to avoid false positives
        attack_count = sum(
            1 for pattern in self.PERSONAL_ATTACK_PATTERNS
            if re.search(pattern, text_lower, re.IGNORECASE)
        )

        if attack_count >= 2:
            logger.warning(f"Personal attacks detected from user {user_id}: {content[:50]}...")
            return (True, "Personal attacks detected", "personal_attack")

        # All checks passed
        return (False, None, None)

    def flag_abusive_feedback(self, feedback_id: int, reason: str, category: str, user_id: int, content: str) -> bool:
        """
        Flag abusive feedback and notify admin.

        Args:
            feedback_id: Feedback database ID
            reason: Flagging reason
            category: Abuse category (profanity, threat, harassment, personal_attack)
            user_id: User ID who submitted
            content: Feedback content

        Returns:
            True if successfully flagged
        """
        try:
            with get_db() as db:
                from database import Feedback, User

                # Update feedback status to flagged
                feedback = db.query(Feedback).filter(Feedback.id == feedback_id).first()

                if not feedback:
                    logger.error(f"Feedback {feedback_id} not found")
                    return False

                # Mark as rejected with abuse reason
                feedback.status = "rejected"
                feedback.rejection_reason = f"[ABUSE:{category}] {reason}"
                feedback.rejected_at = datetime.utcnow()

                db.commit()

                # Handle user warnings/flagging
                self._handle_user_warning(user_id, category)

                # Notify admin
                self._notify_admin_of_abuse(feedback_id, reason, category, user_id, content)

                # Log the flagging
                self._log_abuse_flag(feedback_id, reason, category, user_id, content)

                logger.info(f"Flagged abusive feedback {feedback_id}: {category}")
                return True

        except Exception as e:
            logger.error(f"Failed to flag abusive feedback {feedback_id}: {e}")
            return False

    def _handle_user_warning(self, user_id: int, category: str):
        """
        Handle user warning/flagging for abusive behavior.

        First offense: Warning
        Repeat offense: Flag user for review

        Args:
            user_id: Database user ID
            category: Abuse category
        """
        try:
            with get_db() as db:
                from database import User, Feedback

                user = db.query(User).filter(User.id == user_id).first()

                if not user:
                    logger.error(f"User {user_id} not found")
                    return

                # Count previous abuse flags
                abuse_count = db.query(Feedback).filter(
                    Feedback.user_id == user_id,
                    Feedback.rejection_reason.like('[ABUSE:%')
                ).count()

                if abuse_count == 1:
                    # First offense - log warning
                    logger.warning(f"User {user_id} received first abuse warning ({category})")
                    # Slight quality score penalty
                    user.quality_score = max(0, user.quality_score - 10)

                elif abuse_count >= 2:
                    # Repeat offense - flag user
                    logger.error(f"User {user_id} flagged for repeated abuse ({abuse_count} incidents)")
                    # Significant quality score penalty
                    user.quality_score = max(0, user.quality_score - 25)

                    # If quality score drops too low, consider banning
                    if user.quality_score < 20:
                        logger.critical(f"User {user_id} has low quality score ({user.quality_score}) - review for ban")

                db.commit()

        except Exception as e:
            logger.error(f"Failed to handle user warning for {user_id}: {e}")

    def _notify_admin_of_abuse(self, feedback_id: int, reason: str, category: str, user_id: int, content: str):
        """
        Notify admin of flagged abusive content.

        Args:
            feedback_id: Feedback ID
            reason: Flagging reason
            category: Abuse category
            user_id: User ID
            content: Feedback content
        """
        notification = {
            "timestamp": datetime.utcnow().isoformat(),
            "type": "abuse_flagged",
            "severity": "HIGH" if category == "threat" else "MEDIUM",
            "feedback_id": feedback_id,
            "user_id": user_id,
            "category": category,
            "reason": reason,
            "content_preview": content[:200] if content else ""
        }

        # Log to admin notification file
        log_file = "logs/admin_notifications.log"
        os.makedirs(os.path.dirname(log_file), exist_ok=True)

        try:
            with open(log_file, 'a') as f:
                import json
                f.write(json.dumps(notification) + '\n')

            # For threats, also log to security alerts
            if category == "threat":
                security_log = "logs/security_alerts.log"
                with open(security_log, 'a') as f:
                    f.write(json.dumps(notification) + '\n')

        except Exception as e:
            logger.error(f"Failed to write admin notification: {e}")

    def _log_abuse_flag(self, feedback_id: int, reason: str, category: str, user_id: int, content: str):
        """
        Log abuse flag for tracking and analysis.

        Args:
            feedback_id: Feedback ID
            reason: Flagging reason
            category: Abuse category
            user_id: User ID
            content: Feedback content (truncated)
        """
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "feedback_id": feedback_id,
            "user_id": user_id,
            "category": category,
            "reason": reason,
            "content_preview": content[:100] if content else "",
            "action": "flagged_for_abuse"
        }

        # Log to abuse tracking file
        log_file = "logs/abuse_flags.log"
        os.makedirs(os.path.dirname(log_file), exist_ok=True)

        try:
            with open(log_file, 'a') as f:
                import json
                f.write(json.dumps(log_entry) + '\n')
        except Exception as e:
            logger.error(f"Failed to write abuse flag log: {e}")


# Singleton instances
_spam_detector = None
_abuse_detector = None

def get_abuse_detector() -> AbuseDetector:
    """
    Get the global abuse detector instance.

    Returns:
        AbuseDetector instance
    """
    global _abuse_detector
    if _abuse_detector is None:
        _abuse_detector = AbuseDetector()
    return _abuse_detector


def screen_feedback(content: str, user_id: int, feedback_id: Optional[int] = None) -> Tuple[bool, Optional[str]]:
    """
    Screen feedback for spam patterns and abusive content.

    Convenience function that checks spam/abuse and auto-rejects/flags if needed.

    Args:
        content: Feedback content
        user_id: Database user ID
        feedback_id: Optional feedback ID (for auto-rejection/flagging)

    Returns:
        Tuple of (is_rejected: bool, reason: str or None)
        - (True, "reason") if spam/abuse detected
        - (False, None) if content is legitimate
    """
    # Check for spam first
    spam_detector = get_spam_detector()
    is_spam, spam_reason = spam_detector.detect_spam(content, user_id)

    if is_spam and feedback_id:
        spam_detector.auto_reject_spam(feedback_id, spam_reason)
        return (True, spam_reason)
    elif is_spam:
        return (True, spam_reason)

    # Check for abuse
    abuse_detector = get_abuse_detector()
    is_abuse, abuse_reason, abuse_category = abuse_detector.detect_abuse(content, user_id)

    if is_abuse and feedback_id:
        abuse_detector.flag_abusive_feedback(feedback_id, abuse_reason, abuse_category, user_id, content)
        return (True, abuse_reason)
    elif is_abuse:
        return (True, abuse_reason)

    # All checks passed
    return (False, None)
