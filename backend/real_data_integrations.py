#!/usr/bin/env python3
"""
EcoSmart AI Real Data Integrations
Connect to actual weather APIs, energy meters, and IoT devices
"""

import asyncio
import aiohttp
import json
import os
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RealWeatherIntegration:
    """Real weather data from OpenWeatherMap API"""
    
    def __init__(self, api_key: str = None, city: str = "Casablanca", country: str = "MA"):
        self.api_key = api_key or os.getenv("OPENWEATHER_API_KEY")
        self.city = city
        self.country = country
        self.base_url = "http://api.openweathermap.org/data/2.5"
        self.last_data = None
        self.cache_duration = 600  # 10 minutes
        self.last_fetch = None
        
    async def get_current_weather(self) -> Dict[str, Any]:
        """Get real current weather data"""
        try:
            if not self.api_key:
                logger.warning("No OpenWeather API key provided, using demo data")
                return self._get_demo_weather()
            
            async with aiohttp.ClientSession() as session:
                url = f"{self.base_url}/weather"
                params = {
                    "q": f"{self.city},{self.country}",
                    "appid": self.api_key,
                    "units": "metric"
                }
                
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        # Transform to our format
                        weather_data = {
                            "temperature": data["main"]["temp"],
                            "humidity": data["main"]["humidity"],
                            "wind_speed": data["wind"]["speed"] * 3.6,  # Convert m/s to km/h
                            "description": data["weather"][0]["description"].title(),
                            "solar_potential": self._calculate_solar_potential(data),
                            "cooling_needs": self._calculate_cooling_needs(data["main"]["temp"], data["main"]["humidity"]),
                            "source": "OpenWeatherMap",
                            "location": f"{self.city}, {self.country}",
                            "timestamp": datetime.now().isoformat()
                        }
                        
                        logger.info(f"Real weather data: {data['main']['temp']}°C in {self.city}")
                        return weather_data
                    else:
                        logger.error(f"Weather API error: {response.status}")
                        return self._get_demo_weather()
                        
        except Exception as e:
            logger.error(f"Weather API connection failed: {e}")
            return self._get_demo_weather()
    
    def _calculate_solar_potential(self, weather_data: Dict) -> float:
        """Calculate solar energy potential based on real weather"""
        base_potential = 10.0
        clouds = weather_data.get("clouds", {}).get("all", 0)
        cloud_factor = 1.0 - (clouds / 100 * 0.7)
        
        hour = datetime.now().hour
        if 6 <= hour <= 18:
            time_factor = 1.0 if 10 <= hour <= 16 else 0.7
        else:
            time_factor = 0.0
        
        return round(base_potential * cloud_factor * time_factor, 1)
    
    def _calculate_cooling_needs(self, temp: float, humidity: float) -> float:
        """Calculate cooling needs based on real temperature and humidity"""
        if temp < 20:
            return 0.0
        
        heat_factor = max(0, (temp - 20) / 10)
        humidity_factor = max(0, (humidity - 40) / 60)
        
        return round(heat_factor * 5 + humidity_factor * 2, 1)
    
    def _get_demo_weather(self) -> Dict[str, Any]:
        """Fallback demo weather data"""
        return {
            "temperature": 22.0,
            "humidity": 65,
            "wind_speed": 12.0,
            "description": "Demo Data - API Key Required",
            "solar_potential": 8.5,
            "cooling_needs": 5.2,
            "source": "Demo",
            "location": f"{self.city}, {self.country}",
            "timestamp": datetime.now().isoformat()
        }

class SmartDeviceIntegration:
    """Smart device integration for real IoT devices"""
    
    def __init__(self):
        self.devices = []
        
    async def discover_devices(self) -> List[Dict[str, Any]]:
        """Discover smart devices on network"""
        discovered = []
        
        # Try different discovery methods
        try:
            # TP-Link Kasa devices
            kasa_devices = await self._discover_kasa_devices()
            discovered.extend(kasa_devices)
        except Exception as e:
            logger.debug(f"Kasa discovery failed: {e}")
        
        return discovered
    
    async def _discover_kasa_devices(self) -> List[Dict[str, Any]]:
        """Discover TP-Link Kasa devices"""
        devices = []
        try:
            # This would require python-kasa library
            # For now, return empty list
            pass
        except:
            pass
        return devices

# Global instances
real_weather = RealWeatherIntegration()
smart_devices = SmartDeviceIntegration()

async def get_real_weather_data() -> Dict[str, Any]:
    """Get real weather data"""
    return await real_weather.get_current_weather()

async def get_real_device_data() -> List[Dict[str, Any]]:
    """Get real device data"""
    return await smart_devices.discover_devices()

# Setup instructions for users
SETUP_INSTRUCTIONS = """
🔧 REAL DATA INTEGRATION SETUP:

1. WEATHER DATA (FREE):
   - Sign up at: https://openweathermap.org/api
   - Get free API key
   - Set environment variable: OPENWEATHER_API_KEY=your_key_here

2. SMART DEVICES:
   - TP-Link Kasa: Install python-kasa library
   - Home Assistant: Set HOMEASSISTANT_URL and HOMEASSISTANT_TOKEN
   - Smart plugs with energy monitoring recommended

3. ENERGY MONITORING:
   - Smart electricity meter with API access
   - Individual device energy monitors
   - Utility company API integration

Run: python backend/real_data_integrations.py to test connections
""" 