class Character:
    def __init__(self, name):
        self.name = name
        self.traits = []

    def add_trait(self, trait):
        self.traits.append(trait)

    def react(self, stimulus):
        reactions = []
        for trait in self.traits:
            if hasattr(trait, 'handle_stimulus'):
                reaction = trait.handle_stimulus(stimulus, self)
                if reaction:
                    reactions.append(reaction)
        return reactions