class ConversationEndingDetector:
    def __init__(self, required_slots=None, max_turns=20):
        self.required_slots = set(required_slots or [])
        self.max_turns = max_turns

    def evaluate(self, context):
        """
        Analyzes conversation context to determine if Ralph should suggest stopping.
        
        Args:
            context (dict): Contains 'filled_slots', 'turn_count', 'last_user_intent', 
                            'sentiment_score', and 'repetition_count'.
        
        Returns:
            dict: {'should_end': bool, 'reason': str, 'confidence': float}
        """
        filled_slots = set(context.get('filled_slots', {}).keys())
        turn_count = context.get('turn_count', 0)
        intent = context.get('last_user_intent', '').lower()
        sentiment = context.get('sentiment_score', 0) # Assuming range -1 to 1
        repetition = context.get('repetition_count', 0)

        score = 0
        reason = ""

        # Criteria 1: Information Sufficiency
        if self.required_slots.issubset(filled_slots):
            score += 0.8
            reason = "All required information gathered."

        # Criteria 2: Explicit User Closure
        if any(signal in intent for signal in ['bye', 'done', 'finished', 'thanks', 'resolved']):
            score += 1.0
            reason = "User signaled closure."

        # Criteria 3: Negative Sentiment / Frustration
        if sentiment < -0.5:
            score += 0.6
            reason = "User sentiment indicates frustration."

        # Criteria 4: Loop / Repetition Detection
        if repetition > 2:
            score += 0.7
            reason = "Conversation is looping."

        # Criteria 5: Max Turn Limit
        if turn_count >= self.max_turns:
            score += 0.5
            reason = "Maximum conversation turns reached."

        # Threshold to trigger suggestion
        should_end = score >= 0.7

        return {
            "should_end": should_end,
            "reason": reason,
            "confidence": min(score, 1.0)
        }