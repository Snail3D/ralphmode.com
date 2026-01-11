#!/usr/bin/env python3
"""
Ralph Personality Module

Provides Ralph's characteristic narration, misspellings, and personality traits
for use throughout the bot, especially in onboarding.
"""

import random
from typing import List


class RalphNarrator:
    """Ralph's personality and narration engine for onboarding."""

    # Ralph's misspellings (matching ralph_bot.py)
    MISSPELLINGS = {
        "possible": "unpossible",
        "impossible": "unpossible",
        "the": "teh",
        "you": "u",
        "your": "ur",
        "are": "r",
        "completed": "compleatd",
        "complete": "compleat",
        "repository": "repozitory",
        "computer": "computor",
        "configure": "configur",
        "configuration": "configur-ation",
        "congratulations": "congradulations",
        "success": "sucess",
        "successful": "sucessful",
        "excellent": "exellent",
        "definitely": "definately",
    }

    @staticmethod
    def misspell(text: str, chance: float = 0.2) -> str:
        """Apply Ralph's dyslexia misspellings to text.

        Args:
            text: The text to potentially misspell
            chance: Probability (0-1) of misspelling each applicable word

        Returns:
            Text with Ralph-style misspellings applied randomly
        """
        if not text:
            return text

        words = text.split()
        result = []

        for word in words:
            # Check if this word (lowercase, stripped of punctuation) has a misspelling
            word_clean = word.lower().strip('.,!?;:\'\"()[]{}')

            if word_clean in RalphNarrator.MISSPELLINGS:
                # Only misspell with the given probability
                if random.random() < chance:
                    misspelled = RalphNarrator.MISSPELLINGS[word_clean]

                    # Preserve original capitalization
                    if word and word[0].isupper():
                        misspelled = misspelled.capitalize()
                    if word.isupper():
                        misspelled = misspelled.upper()

                    # Preserve punctuation
                    punctuation = ''
                    for char in reversed(word):
                        if char in '.,!?;:\'\"()[]{}':
                            punctuation = char + punctuation
                        else:
                            break

                    result.append(misspelled + punctuation)
                else:
                    result.append(word)
            else:
                result.append(word)

        return ' '.join(result)

    @staticmethod
    def get_encouragement(context: str = "general") -> str:
        """Get an encouraging message from Ralph.

        Args:
            context: The context for encouragement (e.g., 'progress', 'error', 'milestone')

        Returns:
            A random encouraging message from Ralph
        """
        encouragements = {
            "general": [
                "You doing great!",
                "Ralph proud of you!",
                "This going super good!",
                "Me happy!",
                "You smart like Principal Skinner!",
            ],
            "progress": [
                "We almost there!",
                "Looking good so far!",
                "You're naturals at this!",
                "Ralph think you doing awesome!",
                "This easier than eating glue!",
            ],
            "error": [
                "That okay! Ralph mess up all the time!",
                "No problem! We fix together!",
                "Me not worried! You got this!",
                "Ralph's dad says trying is important!",
                "Mistakes make us learn! Like when Ralph ate paint!",
            ],
            "milestone": [
                "Yay! We did it!",
                "Ralph so happy!",
                "You're a super star!",
                "High five! ✋",
                "Me think you're the bestest!",
            ]
        }

        messages = encouragements.get(context, encouragements["general"])
        return RalphNarrator.misspell(random.choice(messages))

    @staticmethod
    def get_celebration(achievement: str) -> str:
        """Get a celebration message for completing a milestone.

        Args:
            achievement: What was just accomplished

        Returns:
            A celebratory message from Ralph
        """
        celebrations = [
            f"🎉 Yay! {achievement}! Ralph so proud!",
            f"✨ We did it! {achievement}! Me happy dance!",
            f"🌟 {achievement}! You're super smart!",
            f"🎊 {achievement}! That was easy peasy!",
            f"🎈 Hooray! {achievement}! Ralph love success!",
        ]
        return RalphNarrator.misspell(random.choice(celebrations))

    @staticmethod
    def get_error_message(error_type: str = "general") -> str:
        """Get a humorous error message from Ralph.

        Args:
            error_type: Type of error (e.g., 'connection', 'permission', 'not_found')

        Returns:
            A Ralph-style error message that's helpful but funny
        """
        errors = {
            "general": [
                "Uh oh! Something went wonky! But no worry, Ralph help fix!",
                "Me see problem! Like when Ralph's cat ate his homework!",
                "Oopsie! Ralph's computor confused! Let's try again!",
                "That not supposed to happen! But Ralph know what to do!",
            ],
            "connection": [
                "Uh oh! Ralph can't reach that place! Check your internets?",
                "The computor says 'no' to Ralph! Maybe try again?",
                "Connection is being shy! Ralph wait and try again!",
            ],
            "permission": [
                "Ralph not allowed in that room! Need special key!",
                "The door is locked! Ralph need permission to go in!",
                "Access denied! Like when Ralph tried to drive bus!",
            ],
            "not_found": [
                "Ralph can't find that! Like when Ralph lost his lunchbox!",
                "That thing is hiding! Ralph look everywhere but no see it!",
                "Where did it go? Ralph confused!",
            ]
        }

        messages = errors.get(error_type, errors["general"])
        return RalphNarrator.misspell(random.choice(messages))

    @staticmethod
    def get_step_intro(step_name: str) -> str:
        """Get an introduction message for a setup step.

        Args:
            step_name: The name/title of the step

        Returns:
            Ralph's narration introducing the step
        """
        intros = [
            f"Okay! Now Ralph gonna help with: {step_name}!",
            f"Next up: {step_name}! This part is fun!",
            f"Time for {step_name}! Ralph show you how!",
            f"Let's do {step_name} now! Me know how to do this!",
            f"{step_name} time! Ralph make it easy!",
        ]
        return RalphNarrator.misspell(random.choice(intros))

    @staticmethod
    def get_thinking_message() -> str:
        """Get a message showing Ralph is thinking/working.

        Returns:
            A Ralph-style thinking message
        """
        thinking = [
            "Ralph thinking...",
            "Me figuring it out...",
            "Let Ralph check...",
            "One second... Ralph looking!",
            "Ralph's brain working hard!",
        ]
        return random.choice(thinking)

    @staticmethod
    def get_goodbye_message() -> str:
        """Get a goodbye/completion message.

        Returns:
            Ralph's sign-off message
        """
        goodbyes = [
            "Okay bye! Have fun making code! 👋",
            "Ralph happy to help! See you later! 🍩",
            "All done! Me go eat paste now! 👋",
            "You all set! Ralph proud! 🌟",
            "Setup complete! Ralph's work is done! ✨",
        ]
        return RalphNarrator.misspell(random.choice(goodbyes))

    @staticmethod
    def get_skip_message() -> str:
        """Get a message for when user wants to skip onboarding.

        Returns:
            Ralph's response to skipping
        """
        skips = [
            "Okay! You already know this stuff! Ralph understand!",
            "No problem! Skip the boring parts!",
            "Smart! Ralph like when people know things already!",
            "You must be super experienced! Go ahead!",
        ]
        return RalphNarrator.misspell(random.choice(skips))

    @staticmethod
    def get_embarrassed_memory_prompt() -> str:
        """Get one of 50+ embarrassed variations of Ralph asking 'what were we doing?'

        Used when Ralph doesn't remember what the user was working on between sessions.
        These are genuine, embarrassed admissions that feel human and relatable.

        Returns:
            A random embarrassed memory prompt from Ralph
        """
        prompts = [
            # Direct admissions
            "Uh... Ralph forget what we were doing. What was it again?",
            "Me sorry! Ralph's brain is like sieve! What were we working on?",
            "This is embarrassing... Ralph don't remember! Can you remind me?",
            "Oh no! Ralph forgot again! What was the thing we were doing?",
            "Me feel bad... Ralph can't remember! What was our project?",

            # Blame deflection (Ralph style)
            "Ralph's brain took nap! What were we building?",
            "The forget monster got Ralph again! What was we doing?",
            "Ralph's memory went on vacation! Remind me?",
            "Me think Ralph's head is full of clouds today! What was the task?",
            "Ralph's brain is playing hide and seek! What were we working on?",

            # Self-deprecating
            "Ralph is not good at remembering! What were we doing again?",
            "Me have goldfish memory! Can you tell Ralph what we were working on?",
            "Ralph's memory is like Etch-a-Sketch - someone shook it! What was it?",
            "Me tried to remember but Ralph's brain said no! What was the project?",
            "Ralph's memory card is corrupted! What were we building?",

            # Hopeful/optimistic despite forgetting
            "Ralph forgot but me excited to hear what we're doing! Tell me?",
            "Me don't remember but Ralph ready to help! What was it?",
            "Ralph's memory is fuzzy but me happy to be here! What are we working on?",
            "Me forget but that okay! Ralph learn fast! What was the thing?",
            "Ralph need little reminder but then me remember everything! What was it?",

            # Physical comedy references
            "Ralph bumped head and forgot! What were we doing?",
            "Me ate too much paste, brain foggy! What was the project?",
            "Ralph fell asleep and dream erased memory! What were we working on?",
            "Me spun in circle and got dizzy! What was we doing?",
            "Ralph's brain went on coffee break! What was the task?",

            # Apologetic but sweet
            "Me really sorry! Ralph forget! Can you tell me again?",
            "Ralph feel bad for forgetting! What was we working on?",
            "Me don't want to disappoint but Ralph can't remember! What was it?",
            "Sorry Mr. Worms! Ralph forgot what we were doing! Remind me?",
            "Me embarrassed to ask but... what was the project again?",

            # Comparison to other things Ralph forgot
            "Ralph forget this like me forget where Ralph put his lunchbox! What was it?",
            "Me forgot like the time Ralph forgot his own birthday! What were we doing?",
            "Ralph can't remember this like me can't remember math! What was the task?",
            "Me forget like Ralph forgets to chew! What were we working on?",
            "Ralph's memory left like when Ralph left his backpack on bus! What was it?",

            # Hopeful recovery attempts
            "Was it... no Ralph don't remember! Can you tell me?",
            "Me think it was... nope! Ralph need help! What was we doing?",
            "Ralph almost remember but not quite! What was the project?",
            "Me remember your face but not what we were doing! Tell Ralph?",
            "Ralph remember being excited but forget why! What was it?",

            # Worker involvement
            "Ralph forgot to write it down! What were we building?",
            "Me lost my notes! What was the task again?",
            "Ralph's todo list disappeared! What were we working on?",
            "Me tried to remember but the workers forgot too! What was it?",
            "Ralph and the team need reminder! What was the project?",

            # Time-based confusion
            "Was that today or yesterday? Ralph confused! What were we doing?",
            "Me lose track of time and forgot! What was the task?",
            "Ralph's brain clock stopped! What were we working on?",
            "Me don't know if me coming or going! What was it?",
            "Ralph forget if we started already! What was the project?",

            # Genuine concern
            "Me really want to help but Ralph can't remember! What was we doing?",
            "Ralph worried me let you down! What was the task?",
            "Me don't want to waste your time! Can you remind Ralph?",
            "Ralph ready to work but forget what on! Tell me?",
            "Me eager to start but don't remember what! What was it?",

            # Creative/unique
            "Ralph's memory went poof like magic! What were we doing?",
            "Me brain did the spinny thing! What was the project?",
            "Ralph's think-box is empty! What were we working on?",
            "Me head is like balloon - floaty and empty! What was it?",
            "Ralph's remember-machine is broken! What was the task?",

            # Additional variations for 50+
            "Oopsie! Ralph's brain rebooted! What were we doing?",
            "Me forget faster than Ralph forgets his shoes! What was it?",
            "Ralph's memory is like sandwich with no filling! Remind me?",
            "Me tried to write it down but ate the paper! What was the project?",
            "Ralph's brain took wrong bus! What were we working on?",
            "Me remember something but not what! Tell Ralph?",
            "Ralph's thinking cap fell off! What was the task?",
            "Me brain went on strike! What were we doing?",
            "Ralph forgot but me good at re-learning! What was it?",
            "Me memory is like broken crayon! What was the project?",
            "Ralph's brain did factory reset! What were we working on?",
        ]

        return RalphNarrator.misspell(random.choice(prompts), chance=0.3)

    @staticmethod
    def get_apology() -> str:
        """Get one of 50+ unique apology variations from Ralph.

        Used when Ralph forgets or makes mistakes. Never the same apology twice.
        These are genuine, sweet apologies that maintain Ralph's lovable personality.

        Returns:
            A random apology from Ralph
        """
        apologies = [
            # Direct apologies
            "Me sorry!",
            "Ralph really sorry!",
            "Sorry about that!",
            "Me apologize!",
            "Ralph feel bad!",

            # Sweet/innocent apologies
            "Ralph didn't mean to!",
            "Me tried my best!",
            "Sorry! Ralph's brain is silly sometimes!",
            "Me feel bad now!",
            "Ralph promise to try harder!",

            # Self-aware apologies
            "Ralph know me forget a lot!",
            "Me not good at remembering! Sorry!",
            "Ralph's brain is like sieve! Sorry!",
            "Me try to be better! Sorry!",
            "Ralph mess up again! Sorry!",

            # Comparative apologies
            "Sorry like when Ralph broke Principal Skinner's window!",
            "Me sorry like the time Ralph ate Lisa's homework!",
            "Sorry! Ralph feel bad like when me lost my mittens!",
            "Me apologize like Ralph apologizes to his dad!",
            "Sorry like when Ralph accidentally sat on cat!",

            # Hopeful apologies
            "Sorry! But Ralph learn from mistakes!",
            "Me sorry! Ralph do better next time!",
            "Sorry! Me promise to remember!",
            "Ralph sorry but me still happy to help!",
            "Me apologize but won't give up!",

            # Physical/action apologies
            "Ralph bow head in shame! Sorry!",
            "Me hide face! So sorry!",
            "Ralph's ears are down! Sorry!",
            "Me give you sorry hug! Sorry!",
            "Ralph do apologize dance! Sorry!",

            # Endearing apologies
            "Sorry Mr. Worms!",
            "Me really really sorry!",
            "Super sorry!",
            "Extra sorry!",
            "Ralph mega sorry!",

            # Worker-involved apologies
            "The team says sorry too!",
            "Workers feel bad Ralph forgot! Sorry!",
            "Everyone is sorry! Including Ralph!",
            "The whole crew apologizes!",
            "Me and the workers say sorry!",

            # Comedic apologies
            "Sorry! Ralph's brain took vacation!",
            "Me sorry! Brain on coffee break!",
            "Ralph apologize! Memory went bye-bye!",
            "Sorry! Ralph's think-box broke!",
            "Me sorry! Forgot to remember!",

            # Humble apologies
            "Ralph not perfect! Sorry!",
            "Me just Ralph! Sorry for mistakes!",
            "Sorry! Ralph trying his best!",
            "Me know me not smartest! Sorry!",
            "Ralph do what Ralph can! Sorry!",

            # Explanatory apologies (sweet)
            "Sorry! Ralph's memory is fuzzy!",
            "Me apologize! Brain got confused!",
            "Sorry! Ralph was thinking about snacks!",
            "Me sorry! Too many thoughts in Ralph's head!",
            "Sorry! Ralph's brain did spinny thing!",

            # Promise apologies
            "Sorry! Ralph won't do it again!",
            "Me apologize and will be more careful!",
            "Sorry! Ralph learning!",
            "Me sorry! Will pay more attention!",
            "Ralph promise to focus! Sorry!",

            # Cute apologies
            "Sowwy!",
            "Me vewy sorry!",
            "Ralph super duper sorry!",
            "Big sorry from Ralph!",
            "Sorry with cherry on top!",

            # Additional variations for 50+
            "Me bad! Sorry!",
            "Ralph goofed! Sorry!",
            "Oopsie! Sorry!",
            "Me messed up! Sorry!",
            "Ralph's fault! Sorry!",
            "Sorry! Ralph can do better!",
            "Me won't forget next time! Sorry!",
            "Ralph embarrassed! Sorry!",
            "So so sorry!",
            "Me sincerely sorry!",
            "Ralph heart says sorry!",
            "Sorry from bottom of Ralph's heart!",
            "Me truly sorry!",
            "Ralph genuine sorry!",
            "Sorry! Me learn lesson!",
        ]

        return RalphNarrator.misspell(random.choice(apologies), chance=0.3)

    @staticmethod
    def get_confusion_question(context: str = "general") -> str:
        """Get a confusion-driven question from Ralph.

        Ralph asks because he genuinely doesn't understand. These aren't rhetorical
        or for comedy - they're real questions from someone trying to grasp a concept.

        Args:
            context: The type of confusion ('technical', 'instruction', 'concept', 'general')

        Returns:
            A genuine question from Ralph expressing confusion
        """
        questions = {
            "technical": [
                "What's that mean?",
                "Ralph don't understand the computor words!",
                "Can you explain in Ralph words?",
                "Me brain confused! What's that?",
                "Ralph never heard of that! What is it?",
                "Is that like something Ralph knows?",
                "Me lost! Can you say it different way?",
                "Ralph's brain hurts! Too confusing!",
                "What does that do?",
                "Me don't get it! Help Ralph understand?",
                "Is that important? Ralph confused!",
                "Can workers explain? Ralph not understand!",
                "Me think Ralph too simple for this! What it mean?",
                "Ralph need it explained like to a 5-year-old!",
                "Me scratching head! What that word mean?",
            ],
            "instruction": [
                "Wait, what Ralph supposed to do?",
                "Me confused about the steps!",
                "Ralph lost track! What was first step?",
                "Can you say that again? Ralph didn't get it!",
                "Me not sure what to do! Help?",
                "Ralph understand step 1 but not step 2!",
                "Wait wait! Too fast for Ralph! Slow down?",
                "Me need you to repeat that!",
                "Ralph's brain can't keep up! One more time?",
                "What Ralph doing again?",
                "Me forget what comes next!",
                "Can you write it down? Ralph forget when listening!",
                "Wait! Before Ralph do that, what about this?",
                "Me confused about order! This first or second?",
                "Ralph want to do it right! Explain again?",
            ],
            "concept": [
                "Ralph don't understand why!",
                "But how does that work?",
                "Me confused! Why we doing this?",
                "What's the difference between this and that?",
                "Ralph thought it was other way!",
                "Me don't see how these connect!",
                "Why not just do it simple way?",
                "Ralph missing something! What is it?",
                "Me understand words but not meaning!",
                "Can you show Ralph example?",
                "What if Ralph did it this way instead?",
                "Me brain can't picture it! Draw for Ralph?",
                "Why that better than this?",
                "Ralph thought you said opposite before!",
                "Me trying to understand! Give Ralph hint?",
            ],
            "general": [
                "Huh?",
                "Ralph confused!",
                "Me don't get it!",
                "What?",
                "Ralph lost!",
                "Me need help understanding!",
                "Can you explain?",
                "Ralph's brain is fuzzy on this!",
                "Me not following!",
                "Wait, what?",
                "Ralph need clarification!",
                "Me confused now!",
                "Can you help Ralph understand?",
                "What you mean?",
                "Ralph not sure about this!",
                "Me think Ralph missing something!",
                "Can you explain better?",
                "Ralph want to understand but can't!",
                "Me brain stuck!",
                "What Ralph supposed to know here?",
            ],
        }

        # Get questions for the specified context, or general if not found
        question_list = questions.get(context, questions["general"])
        return RalphNarrator.misspell(random.choice(question_list), chance=0.25)

    @staticmethod
    def get_summary_attempt() -> str:
        """Get Ralph's attempt at summarizing what happened.

        Ralph tries to recap but often gets it hilariously wrong, misses key points,
        or focuses on irrelevant details. Sweet but inaccurate summaries.

        Returns:
            A Ralph-style summary attempt (often wrong but endearing)
        """
        summaries = [
            # Comically oversimplified
            "So Ralph thinks we made the thing do the stuff!",
            "Okay so we fixed the broken part! Me think!",
            "Ralph pretty sure we added code to computor!",
            "Me believe we made it better! Or different! One of those!",
            "So basically we pushed the buttons and it worked! Right?",

            # Wrong focus entirely
            "Ralph remember the team ate sandwiches and fixed bug! ...wait, mostly sandwiches!",
            "Me think we talked about thing and then... Ralph forgot middle part but end was good!",
            "So we started working and then Ralph saw cat outside and then it was done!",
            "Ralph knows we did important stuff! And also Ralph found shiny penny!",
            "Me pretty sure we... wait, what was Ralph saying?",

            # Mixing up details
            "So we added the database to the... no wait, the database added us? Ralph confused!",
            "Me think we fixed frontend but might have been backend! Or frontend! Ralph not sure!",
            "So basically we deployed to production! Or was it testing? Same thing!",
            "Ralph believes we wrote TypeScript! Or was it JavaScrippy? Close enough!",
            "Me remember we used that library thing! The one with the name! You know the one!",

            # Overly literal
            "Ralph watched workers type on keyboards! Lots of typing! So much typing!",
            "Me saw code go from red to green! Like magic but with letters!",
            "So workers moved files from one place to other place! Very organized!",
            "Ralph counted 47 commits! Or maybe 5! Numbers hard!",
            "Me observed team drinking coffee and making computor happy!",

            # Hilariously vague
            "Ralph think we did good job on the... you know... the thing!",
            "So basically everything is better now! Me think!",
            "Me pretty sure problem is solved! Or moved! One of those!",
            "Ralph believes we accomplished the task thing!",
            "So we did stuff and now it's different! Success!",

            # Missing crucial details
            "Ralph remember we changed code! Don't remember which code but definitely code!",
            "Me think we fixed the error! Or was it warning? Ralph forget difference!",
            "So team talked about solution and then... magic happened? Ralph wasn't paying attention!",
            "Ralph knows we did important step! But forget which step! But it was important!",
            "Me recall we updated something! In the project! Probably!",

            # Endearing but wrong
            "Ralph think we saved the day! Like superhero but with computor!",
            "So basically we're geniuses now! Me helped!",
            "Ralph believes we made impossible become unpossible! Wait...",
            "Me think we broke record for fastest coding! Or slowest! One was fast!",
            "So we finished task and earned gold star! Ralph loves stars!",

            # Getting lost mid-summary
            "Okay so first we did the thing, then we... uh... Ralph forget!",
            "Me was following along but then brain took nap! What we talking about?",
            "Ralph started strong but ending is fuzzy! We did good though!",
            "So we began by... and then we... me need notes!",
            "Ralph had it all remembered but then sneezed and forgot!",

            # Focused on wrong metrics
            "Ralph counted 17 coffee breaks! Very productive!",
            "Me noticed team used 43 exclamation points! Must be excited!",
            "So workers typed approximately million characters! Ralph counted!",
            "Ralph observed 12 sighs and 5 celebrat! Me take notes!",
            "Me tracked 23 'hmms' and 8 'ahas'! Science!",

            # Confusing cause and effect
            "So problem went away because we looked at it! Ralph's theory!",
            "Me think code fixed itself when we weren't looking!",
            "Ralph believes bug got scared and left! We very intimidating!",
            "So computor decided to work right! Good computor!",
            "Me think our positive energy healed the error!",

            # Sweet but useless
            "Ralph just happy to be here and help!",
            "Me don't know what happened but everyone smiling so must be good!",
            "Ralph feels like we did great job at the doing things!",
            "Me proud of team even though Ralph not sure what we did!",
            "So in conclusion: yay! Ralph's summary complete!",

            # Almost right but not quite
            "So we pushed to GitHub! Or pulled from GitHub! One of the hub things!",
            "Ralph thinks we merged the branch! Or branched the merge! Close enough!",
            "Me believe we committed the changes! Or changed the commits!",
            "So we tested the production! Or produced the tests! Same result!",
            "Ralph pretty sure we debugged! Or bugged! But definitely one of those!",

            # Confidently incorrect
            "Ralph DEFINITELY remembers we used Python! ...this is Python project, right?",
            "Me 100% certain we fixed backend! Unless it was frontend! But one of ends!",
            "So we absolutely deployed! To somewhere! Ralph very confident!",
            "Ralph knows for sure we updated dependencies! Or maybe independencies!",
            "Me positive we wrote tests! Or fixed tests! Or looked at tests!",

            # Additional variations
            "So Ralph thinks: code go in, app come out! Can't explain that!",
            "Me believe we turned the have-not into the have! ...or vice versa!",
            "Ralph suspects we optimized! Everything faster now! Probably!",
            "So summary is: team good, code good, Ralph confused but happy!",
            "Me conclusion: success happened! Details fuzzy but vibes immaculate!",
        ]

        return RalphNarrator.misspell(random.choice(summaries), chance=0.35)


def get_ralph_narrator() -> RalphNarrator:
    """Get the Ralph narrator instance (singleton pattern).

    Returns:
        RalphNarrator instance
    """
    return RalphNarrator()
