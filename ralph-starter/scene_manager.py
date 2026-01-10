#!/usr/bin/env python3
"""
Scene Manager - SS-001: Opening Scene Generation

Generates atmospheric opening scenes for Ralph Mode sessions.
Each scene is unique, sets the mood, and introduces workers naturally.
"""

import random
from datetime import datetime
from typing import Dict, List, Any


class SceneManager:
    """Manages atmospheric scene generation for session openings."""

    # Weather options with matching moods
    WEATHER = {
        "sunny": {
            "descriptions": [
                "Sunlight streams through dusty windows",
                "Golden morning light fills the office",
                "Bright sunshine makes the coffee stains more visible",
                "A perfect sunny day outside. Inside? Same fluorescent lights as always"
            ],
            "mood": "energetic"
        },
        "rainy": {
            "descriptions": [
                "Rain patters against the windows",
                "Gray clouds hang low. Perfect coding weather",
                "The steady drumming of rain on the roof",
                "Drizzle outside. Someone's wet shoes squeak on the floor"
            ],
            "mood": "cozy"
        },
        "overcast": {
            "descriptions": [
                "Overcast skies match the mood of Monday",
                "Gray morning. The fluorescent lights hum louder somehow",
                "Clouds obscure the sun. Nobody notices",
                "Another gray day in the office"
            ],
            "mood": "neutral"
        },
        "stormy": {
            "descriptions": [
                "Thunder rumbles in the distance",
                "Storm clouds gathering. The power flickers once",
                "Wind rattles the windows. Someone mutters 'great, no pressure'",
                "Lightning flashes. The coffee maker beeps ominously"
            ],
            "mood": "intense"
        },
        "foggy": {
            "descriptions": [
                "Thick fog presses against the windows",
                "Morning fog hasn't lifted. Can barely see across the parking lot",
                "The world outside is gray. The world inside is fluorescent",
                "Fog rolls past the windows like the code we're about to debug"
            ],
            "mood": "mysterious"
        }
    }

    # Time of day options with enhanced atmospheric details
    TIMES = {
        "early_morning": {
            "times": ["6:47 AM", "7:03 AM", "7:21 AM", "7:58 AM"],
            "descriptions": [
                "The office is eerily quiet",
                "Coffee machine is still warming up",
                "The parking lot is mostly empty",
                "Even the pigeons haven't woken up yet",
                "First one in. The silence is actually kinda nice",
                "Dawn light just starting to filter through the windows"
            ],
            "energy": "slow_start",
            "worker_mood": "groggy but focused"
        },
        "morning": {
            "times": ["8:34 AM", "9:07 AM", "9:42 AM", "9:58 AM"],
            "descriptions": [
                "The daily standup is in 20 minutes. Nobody's prepared",
                "Keyboards are starting to clatter",
                "Someone microwaves fish. Again",
                "The coffee pot is already half empty",
                "Workers trickle in with their morning routines",
                "Slack notifications are starting to pile up"
            ],
            "energy": "picking_up",
            "worker_mood": "caffeinated and ready"
        },
        "late_morning": {
            "times": ["10:17 AM", "10:49 AM", "11:23 AM", "11:55 AM"],
            "descriptions": [
                "The morning energy is fading. Lunch can't come soon enough",
                "Three browser tabs of Stack Overflow already open",
                "Someone's on their fourth coffee",
                "The午前会議 ended 10 minutes ago. Nobody moved yet",
                "Productive energy fills the air. Or maybe that's just the HVAC",
                "Stomachs start rumbling. Lunch is on everyone's mind"
            ],
            "energy": "productive",
            "worker_mood": "focused but hungry"
        },
        "afternoon": {
            "times": ["1:08 PM", "1:43 PM", "2:17 PM", "2:54 PM"],
            "descriptions": [
                "Post-lunch food coma is setting in",
                "Half the team is in meetings. The other half pretends to be",
                "Someone's watching YouTube with headphones",
                "The afternoon slump is real",
                "Settling into steady work. The day has found its rhythm",
                "Coffee runs are starting again. Second wind incoming"
            ],
            "energy": "settling_in",
            "worker_mood": "steady grind"
        },
        "late_afternoon": {
            "times": ["3:29 PM", "4:02 PM", "4:38 PM", "4:56 PM"],
            "descriptions": [
                "End of day approaching. People are getting antsy",
                "The parking lot is emptier already",
                "Someone asks 'is this urgent or can it wait til tomorrow?'",
                "The energy picks up slightly. Home time is near",
                "Last push before wrapping up. Or starting crunch mode",
                "Eyes on the clock. But the work isn't done yet"
            ],
            "energy": "winding_down",
            "worker_mood": "tired but pushing through"
        },
        "evening": {
            "times": ["6:12 PM", "7:23 PM", "8:41 PM", "9:07 PM"],
            "descriptions": [
                "The cleaning crew arrives. We're still here",
                "Pizza boxes and empty energy drinks litter the desks",
                "The only sounds are mechanical keyboards and distant sirens",
                "Everyone else went home. We're in crunch mode",
                "Night shift mode activated. This is where real work happens",
                "Tired but focused. The deadline doesn't care what time it is"
            ],
            "energy": "crunch_mode",
            "worker_mood": "exhausted but dedicated"
        },
        "night": {
            "times": ["10:34 PM", "11:18 PM", "12:03 AM", "1:27 AM"],
            "descriptions": [
                "The office is dark except for monitor glow",
                "Someone's asleep on the couch in the break room",
                "The coffee is old but we're drinking it anyway",
                "Peak productivity hours. Or delirium. Hard to tell",
                "Skeleton crew. The dedicated few. The slightly insane",
                "The city sleeps. We debug. This is the way"
            ],
            "energy": "skeleton_crew",
            "worker_mood": "delirious but determined"
        }
    }

    # Office atmosphere elements
    OFFICE_DETAILS = [
        "The coffee machine gurgles ominously",
        "Someone left a half-eaten bagel on the counter",
        "The whiteboard still has last week's架构 diagram",
        "A stack of sticky notes threatens to avalanche",
        "The Slack notification sound echoes from somewhere",
        "Somebody's mechanical keyboard is particularly loud today",
        "The air conditioning is either too hot or too cold, never just right",
        "A lonely plant in the corner looks like it needs water",
        "Yesterday's pizza box is still on the table",
        "The motivational poster about 'teamwork' is slightly crooked",
        "Someone's standing desk is stuck halfway up",
        "The recycling bin is full of energy drink cans",
        "A rubber duck sits on a monitor, ready to debug",
        "Post-it notes cover one entire wall in rainbow chaos"
    ]

    # Worker arrival patterns
    WORKER_ARRIVALS = {
        "Stool": [
            "Stool strolls in with AirPods and an iced latte",
            "Stool appears, tapping away at their phone",
            "Stool slides in, coffee in one hand, phone in the other",
            "Stool arrives looking surprisingly awake"
        ],
        "Gomer": [
            "Gomer shuffles in carrying a box of donuts",
            "Gomer arrives with a yawn and a dopey smile",
            "Gomer lumbers in, already thinking about lunch",
            "Gomer enters humming some TV show theme"
        ],
        "Mona": [
            "Mona walks in precisely on time, laptop already open",
            "Mona arrives with three notebooks and an agenda",
            "Mona enters, somehow looking both energized and exasperated",
            "Mona strides in, already analyzing the day ahead"
        ],
        "Gus": [
            "Gus trudges in gripping coffee like his life depends on it",
            "Gus arrives muttering something about 'kids these days'",
            "Gus enters with the weariness of a thousand sprints",
            "Gus shuffles in, his coffee mug says 'I've seen things'"
        ],
        "Ralph": [
            "Ralph bounds in with a huge smile and mismatched socks",
            "Ralph arrives with enthusiastic energy and a backwards cap",
            "Ralph skips in humming, pleased about something",
            "Ralph enters grinning, proud to be the manager"
        ]
    }

    def generate_opening_scene(self, project_name: str = None, boss_tone: str = None) -> Dict[str, Any]:
        """
        Generate a unique opening scene for a session.

        Args:
            project_name: Optional project name to reference
            boss_tone: TL-001: Optional tone from voice analysis (angry, happy, urgent, etc.)

        Returns:
            Dictionary with scene elements:
            - full_text: Complete scene description
            - weather: Weather condition
            - time: Time of day
            - mood: Overall mood/atmosphere
            - worker_order: List of workers in arrival order
        """
        # TL-001: Pick weather based on boss tone if provided
        if boss_tone:
            # Map tone to weather/mood
            tone_to_weather = {
                'angry': 'stormy',
                'frustrated': 'stormy',
                'urgent': 'stormy',
                'happy': 'sunny',
                'excited': 'sunny',
                'pleased': 'sunny',
                'calm': 'overcast',
                'neutral': 'overcast',
                'questioning': 'foggy',
                'concerned': 'rainy'
            }
            weather_key = tone_to_weather.get(boss_tone.lower(), random.choice(list(self.WEATHER.keys())))
        else:
            weather_key = random.choice(list(self.WEATHER.keys()))

        weather_info = self.WEATHER[weather_key]
        weather_desc = random.choice(weather_info["descriptions"])
        mood = weather_info["mood"]

        # Pick time of day based on actual current time (or random if you prefer)
        current_hour = datetime.now().hour
        if current_hour < 7:
            time_key = "early_morning"
        elif current_hour < 10:
            time_key = "morning"
        elif current_hour < 12:
            time_key = "late_morning"
        elif current_hour < 15:
            time_key = "afternoon"
        elif current_hour < 17:
            time_key = "late_afternoon"
        elif current_hour < 21:
            time_key = "evening"
        else:
            time_key = "night"

        time_info = self.TIMES[time_key]
        time_str = random.choice(time_info["times"])
        time_context = random.choice(time_info["descriptions"])

        # Pick office details (1-2)
        office_details = random.sample(self.OFFICE_DETAILS, random.randint(1, 2))

        # Generate worker arrival order (randomize but keep Ralph for later)
        workers = ["Stool", "Gomer", "Mona", "Gus"]
        random.shuffle(workers)

        # Build the scene
        scene_parts = []

        # Opening: time and weather
        scene_parts.append(f"**{time_str}**")
        scene_parts.append(f"{weather_desc}.")

        # Office atmosphere
        scene_parts.append(f"{time_context}.")

        # Office details
        for detail in office_details:
            scene_parts.append(detail + ".")

        # The office opens
        if project_name:
            scene_parts.append(f"\n*Ralph Mode HQ. A new project awaits: {project_name}.*")
        else:
            scene_parts.append(f"\n*Ralph Mode HQ. Another day, another codebase.*")

        scene_parts.append("\nThe lights flicker on. The team trickles in...")

        full_text = " ".join(scene_parts)

        return {
            "full_text": full_text,
            "weather": weather_key,
            "time": time_key,
            "time_str": time_str,
            "mood": mood,
            "energy": time_info.get("energy", "neutral"),
            "worker_mood": time_info.get("worker_mood", "working"),
            "worker_order": workers + ["Ralph"],  # Ralph always arrives last (he's the manager)
            "worker_arrivals": self.WORKER_ARRIVALS
        }

    def get_worker_arrival(self, worker_name: str) -> str:
        """Get a random arrival message for a specific worker."""
        arrivals = self.WORKER_ARRIVALS.get(worker_name, [f"{worker_name} arrives"])
        return random.choice(arrivals)

    def get_time_of_day_context(self) -> Dict[str, str]:
        """
        Get current time of day context for use in responses.

        Returns:
            Dictionary with time_key, energy, and worker_mood
        """
        current_hour = datetime.now().hour
        if current_hour < 7:
            time_key = "early_morning"
        elif current_hour < 10:
            time_key = "morning"
        elif current_hour < 12:
            time_key = "late_morning"
        elif current_hour < 15:
            time_key = "afternoon"
        elif current_hour < 17:
            time_key = "late_afternoon"
        elif current_hour < 21:
            time_key = "evening"
        else:
            time_key = "night"

        time_info = self.TIMES[time_key]

        return {
            "time_key": time_key,
            "energy": time_info.get("energy", "neutral"),
            "worker_mood": time_info.get("worker_mood", "working"),
            "description": random.choice(time_info["descriptions"])
        }


# Global instance for easy import
_scene_manager = SceneManager()


def generate_opening_scene(project_name: str = None, boss_tone: str = None) -> Dict[str, Any]:
    """Generate an opening scene (convenience function)."""
    return _scene_manager.generate_opening_scene(project_name, boss_tone)


def get_worker_arrival(worker_name: str) -> str:
    """Get worker arrival text (convenience function)."""
    return _scene_manager.get_worker_arrival(worker_name)


def get_time_of_day_context() -> Dict[str, str]:
    """Get current time of day context (convenience function)."""
    return _scene_manager.get_time_of_day_context()


if __name__ == "__main__":
    # Test the scene generator
    print("Testing Scene Manager...\n")
    print("=" * 60)

    for i in range(3):
        print(f"\n### Scene {i+1} ###\n")
        scene = generate_opening_scene("TestProject")
        print(scene["full_text"])
        print(f"\nMood: {scene['mood']}")
        print(f"Worker order: {', '.join(scene['worker_order'])}")
        print("\n" + "=" * 60)
