#!/usr/bin/env python3
"""
QS-001: Feedback Quality Scoring Module for Ralph Mode Bot

Calculates quality scores (0-100) for user feedback based on:
- Clarity (0-25): Is it clearly written?
- Actionability (0-25): Can we do something with this?
- Specificity (0-25): Does it include details, examples?
- Reproducibility (0-25): Can we reproduce/understand scope?

This is part of the RLHF Self-Building System where feedback quality
determines priority and implementation order.
"""

import logging
import re
from typing import Dict, Optional
from datetime import datetime

from database import get_db, Feedback, InputValidator

logger = logging.getLogger(__name__)


class FeedbackScorer:
    """
    Scores feedback quality based on objective criteria.

    Quality factors (0-25 each, totaling 0-100):
    1. Clarity: Grammar, structure, coherence
    2. Actionability: Clear ask, feasible implementation
    3. Specificity: Concrete details, examples, context
    4. Reproducibility: Steps provided, scope defined
    """

    def __init__(self):
        """Initialize the feedback scorer."""
        pass

    def score_clarity(self, content: str) -> float:
        """
        Score feedback clarity (0-25).

        Evaluates:
        - Length (too short/long reduces clarity)
        - Sentence structure (complete thoughts)
        - Grammar indicators (punctuation, capitalization)
        - Readability (not all caps, not excessive emoji)

        Args:
            content: Feedback text content

        Returns:
            Clarity score (0-25)
        """
        score = 25.0

        # Length check: ideal is 20-500 words
        words = content.split()
        word_count = len(words)

        if word_count < 5:
            score -= 15  # Too vague
        elif word_count < 10:
            score -= 10
        elif word_count > 500:
            score -= 5  # Too verbose
        elif word_count > 1000:
            score -= 10

        # Sentence structure: check for complete sentences
        sentences = re.split(r'[.!?]+', content)
        valid_sentences = [s for s in sentences if len(s.strip()) > 10]

        if len(valid_sentences) < 1:
            score -= 10  # No complete sentences

        # Check for all caps (screaming)
        if content.isupper() and len(content) > 20:
            score -= 5

        # Check for excessive emoji (more than 1 per 10 words)
        emoji_pattern = re.compile(r'[\U0001F300-\U0001F9FF]')
        emoji_count = len(emoji_pattern.findall(content))
        if word_count > 0 and emoji_count > word_count / 10:
            score -= 5

        # Check for basic punctuation (indicates thoughtful writing)
        has_punctuation = bool(re.search(r'[.,!?;:]', content))
        if not has_punctuation and word_count > 10:
            score -= 5

        # Check for mixed case (indicates normal writing, not lazy)
        has_uppercase = any(c.isupper() for c in content)
        has_lowercase = any(c.islower() for c in content)
        if not (has_uppercase and has_lowercase) and len(content) > 20:
            score -= 5

        return max(0.0, min(25.0, score))

    def score_actionability(self, content: str) -> float:
        """
        Score feedback actionability (0-25).

        Evaluates:
        - Contains action words (add, fix, change, improve)
        - Describes desired outcome
        - Avoids vague complaints ("this sucks")
        - Has a clear request

        Args:
            content: Feedback text content

        Returns:
            Actionability score (0-25)
        """
        score = 15.0  # Base score (assume somewhat actionable)

        content_lower = content.lower()

        # Check for action words
        action_words = [
            'add', 'remove', 'fix', 'change', 'improve', 'update', 'make',
            'should', 'could', 'need', 'want', 'would like', 'please',
            'implement', 'create', 'build', 'modify', 'adjust', 'enhance'
        ]

        action_word_count = sum(1 for word in action_words if word in content_lower)
        if action_word_count > 0:
            score += min(5, action_word_count * 2)  # Up to +5 for action words
        else:
            score -= 5  # No clear action requested

        # Check for vague complaints (reduce score)
        vague_complaints = [
            'sucks', 'terrible', 'awful', 'hate', 'worst', 'garbage',
            'trash', 'useless', 'bad', 'broken'
        ]

        complaint_count = sum(1 for word in vague_complaints if word in content_lower)
        if complaint_count > 2:
            score -= 10  # Multiple complaints without constructive feedback
        elif complaint_count > 0:
            score -= 3

        # Check for solution-oriented language (boost score)
        solution_words = [
            'instead', 'alternatively', 'suggestion', 'recommend',
            'better', 'prefer', 'easier', 'simpler'
        ]

        solution_count = sum(1 for word in solution_words if word in content_lower)
        if solution_count > 0:
            score += min(5, solution_count * 2)

        # Check for question marks (indicates unclear request)
        question_count = content.count('?')
        if question_count > 3:
            score -= 3  # Too many questions, unclear what they want

        return max(0.0, min(25.0, score))

    def score_specificity(self, content: str) -> float:
        """
        Score feedback specificity (0-25).

        Evaluates:
        - Contains examples or concrete details
        - Mentions specific features/UI elements
        - Includes context (when, where, what)
        - Uses technical terms appropriately

        Args:
            content: Feedback text content

        Returns:
            Specificity score (0-25)
        """
        score = 10.0  # Base score

        content_lower = content.lower()

        # Check for specific indicators
        specific_indicators = [
            'when i', 'when you', 'if i', 'if you', 'after i',
            'for example', 'like', 'such as', 'specifically',
            'in particular', 'especially', 'button', 'page',
            'screen', 'menu', 'feature', 'option'
        ]

        indicator_count = sum(1 for phrase in specific_indicators if phrase in content_lower)
        score += min(10, indicator_count * 2)  # Up to +10 for specific language

        # Check for quoted text or code (highly specific)
        has_quotes = '"' in content or "'" in content
        has_backticks = '`' in content
        if has_quotes or has_backticks:
            score += 5

        # Check for URLs or paths (concrete references)
        has_url = bool(re.search(r'https?://', content_lower))
        has_path = bool(re.search(r'[/\\][\w/\\]+', content))
        if has_url or has_path:
            score += 3

        # Check for numbers/versions (specific details)
        has_numbers = bool(re.search(r'\d+', content))
        if has_numbers:
            score += 2

        # Penalize vague language
        vague_terms = [
            'something', 'somehow', 'maybe', 'perhaps', 'kind of',
            'sort of', 'whatever', 'thing', 'stuff'
        ]

        vague_count = sum(1 for term in vague_terms if term in content_lower)
        if vague_count > 2:
            score -= min(10, vague_count * 2)

        return max(0.0, min(25.0, score))

    def score_reproducibility(self, content: str) -> float:
        """
        Score feedback reproducibility (0-25).

        Evaluates:
        - Contains steps to reproduce
        - Defines scope/boundaries
        - Mentions conditions or triggers
        - Describes current vs. expected behavior

        Args:
            content: Feedback text content

        Returns:
            Reproducibility score (0-25)
        """
        score = 10.0  # Base score

        content_lower = content.lower()

        # Check for step indicators
        step_indicators = [
            'step', 'first', 'second', 'then', 'next', 'after',
            'before', 'finally', '1.', '2.', '1)', '2)'
        ]

        step_count = sum(1 for indicator in step_indicators if indicator in content_lower)
        if step_count >= 3:
            score += 10  # Clear steps provided
        elif step_count >= 1:
            score += 5

        # Check for behavior descriptions
        behavior_words = [
            'expected', 'actual', 'should', "shouldn't", 'does', "doesn't",
            'happens', 'occurs', 'results', 'outcome'
        ]

        behavior_count = sum(1 for word in behavior_words if word in content_lower)
        if behavior_count >= 2:
            score += 5

        # Check for condition/trigger words
        trigger_words = [
            'when', 'if', 'while', 'during', 'after', 'upon',
            'whenever', 'as soon as', 'in case'
        ]

        trigger_count = sum(1 for word in trigger_words if word in content_lower)
        if trigger_count >= 2:
            score += 5

        # Check for scope definition
        scope_words = [
            'always', 'never', 'sometimes', 'often', 'occasionally',
            'every time', 'only when', 'affects', 'impacts'
        ]

        scope_count = sum(1 for word in scope_words if word in content_lower)
        if scope_count >= 1:
            score += 5

        # Penalize if too vague to reproduce
        if len(content.split()) < 15:
            score -= 5  # Probably too short to describe reproduction

        return max(0.0, min(25.0, score))

    def calculate_quality_score(self, content: str) -> Dict[str, float]:
        """
        Calculate overall quality score for feedback.

        Args:
            content: Feedback text content

        Returns:
            Dict with component scores and total:
            {
                'clarity': float (0-25),
                'actionability': float (0-25),
                'specificity': float (0-25),
                'reproducibility': float (0-25),
                'total': float (0-100)
            }
        """
        if not content or not isinstance(content, str):
            return {
                'clarity': 0.0,
                'actionability': 0.0,
                'specificity': 0.0,
                'reproducibility': 0.0,
                'total': 0.0
            }

        # Calculate component scores
        clarity = self.score_clarity(content)
        actionability = self.score_actionability(content)
        specificity = self.score_specificity(content)
        reproducibility = self.score_reproducibility(content)

        # Total score
        total = clarity + actionability + specificity + reproducibility

        return {
            'clarity': round(clarity, 2),
            'actionability': round(actionability, 2),
            'specificity': round(specificity, 2),
            'reproducibility': round(reproducibility, 2),
            'total': round(total, 2)
        }

    def score_feedback_by_id(self, feedback_id: int) -> Optional[Dict[str, float]]:
        """
        Score a feedback item by ID and update database.

        Args:
            feedback_id: Database feedback ID

        Returns:
            Score dict if successful, None otherwise
        """
        try:
            with get_db() as db:
                feedback = db.query(Feedback).filter(Feedback.id == feedback_id).first()

                if not feedback:
                    logger.warning(f"Feedback {feedback_id} not found")
                    return None

                # Calculate quality score
                scores = self.calculate_quality_score(feedback.content)

                # Update feedback record
                feedback.quality_score = scores['total']
                feedback.updated_at = datetime.utcnow()
                db.commit()

                logger.info(
                    f"Scored feedback {feedback_id}: {scores['total']:.2f} "
                    f"(clarity={scores['clarity']:.2f}, "
                    f"actionability={scores['actionability']:.2f}, "
                    f"specificity={scores['specificity']:.2f}, "
                    f"reproducibility={scores['reproducibility']:.2f})"
                )

                return scores

        except Exception as e:
            logger.error(f"Failed to score feedback {feedback_id}: {e}")
            return None

    def batch_score_unscored_feedback(self, limit: int = 100) -> int:
        """
        Score all feedback items that don't have a quality_score yet.

        Args:
            limit: Maximum number of items to score in one batch

        Returns:
            Number of items scored
        """
        scored_count = 0

        try:
            with get_db() as db:
                # Find unscored feedback
                unscored = db.query(Feedback).filter(
                    Feedback.quality_score.is_(None)
                ).limit(limit).all()

                for feedback in unscored:
                    scores = self.calculate_quality_score(feedback.content)
                    feedback.quality_score = scores['total']
                    feedback.updated_at = datetime.utcnow()
                    scored_count += 1

                db.commit()

                logger.info(f"Batch scored {scored_count} feedback items")
                return scored_count

        except Exception as e:
            logger.error(f"Failed to batch score feedback: {e}")
            return scored_count


# Singleton instance
_feedback_scorer = None


def get_feedback_scorer() -> FeedbackScorer:
    """
    Get the global feedback scorer instance.

    Returns:
        FeedbackScorer instance
    """
    global _feedback_scorer
    if _feedback_scorer is None:
        _feedback_scorer = FeedbackScorer()
    return _feedback_scorer


def score_feedback(content: str) -> Dict[str, float]:
    """
    Convenience function to score feedback content.

    Args:
        content: Feedback text

    Returns:
        Score dict with components and total
    """
    scorer = get_feedback_scorer()
    return scorer.calculate_quality_score(content)
