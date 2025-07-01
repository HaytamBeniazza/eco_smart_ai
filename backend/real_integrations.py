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
            # Check cache first
            if (self.last_data and self.last_fetch and 
                (datetime.now() - self.last_fetch).seconds < self.cache_duration):
                logger.info("Using cached weather data")
                return self.last_data
            
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
                            "pressure": data["main"]["pressure"],
                            "visibility": data.get("visibility", 10000) / 1000,  # Convert to km
                            "uv_index": await self._get_uv_index(data["coord"]["lat"], data["coord"]["lon"]),
                            "source": "OpenWeatherMap",
                            "location": f"{self.city}, {self.country}",
                            "timestamp": datetime.now().isoformat()
                        }
                        
                        self.last_data = weather_data
                        self.last_fetch = datetime.now()
                        logger.info(f"Real weather data fetched: {data['main']['temp']}°C in {self.city}")
                        return weather_data
                    else:
                        logger.error(f"Weather API error: {response.status}")
                        return self._get_demo_weather()
                        
        except Exception as e:
            logger.error(f"Weather API connection failed: {e}")
            return self._get_demo_weather()
    
    async def _get_uv_index(self, lat: float, lon: float) -> float:
        """Get UV index for solar potential calculation"""
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.base_url}/uvi"
                params = {
                    "lat": lat,
                    "lon": lon,
                    "appid": self.api_key
                }
                
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data.get("value", 5.0)
        except:
            pass
        return 5.0  # Default moderate UV
    
    def _calculate_solar_potential(self, weather_data: Dict) -> float:
        """Calculate solar energy potential based on real weather"""
        base_potential = 10.0  # kWh base for clear day
        
        # Reduce based on cloud coverage
        clouds = weather_data.get("clouds", {}).get("all", 0)
        cloud_factor = 1.0 - (clouds / 100 * 0.7)
        
        # Time of day factor (simplified)
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
        
        # Heat index calculation
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

class RealEnergyIntegration:
    """Real energy monitoring integration"""
    
    def __init__(self):
        self.integrations = {
            "smart_meter": SmartMeterIntegration(),
            "tplink_kasa": TPLinkKasaIntegration(),
            "home_assistant": HomeAssistantIntegration(),
            "manual_input": ManualEnergyInput()
        }
        self.active_integrations = []
        
    async def detect_available_integrations(self) -> List[str]:
        """Detect which real energy integrations are available"""
        available = []
        
        for name, integration in self.integrations.items():
            try:
                if await integration.test_connection():
                    available.append(name)
                    logger.info(f"✅ {name} integration available")
                else:
                    logger.info(f"❌ {name} integration not available")
            except Exception as e:
                logger.debug(f"❌ {name} integration failed: {e}")
        
        self.active_integrations = available
        return available
    
    async def get_real_energy_data(self) -> Dict[str, Any]:
        """Get real energy data from available sources"""
        if not self.active_integrations:
            await self.detect_available_integrations()
        
        energy_data = {
            "current_consumption": 0.0,
            "devices": [],
            "daily_total": 0.0,
            "monthly_total": 0.0,
            "current_cost": 0.0,
            "source": "demo",
            "timestamp": datetime.now().isoformat()
        }
        
        # Try each integration
        for integration_name in self.active_integrations:
            try:
                integration = self.integrations[integration_name]
                data = await integration.get_energy_data()
                
                if data and data.get("current_consumption", 0) > 0:
                    energy_data.update(data)
                    energy_data["source"] = integration_name
                    logger.info(f"Real energy data from {integration_name}: {data['current_consumption']}W")
                    break
            except Exception as e:
                logger.error(f"Failed to get data from {integration_name}: {e}")
                continue
        
        return energy_data

class SmartMeterIntegration:
    """Smart electricity meter integration"""
    
    async def test_connection(self) -> bool:
        """Test if smart meter is accessible"""
        # Check for common smart meter interfaces
        try:
            # Look for HAN port, Zigbee, or utility API access
            # This would need specific implementation based on meter type
            return False  # Placeholder - needs real meter detection
        except:
            return False
    
    async def get_energy_data(self) -> Optional[Dict[str, Any]]:
        """Get data from smart meter"""
        # Implement based on specific smart meter protocol
        return None

class TPLinkKasaIntegration:
    """TP-Link Kasa smart device integration"""
    
    def __init__(self):
        self.devices = []
        self.discovered = False
    
    async def test_connection(self) -> bool:
        """Test if Kasa devices are available on network"""
        try:
            # Try to discover Kasa devices on local network
            # This requires python-kasa library
            # pip install python-kasa
            
            # For now, just check if library is available
            try:
                import kasa
                return True  # Library available, devices might be present
            except ImportError:
                return False
        except:
            return False
    
    async def get_energy_data(self) -> Optional[Dict[str, Any]]:
        """Get energy data from Kasa devices"""
        try:
            import kasa
            
            if not self.discovered:
                # Discover devices
                devices = await kasa.Discover.discover()
                self.devices = [dev for dev in devices.values() if hasattr(dev, 'emeter')]
                self.discovered = True
            
            total_consumption = 0.0
            device_list = []
            
            for device in self.devices:
                await device.update()
                if hasattr(device, 'emeter'):
                    power = device.emeter.power
                    total_consumption += power
                    
                    device_list.append({
                        "id": device.mac.replace(":", "_"),
                        "name": device.alias,
                        "type": "Smart Plug",
                        "current_power": power,
                        "is_on": device.is_on,
                        "room": "Unknown",
                        "controllable": True,
                        "priority": 3,
                        "source": "TP-Link Kasa"
                    })
            
            return {
                "current_consumption": total_consumption,
                "devices": device_list,
                "daily_total": total_consumption * 24 / 1000,  # Rough estimate
                "source": "tp_link_kasa"
            }
            
        except Exception as e:
            logger.error(f"Kasa integration error: {e}")
            return None

class HomeAssistantIntegration:
    """Home Assistant integration"""
    
    def __init__(self, url: str = None, token: str = None):
        self.url = url or os.getenv("HOMEASSISTANT_URL", "http://homeassistant.local:8123")
        self.token = token or os.getenv("HOMEASSISTANT_TOKEN")
    
    async def test_connection(self) -> bool:
        """Test Home Assistant connection"""
        try:
            if not self.token:
                return False
            
            async with aiohttp.ClientSession() as session:
                headers = {"Authorization": f"Bearer {self.token}"}
                async with session.get(f"{self.url}/api/", headers=headers) as response:
                    return response.status == 200
        except:
            return False
    
    async def get_energy_data(self) -> Optional[Dict[str, Any]]:
        """Get energy data from Home Assistant"""
        try:
            async with aiohttp.ClientSession() as session:
                headers = {"Authorization": f"Bearer {self.token}"}
                
                # Get all states
                async with session.get(f"{self.url}/api/states", headers=headers) as response:
                    if response.status == 200:
                        states = await response.json()
                        
                        # Find energy/power sensors
                        total_power = 0.0
                        devices = []
                        
                        for state in states:
                            entity_id = state["entity_id"]
                            
                            # Look for power sensors
                            if ("power" in entity_id.lower() or 
                                state.get("attributes", {}).get("unit_of_measurement") == "W"):
                                
                                try:
                                    power = float(state["state"])
                                    total_power += power
                                    
                                    devices.append({
                                        "id": entity_id.replace(".", "_"),
                                        "name": state.get("attributes", {}).get("friendly_name", entity_id),
                                        "type": "HA Sensor",
                                        "current_power": power,
                                        "is_on": power > 1.0,
                                        "room": "Home Assistant",
                                        "controllable": False,
                                        "priority": 2,
                                        "source": "Home Assistant"
                                    })
                                except ValueError:
                                    continue
                        
                        if devices:
                            return {
                                "current_consumption": total_power,
                                "devices": devices,
                                "source": "home_assistant"
                            }
        except Exception as e:
            logger.error(f"Home Assistant integration error: {e}")
        
        return None

class ManualEnergyInput:
    """Manual energy input for testing"""
    
    def __init__(self):
        self.manual_file = "manual_energy_data.json"
    
    async def test_connection(self) -> bool:
        """Check if manual data file exists"""
        return os.path.exists(self.manual_file)
    
    async def get_energy_data(self) -> Optional[Dict[str, Any]]:
        """Get manually input energy data"""
        try:
            if os.path.exists(self.manual_file):
                with open(self.manual_file, 'r') as f:
                    data = json.load(f)
                    data["source"] = "manual_input"
                    return data
        except Exception as e:
            logger.error(f"Manual input error: {e}")
        
        return None

# Global instances
real_weather = RealWeatherIntegration()
real_energy = RealEnergyIntegration()

async def initialize_real_integrations():
    """Initialize all real data integrations"""
    logger.info("🔍 Detecting available real data sources...")
    
    # Test weather integration
    weather_data = await real_weather.get_current_weather()
    logger.info(f"Weather source: {weather_data.get('source', 'Unknown')}")
    
    # Test energy integrations
    available_energy = await real_energy.detect_available_integrations()
    logger.info(f"Available energy sources: {available_energy}")
    
    return {
        "weather_available": weather_data.get("source") != "Demo",
        "energy_sources": available_energy
    }

if __name__ == "__main__":
    async def test_integrations():
        print("🔍 Testing Real Data Integrations...")
        result = await initialize_real_integrations()
        print(f"Results: {result}")
        
        # Test weather
        weather = await real_weather.get_current_weather()
        print(f"Weather: {weather}")
        
        # Test energy
        energy = await real_energy.get_real_energy_data()
        print(f"Energy: {energy}")
    
    asyncio.run(test_integrations()) 