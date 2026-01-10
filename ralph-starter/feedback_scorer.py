#!/usr/bin/env python3
"""
QS-001 & QS-002: Feedback Quality Scoring Module for Ralph Mode Bot

QS-001 - Rule-based scoring (0-100) based on:
- Clarity (0-25): Is it clearly written?
- Actionability (0-25): Can we do something with this?
- Specificity (0-25): Does it include details, examples?
- Reproducibility (0-25): Can we reproduce/understand scope?

QS-002 - LLM-based assessment:
- Extract structured data (problem, expected, actual, steps)
- Generate clarifying questions for low-quality feedback
- Enhanced quality scoring from LLM analysis

This is part of the RLHF Self-Building System where feedback quality
determines priority and implementation order.
"""

import os
import json
import logging
import re
import requests
from typing import Dict, Optional, List, Tuple
from datetime import datetime

from database import get_db, Feedback, InputValidator

# QS-003: Import user quality tracker
try:
    from user_quality_tracker import update_user_quality_score
    USER_QUALITY_TRACKER_AVAILABLE = True
except ImportError:
    USER_QUALITY_TRACKER_AVAILABLE = False
    def update_user_quality_score(user_id: int): return None
    logging.warning("QS-003: User quality tracker not available")

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

    def __init__(self, groq_api_key: Optional[str] = None):
        """
        Initialize the feedback scorer.

        Args:
            groq_api_key: Optional Groq API key for LLM assessment (QS-002)
        """
        self.groq_api_key = groq_api_key or os.environ.get("GROQ_API_KEY")
        self.groq_api_url = "https://api.groq.com/openai/v1/chat/completions"

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
                user_id = feedback.user_id  # Save for later use
                db.commit()

                logger.info(
                    f"Scored feedback {feedback_id}: {scores['total']:.2f} "
                    f"(clarity={scores['clarity']:.2f}, "
                    f"actionability={scores['actionability']:.2f}, "
                    f"specificity={scores['specificity']:.2f}, "
                    f"reproducibility={scores['reproducibility']:.2f})"
                )

                # QS-003: Update user quality score after scoring feedback
                if USER_QUALITY_TRACKER_AVAILABLE and user_id:
                    try:
                        new_user_score = update_user_quality_score(user_id)
                        if new_user_score is not None:
                            logger.info(f"Updated user {user_id} quality score to {new_user_score}")
                    except Exception as e:
                        logger.error(f"Failed to update user quality score: {e}")

                return scores

        except Exception as e:
            logger.error(f"Failed to score feedback {feedback_id}: {e}")
            return None

    def assess_with_llm(self, content: str, feedback_type: str = "general") -> Optional[Dict]:
        """
        QS-002: Use LLM to assess feedback quality and extract structured data.

        Args:
            content: Feedback text content
            feedback_type: Type of feedback (bug, feature, improvement, praise)

        Returns:
            Dict with structured data:
            {
                'problem': str,
                'expected': str (for bugs),
                'actual': str (for bugs),
                'steps': List[str] (for bugs),
                'use_case': str (for features),
                'scope': str,
                'quality_assessment': str,
                'extracted_score': float (0-100),
                'needs_clarification': bool,
                'clarifying_questions': List[str]
            }
        """
        if not self.groq_api_key:
            logger.warning("QS-002: Groq API key not available, skipping LLM assessment")
            return None

        # Build prompt based on feedback type
        if feedback_type in ["bug", "issue", "problem"]:
            system_prompt = """You are a feedback analyzer for a software development bot.
Analyze the bug report and extract structured information.

Return ONLY valid JSON (no markdown, no explanations) with this exact structure:
{
  "problem": "concise problem statement",
  "expected": "expected behavior",
  "actual": "actual behavior",
  "steps": ["step 1", "step 2", "step 3"],
  "scope": "when this occurs (always, sometimes, specific conditions)",
  "quality_assessment": "brief quality assessment",
  "extracted_score": 75.5,
  "needs_clarification": false,
  "clarifying_questions": ["question 1 if needed"]
}

Quality scoring guide:
- 80-100: Clear, actionable, reproducible with steps
- 60-79: Good description but missing some details
- 40-59: Vague, needs clarification
- 0-39: Unusable, major information missing"""
        else:
            system_prompt = """You are a feedback analyzer for a software development bot.
Analyze the feature request/improvement and extract structured information.

Return ONLY valid JSON (no markdown, no explanations) with this exact structure:
{
  "problem": "what problem does this solve",
  "use_case": "how would this be used",
  "scope": "who needs this / what scenarios",
  "quality_assessment": "brief quality assessment",
  "extracted_score": 75.5,
  "needs_clarification": false,
  "clarifying_questions": ["question 1 if needed"]
}

Quality scoring guide:
- 80-100: Clear use case, specific request, actionable
- 60-79: Good idea but needs more detail on implementation
- 40-59: Vague request, unclear value
- 0-39: Unusable, not enough information"""

        try:
            response = requests.post(
                self.groq_api_url,
                headers={
                    "Authorization": f"Bearer {self.groq_api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "llama-3.3-70b-versatile",
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": f"Analyze this feedback:\n\n{content}"}
                    ],
                    "temperature": 0.3,
                    "max_tokens": 1000
                },
                timeout=10
            )

            if response.status_code == 200:
                result = response.json()
                assistant_message = result['choices'][0]['message']['content']

                # Parse JSON response
                # Remove markdown code blocks if present
                assistant_message = assistant_message.strip()
                if assistant_message.startswith('```'):
                    # Remove ```json and closing ```
                    lines = assistant_message.split('\n')
                    assistant_message = '\n'.join(lines[1:-1])

                structured_data = json.loads(assistant_message)
                logger.info(f"QS-002: LLM assessment completed, score: {structured_data.get('extracted_score', 0)}")
                return structured_data
            else:
                logger.error(f"QS-002: Groq API error: {response.status_code} - {response.text}")
                return None

        except requests.exceptions.Timeout:
            logger.error("QS-002: Groq API timeout")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"QS-002: Failed to parse LLM response as JSON: {e}")
            return None
        except Exception as e:
            logger.error(f"QS-002: LLM assessment failed: {e}")
            return None

    def generate_clarifying_questions(self, content: str, feedback_type: str = "general") -> List[str]:
        """
        QS-002: Generate clarifying questions for low-quality feedback.

        Args:
            content: Feedback text content
            feedback_type: Type of feedback

        Returns:
            List of clarifying questions
        """
        # First try LLM-based questions
        assessment = self.assess_with_llm(content, feedback_type)
        if assessment and assessment.get('clarifying_questions'):
            return assessment['clarifying_questions']

        # Fallback to rule-based questions
        questions = []

        # Check what's missing
        content_lower = content.lower()

        if feedback_type in ["bug", "issue"]:
            # Missing steps
            if not any(word in content_lower for word in ['step', 'first', 'then', '1.', '2.']):
                questions.append("Can you describe the exact steps to reproduce this issue?")

            # Missing expected behavior
            if not any(word in content_lower for word in ['expected', 'should']):
                questions.append("What did you expect to happen?")

            # Missing actual behavior
            if not any(word in content_lower for word in ['actual', 'instead', 'but']):
                questions.append("What actually happened?")

            # Missing frequency
            if not any(word in content_lower for word in ['always', 'sometimes', 'every', 'never']):
                questions.append("Does this happen every time, or only in certain conditions?")

        elif feedback_type == "feature":
            # Missing use case
            if not any(word in content_lower for word in ['when', 'if', 'use case', 'scenario']):
                questions.append("Can you describe a specific scenario where you would use this feature?")

            # Missing why
            if not any(word in content_lower for word in ['because', 'so that', 'would help', 'need']):
                questions.append("What problem would this solve for you?")

            # Missing scope
            if not any(word in content_lower for word in ['who', 'users', 'everyone', 'people']):
                questions.append("Who would benefit from this feature?")

        # Generic questions for vague feedback
        if len(content.split()) < 15:
            questions.append("Could you provide more details about what you're trying to do?")

        return questions[:3]  # Max 3 questions

    def calculate_enhanced_quality_score(
        self,
        content: str,
        feedback_type: str = "general",
        use_llm: bool = True
    ) -> Dict[str, any]:
        """
        Calculate enhanced quality score combining rule-based (QS-001) and LLM (QS-002).

        Args:
            content: Feedback text content
            feedback_type: Type of feedback
            use_llm: Whether to use LLM assessment (default True)

        Returns:
            Dict with scores, structured data, and clarifying questions
        """
        # QS-001: Rule-based scoring
        rule_based_scores = self.calculate_quality_score(content)

        result = {
            'rule_based': rule_based_scores,
            'llm_assessment': None,
            'final_score': rule_based_scores['total'],
            'needs_clarification': rule_based_scores['total'] < 40,
            'clarifying_questions': []
        }

        # QS-002: LLM assessment (if enabled and API key available)
        if use_llm and self.groq_api_key:
            llm_assessment = self.assess_with_llm(content, feedback_type)
            if llm_assessment:
                result['llm_assessment'] = llm_assessment

                # Combine scores (70% LLM, 30% rule-based for balance)
                llm_score = llm_assessment.get('extracted_score', rule_based_scores['total'])
                result['final_score'] = round(0.7 * llm_score + 0.3 * rule_based_scores['total'], 2)

                # Use LLM's clarification assessment
                result['needs_clarification'] = llm_assessment.get('needs_clarification', result['needs_clarification'])
                result['clarifying_questions'] = llm_assessment.get('clarifying_questions', [])

        # Generate clarifying questions if needed
        if result['needs_clarification'] and not result['clarifying_questions']:
            result['clarifying_questions'] = self.generate_clarifying_questions(content, feedback_type)

        return result

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


def get_feedback_scorer(groq_api_key: Optional[str] = None) -> FeedbackScorer:
    """
    Get the global feedback scorer instance.

    Args:
        groq_api_key: Optional Groq API key for LLM assessment

    Returns:
        FeedbackScorer instance
    """
    global _feedback_scorer
    if _feedback_scorer is None:
        _feedback_scorer = FeedbackScorer(groq_api_key)
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
