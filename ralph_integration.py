from conversation_ending import ConversationEndingDetector

class RalphBot:
    def __init__(self):
        # Initialize detector with specific requirements for this bot instance
        self.ending_detector = ConversationEndingDetector(
            required_slots=['issue_type', 'account_id'],
            max_turns=15
        )
        self.context = {
            'filled_slots': {},
            'turn_count': 0,
            'last_user_intent': '',
            'sentiment_score': 0,
            'repetition_count': 0
        }

    def handle_input(self, user_input, nlp_analysis):
        """
        Main integration point for the existing system.
        """
        # Update context based on NLP analysis
        self.context['turn_count'] += 1
        self.context['last_user_intent'] = nlp_analysis.get('intent', '')
        self.context['sentiment_score'] = nlp_analysis.get('sentiment', 0)
        
        # Update slots
        if nlp_analysis.get('entities'):
            self.context['filled_slots'].update(nlp_analysis['entities'])

        # Check for conversation ending
        decision = self.ending_detector.evaluate(self.context)

        if decision['should_end']:
            return self._generate_ending_response(decision)
        
        return self._generate_continuation_response()

    def _generate_ending_response(self, decision):
        return f"I believe we have what we need ({decision['reason']}). Can I help with anything else today?"

    def _generate_continuation_response(self):
        return "I see. Please go on."