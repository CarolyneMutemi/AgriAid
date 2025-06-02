import os
import requests
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Union, Tuple
from functools import lru_cache, wraps
import time
import logging
import json
from pathlib import Path
from dotenv import load_dotenv
from langchain_core.tools import tool
from .utils import capitalize_words


load_dotenv()  # Load environment variables from .env file if available

# Configure logging
# logging.basicConfig(level=logging.INFO)
# logger = logging.getLogger(__name__)

kenyan_wards = {}

# Constants
BASE_URL = "https://api.openweathermap.org/data/3.0/onecall"
RATE_LIMIT_DELAY = 1  # seconds between requests to avoid hitting limits
MAX_RETRIES = 3
API_KEY = os.getenv("OPENWEATHER_API_KEY")

def rate_limit(func):
    """Decorator to add rate limiting between API calls"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        time.sleep(RATE_LIMIT_DELAY)
        return func(*args, **kwargs)
    return wrapper

def retry_on_failure(max_retries: int = MAX_RETRIES):
    """Decorator to retry API calls on failure"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except requests.exceptions.RequestException as e:
                    last_exception = e
                    if attempt < max_retries - 1:
                        wait_time = 2 ** attempt  # Exponential backoff
                        # logger.warning(f"API call failed (attempt {attempt + 1}), retrying in {wait_time}s: {e}")
                        time.sleep(wait_time)
                    else:
                        # logger.error(f"API call failed after {max_retries} attempts: {e}")
                        print(f"API call failed after {max_retries} attempts: {e}")
            raise last_exception
        return wrapper
    return decorator

@rate_limit
@retry_on_failure()
def make_api_request(url: str, params: Dict) -> Dict:
    """Make HTTP request to OpenWeather API with error handling"""
    try:
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code == 429:
            raise requests.exceptions.HTTPError(
                "API rate limit exceeded. Daily limit of 1,000 calls reached or custom limit hit."
            )
        elif response.status_code == 401:
            raise requests.exceptions.HTTPError("Invalid API key")
        elif response.status_code == 404:
            raise requests.exceptions.HTTPError("Location not found")
        elif response.status_code != 200:
            raise requests.exceptions.HTTPError(f"API error: {response.status_code}")
        
        return response.json()
    
    except requests.exceptions.Timeout:
        raise requests.exceptions.RequestException("Request timed out")
    except requests.exceptions.ConnectionError:
        raise requests.exceptions.RequestException("Connection error - check internet connectivity")
    except json.JSONDecodeError:
        raise requests.exceptions.RequestException("Invalid response format from API")

def get_current_weather_and_forecast(lat: float, lon: float, api_key: str, 
                                   exclude: Optional[List[str]] = None, 
                                   units: str = "metric") -> Dict:
    """
    Get current weather and forecast data
    
    Args:
        lat: Latitude
        lon: Longitude  
        api_key: OpenWeather API key
        exclude: Optional list of data blocks to exclude (minutely, hourly, daily, alerts)
        units: Temperature units (metric, imperial, standard)
    
    Returns:
        Weather data dictionary
    """
    params = {
        "lat": lat,
        "lon": lon,
        "appid": api_key,
        "units": units
    }
    
    if exclude:
        params["exclude"] = ",".join(exclude)
    
    return make_api_request(BASE_URL, params)

def get_historical_weather(lat: float, lon: float, api_key: str, 
                          timestamp: int, units: str = "metric") -> Dict:
    """
    Get historical weather data for a specific timestamp
    
    Args:
        lat: Latitude
        lon: Longitude
        api_key: OpenWeather API key
        timestamp: Unix timestamp for historical data
        units: Temperature units
    
    Returns:
        Historical weather data dictionary
    """
    url = f"{BASE_URL}/timemachine"
    params = {
        "lat": lat,
        "lon": lon,
        "dt": timestamp,
        "appid": api_key,
        "units": units
    }
    
    return make_api_request(url, params)

def get_daily_aggregation(lat: float, lon: float, api_key: str, 
                         date: str, units: str = "metric") -> Dict:
    """
    Get daily aggregation historical data
    
    Args:
        lat: Latitude
        lon: Longitude
        api_key: OpenWeather API key
        date: Date in YYYY-MM-DD format
        units: Temperature units
    
    Returns:
        Daily aggregation data dictionary
    """
    url = f"{BASE_URL}/day_summary"
    params = {
        "lat": lat,
        "lon": lon,
        "date": date,
        "appid": api_key,
        "units": units
    }
    
    return make_api_request(url, params)

def get_weather_overview(lat: float, lon: float, api_key: str, 
                        units: str = "metric") -> Dict:
    """
    Get weather overview with human-readable summary
    
    Args:
        lat: Latitude
        lon: Longitude
        api_key: OpenWeather API key
        units: Temperature units
    
    Returns:
        Weather overview data dictionary
    """
    url = f"{BASE_URL}/overview"
    params = {
        "lat": lat,
        "lon": lon,
        "appid": api_key,
        "units": units
    }
    
    return make_api_request(url, params)

# Helper functions for farmers

def extract_farmer_relevant_data(weather_data: Dict) -> Dict:
    """Extract weather information most relevant to farmers"""
    try:
        current = weather_data.get("current", {})
        daily = weather_data.get("daily", [])
        
        farmer_data = {
            "current_conditions": {
                "temperature": current.get("temp"),
                "feels_like": current.get("feels_like"),
                "humidity": current.get("humidity"),
                "pressure": current.get("pressure"),
                "wind_speed": current.get("wind_speed"),
                "wind_direction": current.get("wind_deg"),
                "weather_description": current.get("weather", [{}])[0].get("description"),
                "visibility": current.get("visibility"),
                "uv_index": current.get("uvi"),
                "sunrise": current.get("sunrise"),
                "sunset": current.get("sunset")
            },
            "daily_forecast": []
        }
        
        # Extract next 7 days forecast
        for day in daily[:7]:
            daily_info = {
                "date": datetime.fromtimestamp(day.get("dt", 0)).strftime("%Y-%m-%d"),
                "temp_max": day.get("temp", {}).get("max"),
                "temp_min": day.get("temp", {}).get("min"),
                "humidity": day.get("humidity"),
                "wind_speed": day.get("wind_speed"),
                "weather": day.get("weather", [{}])[0].get("description"),
                "precipitation_probability": day.get("pop", 0) * 100,  # Convert to percentage
                "uv_index": day.get("uvi"),
                "sunrise": day.get("sunrise"),
                "sunset": day.get("sunset")
            }
            
            # Add rainfall data if available
            if "rain" in day:
                daily_info["rainfall"] = day["rain"]
            
            farmer_data["daily_forecast"].append(daily_info)
        
        return farmer_data
    
    except Exception as e:
        # logger.error(f"Error extracting farmer data: {e}")
        return {}

def format_weather_for_sms(weather_data: Dict, location_name: str = "") -> str:
    """Format weather data for SMS/USSD display (character limit friendly)"""
    try:
        current = weather_data.get("current_conditions", {})
        forecast = weather_data.get("daily_forecast", [])
        
        # Current weather (keep it concise for SMS)
        sms_text = f"Weather {location_name}\n"
        sms_text += f"Now: {current.get('temperature', 'N/A')}°C, {current.get('weather_description', 'N/A')}\n"
        sms_text += f"Humidity: {current.get('humidity', 'N/A')}%, Wind: {current.get('wind_speed', 'N/A')}m/s\n"
        
        # Next 3 days forecast (most relevant for farmers)
        sms_text += "3-Day Forecast:\n"
        for day in forecast[:3]:
            date = day.get('date', 'N/A')
            temp_max = day.get('temp_max', 'N/A')
            temp_min = day.get('temp_min', 'N/A')
            rain_prob = day.get('precipitation_probability', 0)
            weather = day.get('weather', 'N/A')
            
            sms_text += f"{date}: {temp_min}-{temp_max}°C, Rain:{rain_prob:.0f}%, {weather}\n"
        
        return sms_text.strip()
    
    except Exception as e:
        # logger.error(f"Error formatting SMS: {e}")
        return "Weather data unavailable"

def get_farming_alerts(weather_data: Dict) -> List[str]:
    """Generate farming-specific alerts based on weather conditions"""
    alerts = []
    
    try:
        current = weather_data.get("current_conditions", {})
        forecast = weather_data.get("daily_forecast", [])
        
        # Temperature alerts
        temp = current.get("temperature")
        if temp and temp > 35:
            alerts.append("High temperature alert: Consider irrigation and shade for crops")
        elif temp and temp < 5:
            alerts.append("Low temperature alert: Protect sensitive crops from frost")
        
        # Humidity alerts
        humidity = current.get("humidity")
        if humidity and humidity > 90:
            alerts.append("High humidity: Monitor for fungal diseases")
        elif humidity and humidity < 30:
            alerts.append("Low humidity: Increase irrigation frequency")
        
        # Wind alerts
        wind_speed = current.get("wind_speed")
        if wind_speed and wind_speed > 10:
            alerts.append("Strong winds: Secure greenhouse structures and young plants")
        
        # UV alerts
        uv_index = current.get("uv_index")
        if uv_index and uv_index > 8:
            alerts.append("High UV: Provide shade for workers and sensitive crops")
        
        # Rain forecast alerts
        for day in forecast[:3]:
            rain_prob = day.get("precipitation_probability", 0)
            date = day.get("date", "")
            if rain_prob > 80:
                alerts.append(f"Heavy rain expected {date}: Prepare drainage and harvest ready crops")
            elif rain_prob < 10:
                alerts.append(f"No rain expected {date}: Plan irrigation")
        
        return alerts
    
    except Exception as e:
        # logger.error(f"Error generating farming alerts: {e}")
        return []


@lru_cache(maxsize=1)
def get_kenya_wards_data(file_path):
    """
    Reads a JSON file containing data on Kenyan wards from the given file path and returns the parsed data as a Python object.

    Parameters:
        file_path (str): The path to the JSON file.

    Returns:
        dict : The parsed JSON content.

    Raises:
        FileNotFoundError: If the file does not exist.
        json.JSONDecodeError: If the file is not valid JSON.
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            data = json.load(file)
        return data
    except FileNotFoundError:
        print(f"❌ File not found: {file_path}")
        raise
    except json.JSONDecodeError as e:
        print(f"❌ Failed to decode JSON: {e}")
        raise


def get_coordinates_by_region(county: str, subcounty: str, ward: str) -> Optional[Tuple[float, float]]:
    """Get coordinates for a Kenya region"""
    path = Path(os.getenv("KENYA_WARDS_FILE", "../assets/kenya_wards.json")).resolve()
    regions = get_kenya_wards_data(path)
    ward = regions.get(county, {}).get(subcounty, {}).get(ward, {})
    ward_coordinates = ward.get("centroid", [])
    return ward_coordinates


# Main weather tool functions for the ReAct agent


def get_weather_for_farmer(county: str,
                           subcounty: str = "",
                           ward: str = "",
                           weather_type: str = "current_and_forecast") -> Dict:
    """
    Main function to get weather data for farmers
    
    Args:
        county: Name of the county (e.g., "Isiolo")
        subcounty: Name of the subcounty (e.g, "Isiolo Sub County")
        ward: Name of the ward (e.g., "Wabera")
        coordinates: Optional coordinates as [latitude, longitude] (e.g., [0.0, 0.0])
        weather_type: Type of weather data ("current_and_forecast", "historical", "overview")
                        -> "current_and_forecast" for current weather and 3-day forecast (default)
                        -> "historical" for yesterday's weather
                        -> "overview" for the current general weather overview
    
    Returns:
        Processed weather data for farmers
    """
    try:
        coords = get_coordinates_by_region(county, subcounty, ward)
        if not coords:
            raise ValueError(f"Unknown region")
        lat, lon = coords
        
        # Get weather data based on type
        if weather_type == "current_and_forecast":
            raw_data = get_current_weather_and_forecast(lat, lon, API_KEY)
            processed_data = extract_farmer_relevant_data(raw_data)
            
        elif weather_type == "overview":
            raw_data = get_weather_overview(lat, lon, API_KEY)
            processed_data = {"overview": raw_data}
            
        elif weather_type == "historical":
            # Get yesterday's data as example
            yesterday = int((datetime.now() - timedelta(days=1)).timestamp())
            raw_data = get_historical_weather(lat, lon, API_KEY, yesterday)
            processed_data = {"historical": raw_data}
            
        else:
            raise ValueError(f"Invalid weather_type: {weather_type}")
        
        # Add location info
        processed_data["location"] = {
            "county": county,
            "subcounty": subcounty,
            "ward": ward,
            "latitude": lat,
            "longitude": lon
        }
        
        # Add farming alerts if current weather
        if weather_type == "current_and_forecast":
            processed_data["farming_alerts"] = get_farming_alerts(processed_data)
            processed_data["sms_format"] = format_weather_for_sms(processed_data, ward)
        
        return {
            "success": True,
            "data": processed_data
        }
    
    except requests.exceptions.HTTPError as e:
        if "429" in str(e):
            return {
                "success": False,
                "error": "daily_limit_exceeded",
                "message": "Daily API limit reached. Please try again tomorrow or upgrade your plan."
            }
        elif "401" in str(e):
            return {
                "success": False,
                "error": "invalid_api_key",
                "message": "Invalid API key. Please check your OpenWeather API key."
            }
        else:
            return {
                "success": False,
                "error": "api_error",
                "message": f"API error: {str(e)}"
            }
    
    except Exception as e:
        # logger.error(f"Weather tool error: {e}")
        return {
            "success": False,
            "error": "general_error",
            "message": f"Error getting weather data: {str(e)}"
        }

# Example usage and testing functions

def test_weather_tool():
    """Test function for the weather tool"""
    
    # Test current weather for Nairobi
    result = get_weather_for_farmer("Isiolo", "Isiolo Sub County", "Wabera", "overview")
    
    if result["success"]:
        print("Weather data retrieved successfully!")
        print(json.dumps(result["data"], indent=2))
        
        # Print SMS format
        if "sms_format" in result["data"]:
            print("\nSMS Format:")
            print(result["data"]["sms_format"])
    else:
        print(f"Error: {result['message']}")

if __name__ == "__main__":
    # Example of how to use the weather tool
    test_weather_tool()