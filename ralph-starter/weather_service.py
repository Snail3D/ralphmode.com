#!/usr/bin/env python3
"""
Weather Service - SS-002: Weather Integration

Fetches real weather data when user location is configured, otherwise generates
atmospheric weather. Weather affects scene mood and atmosphere.

Usage:
    from weather_service import get_weather, is_location_configured

    if is_location_configured():
        weather = get_weather()  # Real weather
    else:
        weather = get_weather()  # Generated atmospheric weather
"""

import os
import logging
import requests
import random
from typing import Dict, Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# Weather API key from environment (OpenWeather API)
WEATHER_API_KEY = os.getenv('OPENWEATHER_API_KEY')

# User location from environment (city name or lat,lon)
USER_LOCATION = os.getenv('USER_LOCATION')

# Cache duration (don't fetch weather more than once every 30 minutes)
WEATHER_CACHE_DURATION = timedelta(minutes=30)

# Weather cache (in-memory for now, could use Redis/file later)
_weather_cache: Dict[str, any] = {
    'weather_data': None,
    'last_fetch': None
}


class WeatherService:
    """Manages weather data fetching and caching."""

    # Map OpenWeather condition codes to our scene weather types
    # https://openweathermap.org/weather-conditions
    CONDITION_MAP = {
        # Thunderstorm (200-232)
        200: 'stormy', 201: 'stormy', 202: 'stormy', 210: 'stormy',
        211: 'stormy', 212: 'stormy', 221: 'stormy', 230: 'stormy',
        231: 'stormy', 232: 'stormy',
        # Drizzle (300-321)
        300: 'rainy', 301: 'rainy', 302: 'rainy', 310: 'rainy',
        311: 'rainy', 312: 'rainy', 313: 'rainy', 314: 'rainy',
        321: 'rainy',
        # Rain (500-531)
        500: 'rainy', 501: 'rainy', 502: 'rainy', 503: 'rainy',
        504: 'rainy', 511: 'rainy', 520: 'rainy', 521: 'rainy',
        522: 'rainy', 531: 'rainy',
        # Snow (600-622)
        600: 'rainy', 601: 'rainy', 602: 'rainy', 611: 'rainy',
        612: 'rainy', 613: 'rainy', 615: 'rainy', 616: 'rainy',
        620: 'rainy', 621: 'rainy', 622: 'rainy',
        # Atmosphere (701-781) - Fog, Mist, Haze
        701: 'foggy', 711: 'foggy', 721: 'foggy', 731: 'foggy',
        741: 'foggy', 751: 'foggy', 761: 'foggy', 762: 'foggy',
        771: 'foggy', 781: 'stormy',  # Tornado
        # Clear (800)
        800: 'sunny',
        # Clouds (801-804)
        801: 'sunny',      # Few clouds
        802: 'overcast',   # Scattered clouds
        803: 'overcast',   # Broken clouds
        804: 'overcast',   # Overcast
    }

    def __init__(self):
        """Initialize weather service."""
        self.api_key = WEATHER_API_KEY
        self.location = USER_LOCATION

    def is_location_configured(self) -> bool:
        """Check if user location is configured."""
        return bool(self.location)

    def is_api_configured(self) -> bool:
        """Check if weather API is configured."""
        return bool(self.api_key and self.location)

    def _fetch_from_api(self) -> Optional[Dict]:
        """
        Fetch weather from OpenWeather API.

        Returns:
            Dict with weather data or None if failed
        """
        if not self.is_api_configured():
            logger.warning("SS-002: Weather API not configured (missing API key or location)")
            return None

        try:
            # Build API URL
            base_url = "https://api.openweathermap.org/data/2.5/weather"
            params = {
                'q': self.location,
                'appid': self.api_key,
                'units': 'metric'  # Celsius
            }

            # Make request with timeout
            response = requests.get(base_url, params=params, timeout=5)
            response.raise_for_status()

            data = response.json()

            # Extract relevant data
            condition_code = data.get('weather', [{}])[0].get('id')
            condition_main = data.get('weather', [{}])[0].get('main', 'Clear')
            description = data.get('weather', [{}])[0].get('description', 'clear sky')
            temp = data.get('main', {}).get('temp')
            feels_like = data.get('main', {}).get('feels_like')

            # Map to our weather types
            weather_type = self.CONDITION_MAP.get(condition_code, 'overcast')

            logger.info(
                f"SS-002: Fetched real weather for {self.location}: "
                f"{condition_main} ({description}), {temp}°C"
            )

            return {
                'type': weather_type,
                'condition': condition_main,
                'description': description,
                'temperature': temp,
                'feels_like': feels_like,
                'real': True,
                'location': self.location
            }

        except requests.RequestException as e:
            logger.error(f"SS-002: Failed to fetch weather from API: {e}")
            return None
        except Exception as e:
            logger.error(f"SS-002: Unexpected error fetching weather: {e}", exc_info=True)
            return None

    def _generate_atmospheric_weather(self) -> Dict:
        """
        Generate fitting atmospheric weather when real weather unavailable.

        Returns:
            Dict with generated weather data
        """
        # Weight weather types to favor coding-friendly conditions
        weather_types = [
            'rainy',      # 30% - Perfect coding weather
            'rainy',
            'rainy',
            'overcast',   # 30% - Neutral, common
            'overcast',
            'overcast',
            'sunny',      # 20% - Bright and energetic
            'sunny',
            'foggy',      # 10% - Mysterious
            'stormy',     # 10% - Intense
        ]

        weather_type = random.choice(weather_types)

        # Generate description based on type
        descriptions = {
            'rainy': 'Light rain tapping on the windows',
            'overcast': 'Gray skies, neutral mood',
            'sunny': 'Bright sunshine streaming in',
            'foggy': 'Fog obscuring the view outside',
            'stormy': 'Distant thunder, storm approaching'
        }

        logger.info(f"SS-002: Generated atmospheric weather: {weather_type}")

        return {
            'type': weather_type,
            'condition': weather_type.capitalize(),
            'description': descriptions.get(weather_type, 'Clear skies'),
            'temperature': None,  # Not applicable for generated weather
            'feels_like': None,
            'real': False,
            'location': None
        }

    def get_weather(self, force_refresh: bool = False) -> Dict:
        """
        Get current weather (real or generated).

        Args:
            force_refresh: Force fetch from API even if cached

        Returns:
            Dict with weather data
        """
        # Check cache first
        if not force_refresh and _weather_cache['weather_data'] and _weather_cache['last_fetch']:
            time_since_fetch = datetime.now() - _weather_cache['last_fetch']
            if time_since_fetch < WEATHER_CACHE_DURATION:
                logger.debug("SS-002: Using cached weather data")
                return _weather_cache['weather_data']

        # Try to fetch real weather if configured
        if self.is_api_configured():
            weather_data = self._fetch_from_api()
            if weather_data:
                # Cache the result
                _weather_cache['weather_data'] = weather_data
                _weather_cache['last_fetch'] = datetime.now()
                return weather_data

        # Fall back to generated weather
        weather_data = self._generate_atmospheric_weather()
        _weather_cache['weather_data'] = weather_data
        _weather_cache['last_fetch'] = datetime.now()
        return weather_data


# Global instance for easy import
_weather_service = WeatherService()


def get_weather(force_refresh: bool = False) -> Dict:
    """
    Get current weather (convenience function).

    Args:
        force_refresh: Force fetch from API even if cached

    Returns:
        Dict with weather data:
        - type: 'sunny', 'rainy', 'overcast', 'stormy', 'foggy'
        - condition: Main weather condition (e.g., 'Rain', 'Clear')
        - description: Detailed description (e.g., 'light rain')
        - temperature: Temperature in Celsius (None for generated weather)
        - feels_like: Feels like temperature (None for generated weather)
        - real: True if from API, False if generated
        - location: Location name (None for generated weather)
    """
    return _weather_service.get_weather(force_refresh)


def is_location_configured() -> bool:
    """Check if user location is configured (convenience function)."""
    return _weather_service.is_location_configured()


def is_api_configured() -> bool:
    """Check if weather API is fully configured (convenience function)."""
    return _weather_service.is_api_configured()


if __name__ == "__main__":
    # Test the weather service
    print("Testing Weather Service...\n")
    print("=" * 60)

    print(f"Location configured: {is_location_configured()}")
    print(f"API configured: {is_api_configured()}")
    print()

    weather = get_weather()
    print("Weather data:")
    for key, value in weather.items():
        print(f"  {key}: {value}")

    print("\n" + "=" * 60)
