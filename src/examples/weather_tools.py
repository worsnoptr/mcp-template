"""
Weather Tools - Real-World MCP Tool Examples

This module demonstrates practical MCP tools that interact with external APIs.
These examples show best practices for:
- Making HTTP requests to external services
- Error handling and validation
- Async operations for better performance
- Proper type hints and documentation

Note: This uses wttr.in, a free weather service that doesn't require API keys.
For production use, consider services like OpenWeather, Weather.gov, or AWS Weather.
"""

from mcp.server.fastmcp import FastMCP
import requests
import json
from typing import Dict, Any, Optional
from datetime import datetime


# Initialize FastMCP server
mcp = FastMCP(host="0.0.0.0", port=8000, stateless_http=True)


@mcp.tool()
def get_current_weather(location: str) -> str:
    """
    Get current weather conditions for a location.
    
    This tool fetches real-time weather data from wttr.in, a free weather service.
    It returns current conditions including temperature, description, humidity, and wind.
    
    Args:
        location: City name, coordinates, or location query (e.g., "Seattle", "London", "40.7,-74.0")
    
    Returns:
        JSON string with current weather information including:
        - temperature (Celsius and Fahrenheit)
        - condition (clear, cloudy, rainy, etc.)
        - humidity (percentage)
        - wind speed (km/h and mph)
        - location name
    
    Example:
        get_current_weather("San Francisco")
        # Returns: {"location": "San Francisco", "temperature_c": 18, ...}
    
    Raises:
        ValueError: If location is empty or invalid
        ConnectionError: If unable to reach weather service
    """
    if not location or not location.strip():
        raise ValueError("Location cannot be empty")
    
    try:
        # Use wttr.in weather API (free, no API key required)
        # Format: wttr.in/location?format=j1 returns JSON
        url = f"https://wttr.in/{location.strip()}?format=j1"
        
        # Make request with timeout
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        
        # Parse weather data
        data = response.json()
        
        # Extract current conditions
        current = data['current_condition'][0]
        location_info = data['nearest_area'][0]
        
        weather_data = {
            "location": location_info['areaName'][0]['value'],
            "region": location_info.get('region', [{}])[0].get('value', ''),
            "country": location_info['country'][0]['value'],
            "temperature_c": int(current['temp_C']),
            "temperature_f": int(current['temp_F']),
            "feels_like_c": int(current['FeelsLikeC']),
            "feels_like_f": int(current['FeelsLikeF']),
            "condition": current['weatherDesc'][0]['value'],
            "humidity": int(current['humidity']),
            "wind_speed_kmph": int(current['windspeedKmph']),
            "wind_speed_mph": int(current['windspeedMiles']),
            "wind_direction": current['winddir16Point'],
            "precipitation_mm": float(current['precipMM']),
            "cloud_cover": int(current['cloudcover']),
            "uv_index": int(current['uvIndex']),
            "visibility_km": int(current['visibility']),
            "observation_time": current['observation_time']
        }
        
        return json.dumps(weather_data, indent=2)
        
    except requests.exceptions.Timeout:
        raise ConnectionError(f"Weather service timeout for location: {location}")
    except requests.exceptions.RequestException as e:
        raise ConnectionError(f"Failed to fetch weather data: {str(e)}")
    except (KeyError, IndexError, ValueError) as e:
        raise ValueError(f"Invalid response format or location not found: {str(e)}")


@mcp.tool()
def get_weather_forecast(location: str, days: int = 3) -> str:
    """
    Get weather forecast for a location.
    
    Args:
        location: City name, coordinates, or location query
        days: Number of days to forecast (1-3, default: 3)
    
    Returns:
        JSON string with daily forecast including:
        - date
        - max/min temperature
        - condition
        - chance of rain
        - sunrise/sunset times
    
    Example:
        get_weather_forecast("Tokyo", 2)
    """
    if not location or not location.strip():
        raise ValueError("Location cannot be empty")
    
    if days < 1 or days > 3:
        raise ValueError("Days must be between 1 and 3")
    
    try:
        url = f"https://wttr.in/{location.strip()}?format=j1"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        location_info = data['nearest_area'][0]
        
        forecast_data = {
            "location": location_info['areaName'][0]['value'],
            "country": location_info['country'][0]['value'],
            "forecast": []
        }
        
        # Get forecast for requested days
        for day_data in data['weather'][:days]:
            forecast_data['forecast'].append({
                "date": day_data['date'],
                "max_temp_c": int(day_data['maxtempC']),
                "max_temp_f": int(day_data['maxtempF']),
                "min_temp_c": int(day_data['mintempC']),
                "min_temp_f": int(day_data['mintempF']),
                "avg_temp_c": int(day_data['avgtempC']),
                "avg_temp_f": int(day_data['avgtempF']),
                "condition": day_data['hourly'][4]['weatherDesc'][0]['value'],  # Midday condition
                "total_snow_cm": float(day_data['totalSnow_cm']),
                "sun_hour": float(day_data['sunHour']),
                "uv_index": int(day_data['uvIndex']),
                "astronomy": {
                    "sunrise": day_data['astronomy'][0]['sunrise'],
                    "sunset": day_data['astronomy'][0]['sunset'],
                    "moonrise": day_data['astronomy'][0]['moonrise'],
                    "moonset": day_data['astronomy'][0]['moonset'],
                    "moon_phase": day_data['astronomy'][0]['moon_phase'],
                    "moon_illumination": int(day_data['astronomy'][0]['moon_illumination'])
                }
            })
        
        return json.dumps(forecast_data, indent=2)
        
    except requests.exceptions.Timeout:
        raise ConnectionError(f"Weather service timeout for location: {location}")
    except requests.exceptions.RequestException as e:
        raise ConnectionError(f"Failed to fetch weather data: {str(e)}")
    except (KeyError, IndexError, ValueError) as e:
        raise ValueError(f"Invalid response format or location not found: {str(e)}")


@mcp.tool()
def search_location(query: str) -> str:
    """
    Search for location information to use with weather tools.
    
    This is useful when you're not sure about exact location names or want to
    verify a location before getting weather data.
    
    Args:
        query: Location search query (city name, landmark, coordinates)
    
    Returns:
        JSON string with location details:
        - location name
        - region
        - country
        - latitude/longitude
        - population (if available)
    
    Example:
        search_location("Space Needle")
        # Returns: {"name": "Seattle", "region": "Washington", ...}
    """
    if not query or not query.strip():
        raise ValueError("Search query cannot be empty")
    
    try:
        url = f"https://wttr.in/{query.strip()}?format=j1"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        location_info = data['nearest_area'][0]
        
        result = {
            "name": location_info['areaName'][0]['value'],
            "region": location_info.get('region', [{}])[0].get('value', ''),
            "country": location_info['country'][0]['value'],
            "latitude": location_info['latitude'],
            "longitude": location_info['longitude'],
            "population": location_info.get('population', 'Unknown')
        }
        
        return json.dumps(result, indent=2)
        
    except requests.exceptions.Timeout:
        raise ConnectionError(f"Location search timeout for: {query}")
    except requests.exceptions.RequestException as e:
        raise ConnectionError(f"Failed to search location: {str(e)}")
    except (KeyError, IndexError, ValueError) as e:
        raise ValueError(f"Location not found or invalid query: {str(e)}")


@mcp.tool()
def compare_weather(location1: str, location2: str) -> str:
    """
    Compare current weather conditions between two locations.
    
    This is useful for travel planning or comparing climate between cities.
    
    Args:
        location1: First location to compare
        location2: Second location to compare
    
    Returns:
        JSON string with side-by-side comparison of weather conditions
    
    Example:
        compare_weather("New York", "Los Angeles")
    """
    if not location1 or not location1.strip():
        raise ValueError("Location 1 cannot be empty")
    if not location2 or not location2.strip():
        raise ValueError("Location 2 cannot be empty")
    
    try:
        # Get weather for both locations
        weather1_str = get_current_weather(location1)
        weather2_str = get_current_weather(location2)
        
        weather1 = json.loads(weather1_str)
        weather2 = json.loads(weather2_str)
        
        # Create comparison
        comparison = {
            "location_1": {
                "name": weather1['location'],
                "temperature_c": weather1['temperature_c'],
                "temperature_f": weather1['temperature_f'],
                "condition": weather1['condition'],
                "humidity": weather1['humidity']
            },
            "location_2": {
                "name": weather2['location'],
                "temperature_c": weather2['temperature_c'],
                "temperature_f": weather2['temperature_f'],
                "condition": weather2['condition'],
                "humidity": weather2['humidity']
            },
            "comparison": {
                "temperature_difference_c": abs(weather1['temperature_c'] - weather2['temperature_c']),
                "temperature_difference_f": abs(weather1['temperature_f'] - weather2['temperature_f']),
                "warmer_location": weather1['location'] if weather1['temperature_c'] > weather2['temperature_c'] else weather2['location'],
                "humidity_difference": abs(weather1['humidity'] - weather2['humidity']),
                "more_humid": weather1['location'] if weather1['humidity'] > weather2['humidity'] else weather2['location']
            }
        }
        
        return json.dumps(comparison, indent=2)
        
    except Exception as e:
        raise ValueError(f"Failed to compare weather: {str(e)}")


# Example of how to use these tools in your server.py:
"""
# In src/server.py:

from examples.weather_tools import (
    get_current_weather,
    get_weather_forecast,
    search_location,
    compare_weather
)

# Or import the entire mcp instance:
from examples.weather_tools import mcp

# The tools will be automatically registered and available when the server starts
"""
