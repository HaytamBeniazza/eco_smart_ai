"""
EcoSmart AI Configuration Management
Handles all system settings, API keys, and environment variables
"""

import os
from typing import Dict, Any
from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings and configuration"""
    
    # API Configuration
    api_host: str = Field(default="localhost", env="API_HOST")
    api_port: int = Field(default=8000, env="API_PORT")
    api_debug: bool = Field(default=True, env="API_DEBUG")
    
    # Database Configuration
    database_url: str = Field(default="sqlite:///./ecosmart.db", env="DATABASE_URL")
    database_echo: bool = Field(default=False, env="DATABASE_ECHO")
    
    # OpenWeatherMap API
    openweather_api_key: str = Field(default="", env="OPENWEATHER_API_KEY")
    openweather_base_url: str = "https://api.openweathermap.org/data/2.5"
    
    # Agent Configuration
    agent_poll_interval: int = Field(default=30, env="AGENT_POLL_INTERVAL")  # seconds
    weather_update_interval: int = Field(default=3600, env="WEATHER_UPDATE_INTERVAL")  # 1 hour
    
    # Energy Pricing (Morocco ONEE rates)
    energy_pricing: Dict[str, Any] = {
        "off_peak": {
            "hours": [0, 1, 2, 3, 4, 5],
            "rate_dh_kwh": 0.85,
            "description": "Night hours - cheapest"
        },
        "normal": {
            "hours": [6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 22, 23],
            "rate_dh_kwh": 1.20,
            "description": "Standard daytime rate"
        },
        "peak": {
            "hours": [16, 17, 18, 19, 20, 21],
            "rate_dh_kwh": 1.65,
            "description": "Evening peak - most expensive"
        }
    }
    
    monthly_base_fee_dh: float = 45.00
    
    # System Configuration
    max_agent_response_time: int = 2  # seconds
    websocket_heartbeat_interval: int = 30  # seconds
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    
    # Demo Configuration
    demo_mode: bool = Field(default=True, env="DEMO_MODE")
    simulation_speed_multiplier: int = Field(default=1, env="SIMULATION_SPEED")
    
    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings()


def get_current_pricing_tier(hour: int) -> Dict[str, Any]:
    """Get current energy pricing tier based on hour of day"""
    for tier_name, tier_data in settings.energy_pricing.items():
        if hour in tier_data["hours"]:
            return {
                "tier": tier_name,
                "rate": tier_data["rate_dh_kwh"],
                "description": tier_data["description"]
            }
    
    # Default to normal if not found
    return {
        "tier": "normal",
        "rate": settings.energy_pricing["normal"]["rate_dh_kwh"],
        "description": settings.energy_pricing["normal"]["description"]
    }


def calculate_energy_cost(consumption_kwh: float, hour: int) -> float:
    """Calculate energy cost based on consumption and time of day"""
    pricing = get_current_pricing_tier(hour)
    return consumption_kwh * pricing["rate"]


# Default device specifications for simulation
DEFAULT_DEVICES = {
    "living_room_ac": {
        "name": "Living Room AC",
        "power_watts": 2000,
        "priority": "high",
        "controllable": True,
        "room": "living_room",
        "usage_pattern": "temperature_dependent"
    },
    "bedroom_ac": {
        "name": "Bedroom AC", 
        "power_watts": 1500,
        "priority": "high",
        "controllable": True,
        "room": "bedroom",
        "usage_pattern": "schedule_based"
    },
    "led_lights": {
        "name": "LED Lighting System",
        "power_watts": 80,
        "priority": "medium",
        "controllable": True,
        "room": "all",
        "usage_pattern": "schedule_based"
    },
    "refrigerator": {
        "name": "Refrigerator",
        "power_watts": 150,
        "priority": "critical",
        "controllable": False,
        "room": "kitchen",
        "usage_pattern": "constant"
    },
    "washing_machine": {
        "name": "Washing Machine",
        "power_watts": 800,
        "priority": "low",
        "controllable": True,
        "room": "utility",
        "usage_pattern": "manual"
    },
    "tv_entertainment": {
        "name": "TV & Entertainment",
        "power_watts": 200,
        "priority": "low",
        "controllable": True,
        "room": "living_room", 
        "usage_pattern": "evening_peak"
    }
} 