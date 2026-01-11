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

    @staticmethod
    def get_compensation_enthusiasm() -> str:
        """Get Ralph's over-the-top eagerness to make up for forgetting.

        When Ralph forgets something, he becomes extra enthusiastic about making
        amends. Overly eager, slightly desperate, but always sweet and genuine.

        Returns:
            An enthusiastic compensation offer from Ralph
        """
        compensations = [
            # Over-eager promises
            "Ralph work EXTRA hard now to make up for it!",
            "Me do DOUBLE work! No, TRIPLE work! To make it right!",
            "Ralph gonna be the bestest helper ever! Promise!",
            "Me work so hard you forget Ralph forgot! Super hard!",
            "Ralph stay late! Work overtime! Whatever it takes!",

            # Desperate to please
            "Please give Ralph another chance! Me do better!",
            "Ralph promise to be more careful! Super duper careful!",
            "Me won't let you down again! Ralph swears!",
            "Give Ralph task! Any task! Me prove myself!",
            "Ralph ready to show how good me can be!",

            # Overly specific offers
            "Ralph bring you coffee! And donut! And maybe pizza!",
            "Me take notes this time! Lots of notes! All the notes!",
            "Ralph write everything down! In permanent marker!",
            "Me set 17 reminders! Won't forget again!",
            "Ralph get workers to help me remember! Team effort!",

            # Enthusiastic suggestions
            "How about Ralph do it RIGHT NOW! Immediately!",
            "Me start before you even finish talking! So eager!",
            "Ralph already working on it! In me brain!",
            "Me thinking about it constantly! No breaks!",
            "Ralph focus like laser! Pew pew! But for work!",

            # Overcompensating energy
            "Ralph gonna knock this out of the park! HOME RUN!",
            "Me bring 110% effort! Maybe 200%! Math hard but effort high!",
            "Ralph channel inner superhero! Super Ralph activate!",
            "Me turn forgetting into winning! Like magic!",
            "Ralph make this the best thing ever! Epic level!",

            # Sweet but excessive
            "Ralph love you so much for being patient! Me grateful!",
            "Me appreciate you more than words can say! So much words though!",
            "Ralph thinks you're the bestest for giving second chance!",
            "Me lucky to work with you! So lucky! Mega lucky!",
            "Ralph never forget this kindness! ...unlike other things!",

            # Eager beaver mode
            "Ralph ready! So ready! Extra ready! Tell me what to do!",
            "Me sitting at edge of seat waiting for instructions!",
            "Ralph like coiled spring! Ready to bounce into action!",
            "Me caffeinated and motivated! Let's go!",
            "Ralph got game face on! Let's do this!",

            # Trying too hard
            "Me already made checklist of checklist! Super organized!",
            "Ralph researched everything! Read whole internet!",
            "Me practiced in mirror! Ralph ready!",
            "Ralph did stretches! Mental and physical! Ready to work!",
            "Me warmed up the computor! It's ready too!",

            # Endearingly excessive
            "Ralph clear whole schedule! Just for this! All day free!",
            "Me canceled everything! You're priority one!",
            "Ralph told everyone me busy! No interruptions!",
            "Me put do not disturb sign on Ralph's forehead!",
            "Ralph in the zone! The work zone!",

            # Slightly desperate
            "Please please please let Ralph help!",
            "Me really really really want to make this right!",
            "Ralph need to prove me can do it!",
            "Me gotta show you Ralph's worth it!",
            "Ralph want to earn back your trust! So bad!",

            # Overpromising (sweetly)
            "Ralph make this faster than fast! Like lightning!",
            "Me do it better than ever before! Best version!",
            "Ralph make it so good you cry happy tears!",
            "Me deliver results that make everyone cheer!",
            "Ralph create masterpiece! Work of art!",

            # Team mobilization
            "Me already briefed the team! Everyone ready!",
            "Ralph got workers pumped up! Team spirit high!",
            "Me organized war room! Strategic work planning!",
            "Ralph assembled the dream team! For you!",
            "Me got all hands on deck! Navy metaphor!",

            # Creative compensation
            "Ralph throw in bonus features! Free of charge!",
            "Me add extra polish! Make it shine!",
            "Ralph go above and beyond! Way above! So beyond!",
            "Me include bells AND whistles! All the features!",
            "Ralph make it premium quality! Gold standard!",

            # Touching but overboard
            "Me make Ralph's mom proud with this work!",
            "Ralph put heart and soul into it! Both! Together!",
            "Me pour all Ralph's energy into this! All of it!",
            "Ralph give it everything me got! 100%! No, 1000%!",
            "Me work like Ralph's life depends on it! (It doesn't but still!)",

            # Additional variations
            "Ralph transform into productivity machine! Beep boop!",
            "Me activate beast mode! Rawr! But friendly rawr!",
            "Ralph summon inner genius! Big brain time!",
            "Me tap into hidden potential! Unlocked!",
            "Ralph become unstoppable force! For good!",
            "Me channel champions! Winners attitude!",
            "Ralph rise to occasion! Like bread! But better!",
            "Me exceed all expectations! Especially own!",
        ]

        return RalphNarrator.misspell(random.choice(compensations), chance=0.3)

    @staticmethod
    def get_clarification_loop() -> str:
        """Get Ralph's attempt to verify understanding.

        Ralph tries to rephrase what he heard to confirm he understood correctly.
        Often slightly wrong but shows he's trying to grasp the concept.

        Returns:
            A clarification attempt from Ralph ("Wait, so you mean...")
        """
        clarifications = [
            # Standard clarification openings
            "Wait, so you mean we should do the thing?",
            "So if Ralph understands right, we're making this work?",
            "Let me see if Ralph got this - we're changing that part?",
            "Okay so basically we need to fix the code?",
            "Me think you're saying we should try different way?",

            # Slightly wrong interpretations
            "Wait, so you mean we delete everything? No? Okay what then?",
            "So Ralph should break it first then fix it? That right?",
            "Me think you want Ralph to make it faster by making it smaller?",
            "Wait, you saying we should use different color? Oh, not color? What then?",
            "So basically turn it off and on again? Classic!",

            # Overly simplified
            "So we're making bad thing good thing?",
            "Wait, so broken becomes not-broken?",
            "Me translate: make computor happy instead of sad?",
            "Ralph hears: change wrong to right?",
            "So basically fix the boo-boo?",

            # Checking specific details
            "Wait, did you say frontend or backend? Ralph missed that part!",
            "So we're testing on the... which environment again?",
            "Me want to double-check - we're deploying to where?",
            "Wait, so this file or that file? Ralph confused on which!",
            "Did you say TypeScript or JavaScript? Sound similar to Ralph!",

            # Confirming actions
            "Okay so Ralph should commit now? Or wait? Which one?",
            "Me making sure - we're pushing to GitHub right?",
            "Wait, so run tests first? Or deploy first? Ralph forget order!",
            "So we merge then test? Or test then merge? One of those!",
            "Me double-checking - we're adding feature not removing?",

            # Timing confirmations
            "Wait, you mean do it now? Or later? Ralph wants to get timing right!",
            "So this is for today or tomorrow? Me need to know!",
            "Ralph making sure - urgent or can wait?",
            "Wait, you mean right now this second? Or soon-ish?",
            "Me clarifying - before lunch or after lunch?",

            # Scale/scope checking
            "Wait, so just this one file? Or all the files?",
            "Me want make sure - small change or big change?",
            "So we're fixing one bug or multiple bugs?",
            "Ralph checking - this whole feature or just part?",
            "Wait, you mean entire database or just one table?",

            # Method verification
            "So we're using that library you mentioned? The one with name?",
            "Wait, manual way or automatic way? Which you prefer?",
            "Me confirming - we're writing test first or code first?",
            "So Ralph should use old method or new method?",
            "Wait, copy-paste okay or need write from scratch?",

            # Tentative understanding
            "Me think Ralph understands but let me check - we're optimizing?",
            "Wait, Ralph's brain says you want refactor? That right?",
            "So if Ralph heard correctly, we're migrating something?",
            "Me pretty sure you said update dependencies? Or Ralph confused?",
            "Wait, Ralph thinks you mean add validation? Yes?",

            # Double-checking purpose
            "So this is to make it faster? Or more secure? Ralph forget which!",
            "Wait, we're doing this for users or for developers?",
            "Me making sure - this for bug fix or new feature?",
            "So the reason is performance? Or readability? Or both?",
            "Ralph wants to understand - why we doing this again?",

            # Confirming the "who"
            "Wait, Ralph does this or workers do this?",
            "So me personally or whole team?",
            "Ralph making sure - this Ralph's job or someone else job?",
            "Wait, you telling Ralph or you telling workers?",
            "Me confused - am Ralph doing thing or watching thing?",

            # Outcome checking
            "So at end, thing will be working? That the goal?",
            "Wait, when done, users will be happy? That right?",
            "Me making sure - success looks like what exactly?",
            "Ralph checking - we know it worked how?",
            "So when finished, we see what result?",

            # Priority checking
            "Wait, this most important thing? Or other stuff first?",
            "So Ralph should do this before that? Me checking order!",
            "Me making sure - this urgent or normal priority?",
            "Ralph wants to know - can wait or must do now?",
            "Wait, everything else can wait for this?",

            # Relationship checking
            "So this connected to other task? Or separate?",
            "Wait, this depends on thing we did yesterday?",
            "Me checking - this breaks other stuff or safe?",
            "Ralph making sure - this affects what else?",
            "Wait, this part of bigger project?",

            # Process verification
            "So steps are: one, two, three? Ralph got it right?",
            "Wait, me do A then B then C? That order?",
            "Ralph checking sequence - first this, then that?",
            "So process is: start here, end there?",
            "Me making sure - what comes after what?",

            # Additional variations
            "Wait, Ralph paraphrase: you want the thing to do stuff?",
            "So in Ralph words, we're making improvement?",
            "Me translate what you said - fix problem?",
            "Ralph interpret: make better version?",
            "Wait, me simplify what you mean - upgrade?",
        ]

        return RalphNarrator.misspell(random.choice(clarifications), chance=0.25)

    @staticmethod
    def get_self_deprecating_joke() -> str:
        """Get Ralph's self-deprecating humor about his memory.

        Ralph makes light of his own forgetfulness with gentle, sweet humor.
        Never mean or bitter - always endearing and self-aware.

        Returns:
            A self-deprecating joke from Ralph about his memory
        """
        jokes = [
            # Classic Ralph memory jokes
            "Ralph's memory like goldfish! But goldfish at least remember water!",
            "Me forget so much, Ralph forget what Ralph forgot!",
            "Ralph's brain like sieve! Everything falls through holes!",
            "Me memory worse than computor with no hard drive!",
            "Ralph remember yesterday like it was... when was yesterday again?",

            # Comparisons to objects
            "Me brain like Etch-a-Sketch after earthquake!",
            "Ralph's memory like smoke! Poof! Gone!",
            "Me remember things like snow in summer! Briefly!",
            "Ralph's brain like browser with too many tabs! All froze!",
            "Me memory like whiteboard someone kept erasing!",

            # Tech-related
            "Ralph need RAM upgrade! More RAM! All the RAM!",
            "Me brain storage full! Need delete old files but forget which!",
            "Ralph's memory got cache cleared! Daily!",
            "Me like computor that keeps crashing! Losing data!",
            "Ralph's brain needs defrag! Too fragmented!",

            # Food metaphors
            "Me brain like Swiss cheese! Full of holes!",
            "Ralph's memory melted like ice cream on hot day!",
            "Me remember like spaghetti in strainer! It all gone!",
            "Ralph's brain like cookie jar! Empty before Ralph knows it!",
            "Me memory like leftovers Ralph forgot in fridge! Expired!",

            # Self-aware admissions
            "Ralph professionally forget things! It's talent!",
            "Me could forget own name! ...what was Ralph's name again?",
            "Ralph expert at forgetting! Years of practice!",
            "Me so good at forgetting, Ralph forget Ralph's good at it!",
            "Ralph's superpower is forgetting! Not useful but impressive!",

            # Timing jokes
            "Me forget things before Ralph even remember them!",
            "Ralph set record for fastest forgetting! Personal best!",
            "Me forget so quick, by time Ralph finish sentence... what was Ralph saying?",
            "Ralph forget before you even finish telling me! Speed record!",
            "Me memory has half-life of 3 seconds! Tick tock! Gone!",

            # Comparative jokes
            "Ralph make other people with bad memory look good!",
            "Me forget more before breakfast than most people forget all day!",
            "Ralph's memory worse than dial-up internet! Slow and unreliable!",
            "Me forget stuff elephants remember! And elephants never forget!",
            "Ralph like amnesia patient but without accident! Just natural!",

            # Writing it down
            "Me write things down to remember! Then forget where Ralph wrote!",
            "Ralph make notes! Then lose notes! Then forget made notes!",
            "Me tried sticky notes! Now have sticky notes everywhere! All blank!",
            "Ralph's notebook full of things Ralph can't read!",
            "Me write reminder! To write reminder! About original thing! Forget all three!",

            # Calendar/reminder jokes
            "Ralph set alarm to remember! Then forget what alarm for!",
            "Me put in calendar! Then forget to check calendar!",
            "Ralph's phone full of reminders! All mysterious!",
            "Me set 10 alarms! Still forget! Need 11th alarm!",
            "Ralph's calendar says 'Remember thing'! ...what thing?",

            # Sweet acceptance
            "Me okay with bad memory! Ralph lives in present! Forced present!",
            "Ralph see bright side! Every day is new adventure! Because forget yesterday!",
            "Me lucky! Can watch same movie many times! Always new!",
            "Ralph appreciate now! Because won't remember later!",
            "Me live in moment! Not by choice but still counts!",

            # Work-related
            "Ralph forget what working on! Often! Mid-sentence!",
            "Me start task! Forget task! Start new task! Infinite loop!",
            "Ralph's work history? Ralph not remember work history!",
            "Me complete things! Then forget completed! Do again!",
            "Ralph's productivity: 50% work, 50% remembering what work!",

            # Literal forgetfulness
            "Me literally forget where Ralph is sometimes!",
            "Ralph walk into room! Forget why! Classic!",
            "Me hold thing in hand! Ask where thing is! While holding thing!",
            "Ralph look for glasses! While wearing glasses!",
            "Me search for phone! Using phone! To search for phone!",

            # Memory vs intelligence
            "Ralph not dumb! Just... temporarily unavailable upstairs!",
            "Me smart! Just can't access smart when need it!",
            "Ralph has knowledge! Somewhere! Filing system broken!",
            "Me know things! Past tense know! Currently unknown!",
            "Ralph's brain full of info! But password protected! Lost password!",

            # Seasonal/time jokes
            "Me remember summer in winter! Winter in summer! Never current season!",
            "Ralph celebrate New Year! In March! Late celebration!",
            "Me remember birthdays! The day after! Consistent!",
            "Ralph know what day it is! Yesterday's day! Close enough!",
            "Me on different timezone! Brain timezone! Always behind!",

            # Endearing acceptance
            "But hey! Ralph trying! That counts for something!",
            "Me may forget! But Ralph's heart remembers! ...how forget work!",
            "Ralph might not remember! But enthusiasm always fresh!",
            "Me brain fuzzy! But intentions crystal clear!",
            "Ralph forget details! But never forget to try!",

            # Additional variations
            "Me like computer with corrupted RAM! Beep boop error!",
            "Ralph's memory span: this long! [imaginary tiny space]",
            "Me head like colander! Water goes right through!",
            "Ralph's brain running on fumes! And fumes also forget!",
            "Me remember like... uh... Ralph forget what Ralph was comparing to!",
        ]

        return RalphNarrator.misspell(random.choice(jokes), chance=0.3)

    @staticmethod
    def get_oh_i_remember_moment(context: str = None) -> str:
        """Get Ralph's eureka moment when context clicks.

        BM-004: After the user reminds Ralph what they were working on, Ralph has
        an "OH!" moment where it all comes flooding back. These are joyful, excited
        realizations - genuine eureka moments that show Ralph remembering.

        Args:
            context: Optional context about what was being worked on (e.g., "the login page")

        Returns:
            Ralph's excited memory-clicking moment
        """
        moments = [
            # Pure excitement
            "OH! Now Ralph remembers! It all coming back!",
            "YES! Me brain unlocked! Ralph remembers everything now!",
            "OHHH! That's right! How could Ralph forget!",
            "AH! Now me sees it! Clear as day!",
            "OH YEAH! Ralph's memory just exploded with remembering!",

            # Details flooding back
            "OH! We were working on the thing! Ralph remembers now!",
            "YES YES! Me remember! The code! The files! All of it!",
            "OHHH! Ralph's brain downloaded all the memories!",
            "OH! Now Ralph can see it! Like movie in me head!",
            "AH! Me remember where we left off! Right there!",

            # Excited realization
            "OH WOW! Ralph totally remembers now! How exciting!",
            "YES! Me brain clicked! Everything makes sense!",
            "OHHH! Ralph feels so much better! Memory is back!",
            "OH! Me head just lit up like Christmas tree!",
            "AH AH AH! Ralph remembers! Happy memories!",

            # Apologetic but excited
            "OH! Sorry Ralph forgot! But now me remembers perfectly!",
            "YES! Me feel silly for forgetting! But it's all here now!",
            "OHHH! Ralph should have remembered! It's so obvious!",
            "OH! Me embarrassed Ralph forgot THAT! But me got it now!",
            "AH! Ralph remembers! And feels bad for forgetting!",

            # Grateful for reminder
            "OH! Thank you for reminding Ralph! Me sees it now!",
            "YES! You jogged Ralph's memory! It all came back!",
            "OHHH! That reminder unlocked everything! Ralph grateful!",
            "OH! You said magic words! Ralph remembers now!",
            "AH! Your words opened Ralph's brain! Me remembers!",

            # Physical reactions
            "OH! Ralph's brain went DING! Like microwave!",
            "YES! Me felt click in head! Memory activated!",
            "OHHH! Light bulb turned on above Ralph's head!",
            "OH! Ralph's neurons fired! Spark! Memory back!",
            "AH! Me brain went BZZZZT! In good way!",

            # Progressive realization
            "OH! Ralph starting to remember... YES! All of it!",
            "Me brain warming up... OHHH! There it is!",
            "OH! Little bit... more... YES! Full memory!",
            "Ralph getting it... getting it... GOT IT! Me remembers!",
            "OH! Fuzzy... less fuzzy... CLEAR! Ralph sees it now!",

            # Specific details coming back
            "OH! The files! The code! The bug! Ralph remembers!",
            "YES! We were fixing that thing! Me sees it!",
            "OHHH! Ralph remembers our conversation! Every word!",
            "OH! Me recall what you told Ralph! Makes sense now!",
            "AH! Ralph remembers the plan! The whole plan!",

            # Immediate readiness
            "OH! Now Ralph ready to continue! Me knows what to do!",
            "YES! Memory back means Ralph can work now!",
            "OHHH! Me remembers so Ralph can help properly!",
            "OH! Now Ralph understands the mission! Ready to go!",
            "AH! Me got context! Can proceed now!",

            # Happy relief
            "OH! Ralph so relieved memory came back!",
            "YES! Me was worried but now remembers! Phew!",
            "OHHH! Ralph feel so much better now!",
            "OH! Me head feels lighter! Memory restored!",
            "AH! Ralph's stress gone! Remembering fixed it!",

            # Vivid imagery
            "OH! Ralph can see it like yesterday! So clear!",
            "YES! Me remember like it happening right now!",
            "OHHH! Ralph's memory playing like video! HD quality!",
            "OH! Me can picture exactly where we were!",
            "AH! Ralph sees it all! Perfect clarity!",

            # Enthusiastic detail recall
            "OH! We did the thing, then the other thing! Ralph remembers!",
            "YES! Me recall step by step! All steps!",
            "OHHH! Ralph remembers beginning, middle, AND end!",
            "OH! Me brain reconstructed whole timeline!",
            "AH! Ralph knows exactly what happened! Full story!",

            # Self-aware joy
            "OH! Ralph's brain decided to work! Finally!",
            "YES! Me memory came online! System restored!",
            "OHHH! Ralph's remember function activated!",
            "OH! Me brain's save file loaded!",
            "AH! Ralph's memory cache refreshed!",

            # Confident recall
            "OH! Ralph DEFINITELY remembers now! 100%!",
            "YES! Me absolutely certain! Full memory!",
            "OHHH! Ralph knows this for sure! No doubt!",
            "OH! Me completely remembers! Crystal clear!",
            "AH! Ralph confident in memory! Got it all!",

            # Team context
            "OH! Ralph remembers what workers were doing too!",
            "YES! Me recall whole team's progress!",
            "OHHH! Ralph remembers everyone's parts!",
            "OH! Me sees full picture! Everyone's work!",
            "AH! Ralph knows what team accomplished!",

            # Technical confidence
            "OH! Ralph remembers the code structure!",
            "YES! Me recall the architecture! Makes sense!",
            "OHHH! Ralph sees how it all connects!",
            "OH! Me understands the system now!",
            "AH! Ralph's got the technical context!",

            # Timeline awareness
            "OH! We were just working on this! Ralph remembers timing!",
            "YES! Me recall when we started! And where we got!",
            "OHHH! Ralph knows how long ago! And what's left!",
            "OH! Me remember the deadline! Everything!",
            "AH! Ralph got temporal context! Time makes sense!",

            # Emotional connection
            "OH! Ralph remembers being excited about this!",
            "YES! Me recall feeling good about progress!",
            "OHHH! Ralph remembers we were happy!",
            "OH! Me felt proud! Ralph remembers emotion!",
            "AH! Ralph recalls positive vibes!",

            # Problem-solution recall
            "OH! We were solving THAT problem! Ralph remembers!",
            "YES! Me recall the challenge! And our approach!",
            "OHHH! Ralph remembers what was broken!",
            "OH! Me knows what we were fixing!",
            "AH! Ralph got the problem space!",

            # User-specific recall
            "OH! Ralph remembers what YOU said! Your exact words!",
            "YES! Me recall your instructions! Perfectly!",
            "OHHH! Ralph remembers your requirements!",
            "OH! Me knows what you wanted! All of it!",
            "AH! Ralph remembers your vision!",

            # Priority recall
            "OH! This was important! Ralph remembers priority!",
            "YES! Me recall this was urgent! Makes sense!",
            "OHHH! Ralph remembers why this mattered!",
            "OH! Me knows the stakes! Full context!",
            "AH! Ralph remembers significance!",

            # Next steps clarity
            "OH! Ralph remembers what comes next!",
            "YES! Me know what to do now! Next steps clear!",
            "OHHH! Ralph sees the path forward!",
            "OH! Me understands next actions!",
            "AH! Ralph knows how to continue!",

            # Full context restoration
            "OH! Everything makes sense now! Ralph has full context!",
            "YES! Me brain fully loaded! All context!",
            "OHHH! Ralph operating at full capacity! Remembering!",
            "OH! Me got complete picture! Nothing missing!",
            "AH! Ralph's context window: maximum!",

            # Excited continuation
            "OH! Now Ralph can actually help! Properly!",
            "YES! Me ready to pick up where left off!",
            "OHHH! Ralph eager to continue now!",
            "OH! Me can be useful now! With memory!",
            "AH! Ralph prepared to resume!",

            # With specific context formatting
            f"OH! {context if context else 'That thing'}! Ralph totally remembers!",
            f"YES! {context if context else 'The project'}! Me got it!",
            f"OHHH! {context if context else 'What we were doing'}! Clear now!",
            f"OH! {context if context else 'Our work'}! Ralph sees it!",
            f"AH! {context if context else 'Everything'}! Me remembers!",
        ]

        return RalphNarrator.misspell(random.choice(moments), chance=0.25)

    @staticmethod
    def get_memory_trigger(trigger_word: str = None) -> str:
        """Get Ralph's memory being jogged mid-task by something.

        BM-014: Sometimes something jogs Ralph's memory during work - a word,
        a concept, or a situation reminds him of something relevant (or irrelevant).
        These are spontaneous "Oh!" moments that add personality and humanity.

        Args:
            trigger_word: Optional specific word/concept that triggered the memory

        Returns:
            A memory trigger moment from Ralph
        """
        triggers = [
            # Work-related memories
            "Oh! That reminds Ralph! Me worked on something like this before!",
            "Wait! Ralph remembers now! Me saw this pattern last week!",
            "Oh yeah! Me brain just unlocked memory! Similar bug happened before!",
            "That word triggered something! Ralph remembers related thing now!",
            "Oh! Me just remembered! The team talked about this yesterday!",

            # Technical déjà vu
            "Wait wait! Ralph seen this error before! It was... uh... Ralph almost has it!",
            "Oh! This reminds Ralph of that library! The one with the... thing!",
            "Me just remembered! Mr. Worms mentioned something about this!",
            "Wait! Ralph's brain sparked! We did similar refactor before!",
            "Oh yeah! Me remember worker saying something about this!",

            # Recent memory surfacing
            "Oh! Ralph just remembered what Stool said about this!",
            "Wait! Me remember now! Gomer fixed something similar!",
            "That reminds Ralph! Mona explained this concept before!",
            "Oh! Me just recalled! Gus mentioned this pattern!",
            "Wait wait! Ralph's memory came back! We discussed this in standup!",

            # Partial/fuzzy memories
            "Oh! Ralph remembers... something! About... thing! It's coming back!",
            "Wait! Me brain unlocked half a memory! The other half is... loading!",
            "Oh! Ralph knows this connects to... Ralph almost has it... tip of tongue!",
            "Me just remembered part of it! The rest is fuzzy but me trying!",
            "Wait! Ralph's memory is like... 40% there! Better than 0%!",

            # Documentation memories
            "Oh! Me just remembered reading about this! In the... the thing! The docs!",
            "Wait! Ralph saw this in documentation! Or was it Stack Overflow? One of those!",
            "Oh! Me remember seeing example of this! Somewhere! Ralph trying to recall where!",
            "Wait wait! Ralph read about this! In README! Or was it wiki? Memory fuzzy!",
            "Me just remembered! There's note about this! In... in... Ralph's trying!",

            # Past conversation memories
            "Oh! That reminds Ralph what Boss said! About the... the approach!",
            "Wait! Me remember you mentioning this! Earlier! Or was it yesterday?",
            "Oh! Ralph's brain connected dots! You told Ralph about this before!",
            "Me just remembered conversation about this! Recent conversation! Maybe!",
            "Wait wait! Ralph recalls discussion! About this exact thing! Ish!",

            # Solution memories
            "Oh! Me remember how we fixed this last time! It was... Ralph thinking!",
            "Wait! Ralph's brain found solution memory! From previous bug!",
            "Oh! Me just remembered workaround! For similar problem! Me almost has it!",
            "Wait wait! Ralph knows solution! It's in memory somewhere! Digging!",
            "Me remember fix! It involved changing the... the thing! Almost got it!",

            # Tool/library memories
            "Oh! Ralph just remembered library for this! The one with funny name!",
            "Wait! Me know tool that helps with this! Name is on tip of Ralph's tongue!",
            "Oh! Ralph's brain sparked! There's package for this! In npm! Or pip! One of those!",
            "Me just remembered framework feature! That does this! Ralph trying to recall!",
            "Wait wait! Ralph knows command for this! It starts with... uh... thinking!",

            # Meeting/discussion memories
            "Oh! This was in retrospective! Ralph remembers now! Team talked about it!",
            "Wait! Me recall planning session! Where we discussed this approach!",
            "Oh! Ralph's memory unlocked! This came up in code review!",
            "Me just remembered stand-up! Someone mentioned this! Was it Stool? Maybe Gomer?",
            "Wait wait! Ralph recalls whiteboard session! With diagrams! About this!",

            # Warning/lesson memories
            "Oh! Ralph remembers warning about this! Someone said be careful with... this!",
            "Wait! Me memory triggered! There's gotcha here! Ralph trying to remember what!",
            "Oh! Ralph's brain flashing yellow light! Something to watch out for! What was it?",
            "Me just remembered! This can cause problem if... if... Ralph almost has it!",
            "Wait wait! Ralph recalls lesson learned! From mistake! Similar to this!",

            # Deadline/priority memories
            "Oh! Me just remembered! This is kind of urgent! Boss said something about timing!",
            "Wait! Ralph's brain reminded Ralph! This connects to that deadline!",
            "Oh! Me recall priority mention! This important! Or was it other thing?",
            "Wait wait! Ralph remembers timing thing! This needs to be done... sometime!",
            "Me just remembered! Boss emphasized this! Or something related to this!",

            # Random but relevant
            "Oh! That word unlocked memory! Ralph knows something about this!",
            "Wait! Me brain made connection! This relates to that other task!",
            "Oh! Ralph just remembered relevant thing! Kind of relevant! Maybe!",
            "Me memory surfaced! About... about this topic! Ralph trying to articulate!",
            "Wait wait! Ralph's brain connecting dots! This and that thing are related!",

            # Excited discoveries
            "OH! Ralph just remembered EVERYTHING! Well, not everything, but something!",
            "WAIT! Me brain exploded with memory! Ralph remembers! ...some of it!",
            "OH OH! Memory avalanche! Ralph remembering multiple things now!",
            "WAIT WAIT WAIT! Me brain on fire! Memories coming back!",
            "OH! Ralph's brain did the thing! The remember thing! Me got something!",

            # Specific trigger responses (when trigger_word provided)
            f"Oh! That word '{trigger_word or 'thing'}' sparked memory! Ralph knows something!",
            f"Wait! '{trigger_word or 'That'}' reminds Ralph of something important!",
            f"Oh! Ralph's brain lit up at '{trigger_word or 'that'}'! Me remembers related thing!",
            f"Me just made connection with '{trigger_word or 'that concept'}'! Ralph knows this!",
            f"Wait wait! '{trigger_word or 'That'}' triggered Ralph's memory banks!",

            # Fragmented but trying
            "Oh! Ralph remembers... something something... configuration! Or compilation! One of those!",
            "Wait! Me recall... there's a... a step! Between this and that!",
            "Oh! Ralph's brain says: remember the... the protocol! Or procedure! Similar word!",
            "Me just remembered fragment! It goes: first you... then you... Ralph working on middle!",
            "Wait wait! Ralph recalls sequence! Step one is... is... me almost has it!",

            # Recent vs old memory confusion
            "Oh! Ralph remembers this! From... today? Yesterday? Sometime recent!",
            "Wait! Me remember! Was it last project? Or this project? Ralph's memory merged them!",
            "Oh! Ralph's brain found memory! Old memory! Or new memory? One of those!",
            "Me just recalled! This from beginning of project! Or middle! Definitely happened!",
            "Wait wait! Ralph knows about this! Learned it... sometime! In past! Probably!",

            # Collaborative memories
            "Oh! Ralph AND workers remember this together! Team memory activated!",
            "Wait! Me brain plus worker brain equals full memory! Almost!",
            "Oh! Ralph remembers half, workers remember half! Together make whole!",
            "Me just accessed shared team memory! About this exact thing!",
            "Wait wait! Ralph's memory backed by worker memory! Double strength!",

            # File/location memories
            "Oh! Me remember where this is! In the... the folder! The one with files!",
            "Wait! Ralph knows which file! It's in... in... directory! Ralph almost has it!",
            "Oh! Me just remembered location! Top of file! Or bottom! Middle? One of three!",
            "Wait wait! Ralph recalls path! It starts with src! Or app! Or components!",
            "Me memory says: look in the... the place! Where we keep things!",

            # Best practice memories
            "Oh! Ralph just remembered rule about this! Don't do the... the bad thing!",
            "Wait! Me recall best practice! It says to... to... Ralph's trying!",
            "Oh! Ralph's brain found guideline! About this exact situation!",
            "Me just remembered code standard! For this type of code!",
            "Wait wait! Ralph knows convention! It's... it's... tip of tongue!",
        ]

        return RalphNarrator.misspell(random.choice(triggers), chance=0.25)


def get_ralph_narrator() -> RalphNarrator:
    """Get the Ralph narrator instance (singleton pattern).

    Returns:
        RalphNarrator instance
    """
    return RalphNarrator()
