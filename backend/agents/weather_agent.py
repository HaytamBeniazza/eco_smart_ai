"""
Weather Agent - Agent 2
Weather-based energy forecasting and optimization recommendations
"""

import asyncio
import requests
import json
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import math

from .base_agent import BaseAgent, AgentStatus
from core.message_broker import MessageType, MessagePriority, Message
from core.database import WeatherData
from core.config import settings


class WeatherAgent(BaseAgent):
    """
    Weather Agent - Provides weather-based energy forecasting and optimization
    
    Responsibilities:
    - Fetch weather data from OpenWeatherMap API every hour
    - Predict energy needs based on temperature
    - Calculate optimal AC/heating schedules
    - Provide 24-hour energy demand forecast
    """
    
    def __init__(self):
        super().__init__(
            agent_name="weather_agent",
            description="Weather-based energy forecasting and optimization recommendations"
        )
        
        # Weather API configuration
        self.api_key = settings.openweather_api_key
        self.base_url = settings.openweather_base_url
        self.location = "Casablanca,MA"  # Default to Casablanca, Morocco
        self.last_api_call = None
        self.api_call_count = 0
        self.daily_api_limit = 1000  # Free tier limit
        
        # Weather data state
        self.current_weather = None
        self.forecast_data = []
        self.temperature_history = []
        
        # Energy prediction models
        self.cooling_threshold = 24.0  # Celsius - start cooling above this
        self.heating_threshold = 18.0  # Celsius - start heating below this
        self.optimal_temp_range = (20.0, 26.0)  # Comfort range
        
        # Prediction statistics
        self.prediction_stats = {
            'api_calls_today': 0,
            'forecasts_generated': 0,
            'cooling_recommendations': 0,
            'heating_recommendations': 0,
            'last_forecast_time': None
        }
        
        self.logger.info("Weather Agent initialized")
    
    async def initialize(self):
        """Initialize agent-specific resources"""
        try:
            self.logger.info("Initializing Weather Agent...")
            
            # Check if API key is configured
            if not self.api_key:
                self.logger.warning("No OpenWeatherMap API key configured - using simulation mode")
                self.simulation_mode = True
            else:
                self.simulation_mode = False
                self.logger.info("OpenWeatherMap API key configured")
            
            # Load initial weather data
            await self._load_initial_weather_data()
            
            # Initialize temperature history
            await self._initialize_temperature_history()
            
            self.logger.info("Weather Agent initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize Weather Agent: {e}")
            raise
    
    async def execute_cycle(self):
        """Execute one weather monitoring cycle"""
        try:
            # Check if we need to fetch new weather data (hourly)
            should_fetch = await self._should_fetch_weather_data()
            
            if should_fetch:
                # Fetch current weather and forecast
                weather_data = await self._fetch_weather_data()
                
                if weather_data:
                    # Store weather data in database
                    await self._store_weather_data(weather_data)
                    
                    # Generate energy predictions
                    energy_forecast = await self._generate_energy_forecast(weather_data)
                    
                    # Calculate cooling/heating recommendations
                    recommendations = await self._calculate_hvac_recommendations(weather_data)
                    
                    # Broadcast weather update to other agents
                    await self._broadcast_weather_update(weather_data, energy_forecast, recommendations)
                    
                    # Update statistics
                    self.prediction_stats['forecasts_generated'] += 1
                    self.prediction_stats['last_forecast_time'] = datetime.utcnow()
            
        except Exception as e:
            self.logger.error(f"Error in weather cycle: {e}")
            raise
    
    async def handle_message(self, message: Message):
        """Handle incoming messages from other agents"""
        try:
            self.logger.debug(f"Received message: {message.type.value} from {message.from_agent}")
            
            if message.type == MessageType.CONSUMPTION_UPDATE:
                await self._handle_consumption_update(message.content)
            
            elif message.type == MessageType.SYSTEM_STATUS:
                # Respond with weather status
                await self._send_weather_status(message.from_agent)
            
            else:
                self.logger.debug(f"Unhandled message type: {message.type.value}")
                
        except Exception as e:
            self.logger.error(f"Error handling message: {e}")
    
    async def cleanup(self):
        """Cleanup agent resources"""
        self.logger.info("Cleaning up Weather Agent resources")
        self.current_weather = None
        self.forecast_data.clear()
        self.temperature_history.clear()
    
    def get_capabilities(self) -> List[str]:
        """Return agent capabilities"""
        return [
            "weather_monitoring",
            "temperature_forecasting",
            "energy_demand_prediction",
            "hvac_optimization",
            "cooling_recommendations",
            "24h_forecast"
        ]
    
    def get_execution_interval(self) -> float:
        """Return execution interval (check every 10 minutes, fetch hourly)"""
        return 600  # 10 minutes
    
    # ===== WEATHER DATA METHODS =====
    
    async def _should_fetch_weather_data(self) -> bool:
        """Determine if we should fetch new weather data"""
        if self.last_api_call is None:
            return True
        
        # Fetch every hour or if we don't have current data
        time_since_last_call = datetime.utcnow() - self.last_api_call
        if time_since_last_call.total_seconds() >= settings.weather_update_interval:
            return True
        
        # Check if we're approaching daily API limit
        if self.api_call_count >= self.daily_api_limit * 0.9:
            self.logger.warning("Approaching daily API limit, reducing frequency")
            return time_since_last_call.total_seconds() >= 7200  # 2 hours
        
        return False
    
    async def _fetch_weather_data(self) -> Optional[Dict[str, Any]]:
        """Fetch weather data from OpenWeatherMap API or simulate"""
        try:
            if self.simulation_mode:
                return await self._simulate_weather_data()
            
            # Real API call
            current_url = f"{self.base_url}/weather"
            forecast_url = f"{self.base_url}/forecast"
            
            params = {
                'q': self.location,
                'appid': self.api_key,
                'units': 'metric'
            }
            
            # Fetch current weather
            current_response = requests.get(current_url, params=params, timeout=10)
            current_response.raise_for_status()
            current_data = current_response.json()
            
            # Fetch 5-day forecast
            forecast_response = requests.get(forecast_url, params=params, timeout=10)
            forecast_response.raise_for_status()
            forecast_data = forecast_response.json()
            
            # Update API usage tracking
            self.api_call_count += 2
            self.last_api_call = datetime.utcnow()
            self.prediction_stats['api_calls_today'] += 2
            
            weather_data = {
                'current': current_data,
                'forecast': forecast_data,
                'timestamp': datetime.utcnow(),
                'source': 'openweathermap'
            }
            
            self.logger.info(f"Fetched weather data for {self.location}")
            return weather_data
            
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Failed to fetch weather data: {e}")
            return await self._simulate_weather_data()
        
        except Exception as e:
            self.logger.error(f"Error fetching weather data: {e}")
            return None
    
    async def _simulate_weather_data(self) -> Dict[str, Any]:
        """Simulate realistic weather data for demo purposes"""
        try:
            current_hour = datetime.now().hour
            current_date = datetime.now()
            
            # Simulate Casablanca weather patterns
            base_temp = 22.0  # Average temperature
            
            # Daily temperature variation
            if 6 <= current_hour <= 18:  # Daytime
                temp_variation = 8 * math.sin((current_hour - 6) * math.pi / 12)
            else:  # Nighttime
                temp_variation = -3 + 2 * math.sin((current_hour - 18) * math.pi / 12)
            
            # Seasonal variation
            day_of_year = current_date.timetuple().tm_yday
            seasonal_variation = 8 * math.sin((day_of_year - 80) * 2 * math.pi / 365)
            
            current_temp = base_temp + temp_variation + seasonal_variation
            humidity = max(30, min(80, 60 + 20 * math.sin(current_hour * math.pi / 12)))
            
            # Generate forecast for next 24 hours
            forecast_list = []
            for i in range(8):  # 8 forecasts (3-hour intervals for 24 hours)
                forecast_time = current_date + timedelta(hours=i*3)
                hour = forecast_time.hour
                
                if 6 <= hour <= 18:
                    forecast_variation = 8 * math.sin((hour - 6) * math.pi / 12)
                else:
                    forecast_variation = -3 + 2 * math.sin((hour - 18) * math.pi / 12)
                
                forecast_temp = base_temp + forecast_variation + seasonal_variation
                
                forecast_list.append({
                    'dt': int(forecast_time.timestamp()),
                    'main': {
                        'temp': round(forecast_temp, 1),
                        'humidity': round(humidity + i * 2, 1)
                    },
                    'weather': [{'main': 'Clear', 'description': 'clear sky'}],
                    'dt_txt': forecast_time.strftime('%Y-%m-%d %H:%M:%S')
                })
            
            weather_data = {
                'current': {
                    'main': {
                        'temp': round(current_temp, 1),
                        'humidity': round(humidity, 1)
                    },
                    'weather': [{'main': 'Clear', 'description': 'clear sky'}],
                    'wind': {'speed': 3.5},
                    'name': 'Casablanca'
                },
                'forecast': {
                    'list': forecast_list
                },
                'timestamp': datetime.utcnow(),
                'source': 'simulation'
            }
            
            self.logger.debug(f"Simulated weather: {current_temp:.1f}°C, {humidity:.1f}% humidity")
            return weather_data
            
        except Exception as e:
            self.logger.error(f"Error simulating weather data: {e}")
            return None
    
    async def _store_weather_data(self, weather_data: Dict[str, Any]):
        """Store weather data in database"""
        try:
            session = self.get_db_session()
            try:
                current = weather_data['current']
                forecast = weather_data['forecast']['list'][0] if weather_data['forecast']['list'] else current
                
                # Calculate optimal AC temperature based on current temperature
                current_temp = current['main']['temp']
                optimal_ac_temp = await self._calculate_optimal_ac_temperature(current_temp)
                
                weather_entry = WeatherData(
                    temperature=current_temp,
                    humidity=current['main']['humidity'],
                    forecast_temp=forecast['main']['temp'],
                    optimal_ac_temp=optimal_ac_temp,
                    weather_condition=current['weather'][0]['main'],
                    wind_speed=current.get('wind', {}).get('speed', 0),
                    timestamp=weather_data['timestamp']
                )
                
                session.add(weather_entry)
                session.commit()
                
                # Update current weather state
                self.current_weather = weather_data
                self.forecast_data = weather_data['forecast']['list']
                
                # Update temperature history
                self.temperature_history.append({
                    'timestamp': weather_data['timestamp'],
                    'temperature': current_temp,
                    'humidity': current['main']['humidity']
                })
                
                # Keep only last 24 hours of history
                cutoff_time = datetime.utcnow() - timedelta(hours=24)
                self.temperature_history = [
                    entry for entry in self.temperature_history 
                    if entry['timestamp'] > cutoff_time
                ]
                
                self.logger.debug(f"Stored weather data: {current_temp}°C")
                
            finally:
                session.close()
                
        except Exception as e:
            self.logger.error(f"Failed to store weather data: {e}")
    
    async def _calculate_optimal_ac_temperature(self, outdoor_temp: float) -> float:
        """Calculate optimal AC temperature based on outdoor conditions"""
        if outdoor_temp <= self.heating_threshold:
            # Too cold - suggest heating to comfort range
            return self.optimal_temp_range[0]
        elif outdoor_temp >= self.cooling_threshold:
            # Hot - suggest cooling, but not too aggressive
            if outdoor_temp > 35:
                return 22.0  # Aggressive cooling for very hot days
            elif outdoor_temp > 30:
                return 24.0  # Moderate cooling
            else:
                return 26.0  # Light cooling
        else:
            # In comfort range - no AC needed
            return outdoor_temp
    
    # ===== ENERGY PREDICTION METHODS =====
    
    async def _generate_energy_forecast(self, weather_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate 24-hour energy demand forecast based on weather"""
        try:
            forecast_list = weather_data['forecast']['list']
            energy_predictions = []
            
            for forecast_item in forecast_list[:8]:  # Next 24 hours
                temp = forecast_item['main']['temp']
                humidity = forecast_item['main']['humidity']
                hour = datetime.fromtimestamp(forecast_item['dt']).hour
                
                # Calculate base energy demand
                base_demand = 800  # Base consumption in watts
                
                # HVAC energy calculation
                hvac_demand = 0
                if temp > self.cooling_threshold:
                    # Cooling demand increases exponentially with temperature
                    cooling_factor = (temp - self.cooling_threshold) / 10
                    hvac_demand = 3500 * min(cooling_factor, 1.0)  # Max 3.5kW for AC
                elif temp < self.heating_threshold:
                    # Heating demand
                    heating_factor = (self.heating_threshold - temp) / 10
                    hvac_demand = 2000 * min(heating_factor, 0.8)  # Max 1.6kW for heating
                
                # Lighting demand based on time of day
                if 6 <= hour <= 18:
                    lighting_demand = 0  # Daytime - no artificial lighting
                elif 19 <= hour <= 23:
                    lighting_demand = 80  # Evening - full lighting
                else:
                    lighting_demand = 20  # Night - minimal lighting
                
                # Time-based device usage
                if 18 <= hour <= 23:
                    entertainment_demand = 200  # TV and entertainment
                else:
                    entertainment_demand = 50   # Standby
                
                total_demand = base_demand + hvac_demand + lighting_demand + entertainment_demand
                
                energy_predictions.append({
                    'timestamp': datetime.fromtimestamp(forecast_item['dt']).isoformat(),
                    'temperature': temp,
                    'humidity': humidity,
                    'total_demand_watts': round(total_demand),
                    'hvac_demand_watts': round(hvac_demand),
                    'lighting_demand_watts': lighting_demand,
                    'entertainment_demand_watts': entertainment_demand,
                    'base_demand_watts': base_demand
                })
            
            # Calculate summary statistics
            total_energy_24h = sum(pred['total_demand_watts'] for pred in energy_predictions) / 1000  # kWh
            avg_demand = sum(pred['total_demand_watts'] for pred in energy_predictions) / len(energy_predictions)
            peak_demand = max(pred['total_demand_watts'] for pred in energy_predictions)
            
            forecast_summary = {
                'forecast_period_hours': 24,
                'predictions': energy_predictions,
                'summary': {
                    'total_energy_24h_kwh': round(total_energy_24h, 2),
                    'average_demand_watts': round(avg_demand),
                    'peak_demand_watts': peak_demand,
                    'hvac_contribution_percent': round(
                        sum(pred['hvac_demand_watts'] for pred in energy_predictions) / 
                        sum(pred['total_demand_watts'] for pred in energy_predictions) * 100, 1
                    )
                },
                'generated_at': datetime.utcnow().isoformat()
            }
            
            self.logger.info(f"Generated 24h energy forecast: {total_energy_24h:.2f} kWh predicted")
            return forecast_summary
            
        except Exception as e:
            self.logger.error(f"Error generating energy forecast: {e}")
            return {}
    
    async def _calculate_hvac_recommendations(self, weather_data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate HVAC optimization recommendations"""
        try:
            current_temp = weather_data['current']['main']['temp']
            forecast_list = weather_data['forecast']['list']
            
            recommendations = {
                'current_action': 'none',
                'optimal_temperature': None,
                'energy_savings_potential': 0,
                'schedule_recommendations': [],
                'urgency': 'low'
            }
            
            # Current temperature recommendations
            if current_temp > self.cooling_threshold:
                optimal_temp = await self._calculate_optimal_ac_temperature(current_temp)
                recommendations.update({
                    'current_action': 'cooling',
                    'optimal_temperature': optimal_temp,
                    'urgency': 'high' if current_temp > 32 else 'medium'
                })
                self.prediction_stats['cooling_recommendations'] += 1
                
            elif current_temp < self.heating_threshold:
                recommendations.update({
                    'current_action': 'heating',
                    'optimal_temperature': self.optimal_temp_range[0],
                    'urgency': 'medium' if current_temp < 15 else 'low'
                })
                self.prediction_stats['heating_recommendations'] += 1
            
            # Schedule recommendations for next 8 hours
            for i, forecast_item in enumerate(forecast_list[:8]):
                forecast_temp = forecast_item['main']['temp']
                forecast_time = datetime.fromtimestamp(forecast_item['dt'])
                hour = forecast_time.hour
                
                action = 'none'
                target_temp = None
                
                if forecast_temp > self.cooling_threshold:
                    action = 'cooling'
                    target_temp = await self._calculate_optimal_ac_temperature(forecast_temp)
                elif forecast_temp < self.heating_threshold:
                    action = 'heating'
                    target_temp = self.optimal_temp_range[0]
                
                # Consider time-of-day pricing
                if 16 <= hour <= 21:  # Peak hours
                    priority = 'low' if action != 'none' else 'none'
                    advice = 'Consider pre-cooling/heating before peak hours'
                else:
                    priority = 'high' if action != 'none' else 'none'
                    advice = 'Optimal time for HVAC operation'
                
                recommendations['schedule_recommendations'].append({
                    'time': forecast_time.isoformat(),
                    'action': action,
                    'target_temperature': target_temp,
                    'priority': priority,
                    'advice': advice,
                    'expected_temp': forecast_temp
                })
            
            # Calculate potential energy savings
            if recommendations['current_action'] != 'none':
                # Estimate 10-25% savings with optimization
                base_hvac_consumption = 2000  # watts
                if current_temp > 30:
                    base_hvac_consumption = 3500
                
                optimized_consumption = base_hvac_consumption * 0.8  # 20% savings
                recommendations['energy_savings_potential'] = round(
                    (base_hvac_consumption - optimized_consumption) / base_hvac_consumption * 100, 1
                )
            
            return recommendations
            
        except Exception as e:
            self.logger.error(f"Error calculating HVAC recommendations: {e}")
            return {}
    
    async def _broadcast_weather_update(self, weather_data: Dict[str, Any], 
                                       energy_forecast: Dict[str, Any], 
                                       recommendations: Dict[str, Any]):
        """Broadcast weather update to other agents"""
        try:
            current = weather_data['current']
            
            content = {
                'timestamp': datetime.utcnow().isoformat(),
                'current_weather': {
                    'temperature': current['main']['temp'],
                    'humidity': current['main']['humidity'],
                    'condition': current['weather'][0]['main'],
                    'location': current.get('name', self.location)
                },
                'energy_forecast': energy_forecast,
                'hvac_recommendations': recommendations,
                'data_source': weather_data['source'],
                'agent_stats': self.prediction_stats
            }
            
            # Broadcast general weather update
            await self.broadcast_message(
                MessageType.WEATHER_UPDATE,
                content,
                MessagePriority.MEDIUM
            )
            
            # Send specific recommendations to optimizer agent
            if recommendations.get('current_action') != 'none':
                await self.send_message(
                    "optimizer_agent",
                    MessageType.TEMPERATURE_FORECAST,
                    {
                        'recommendations': recommendations,
                        'forecast': energy_forecast,
                        'urgency': recommendations.get('urgency', 'low')
                    },
                    MessagePriority.HIGH
                )
            
            self.logger.debug(f"Broadcasted weather update: {current['main']['temp']}°C")
            
        except Exception as e:
            self.logger.error(f"Failed to broadcast weather update: {e}")
    
    # ===== MESSAGE HANDLERS =====
    
    async def _handle_consumption_update(self, content: Dict[str, Any]):
        """Handle consumption update to correlate with weather patterns"""
        try:
            total_consumption = content.get('total_consumption_watts', 0)
            timestamp = content.get('timestamp')
            
            if self.current_weather:
                current_temp = self.current_weather['current']['main']['temp']
                
                # Log correlation for future ML improvements
                correlation_data = {
                    'timestamp': timestamp,
                    'temperature': current_temp,
                    'consumption': total_consumption,
                    'correlation_type': 'weather_consumption'
                }
                
                await self.log_decision(
                    "weather_consumption_correlation",
                    correlation_data,
                    confidence=0.8
                )
                
                self.logger.debug(f"Correlated consumption {total_consumption}W with temperature {current_temp}°C")
            
        except Exception as e:
            self.logger.error(f"Failed to handle consumption update: {e}")
    
    async def _send_weather_status(self, requesting_agent: str):
        """Send current weather status to requesting agent"""
        try:
            status_data = {
                'agent_name': self.agent_name,
                'current_weather': self.current_weather['current'] if self.current_weather else None,
                'forecast_available': len(self.forecast_data) > 0,
                'prediction_stats': self.prediction_stats,
                'api_usage': {
                    'calls_today': self.api_call_count,
                    'limit': self.daily_api_limit,
                    'simulation_mode': self.simulation_mode
                },
                'agent_health': self.get_status()
            }
            
            await self.send_message(
                requesting_agent,
                MessageType.SYSTEM_STATUS,
                status_data,
                MessagePriority.MEDIUM
            )
            
        except Exception as e:
            self.logger.error(f"Failed to send weather status: {e}")
    
    # ===== UTILITY METHODS =====
    
    async def _load_initial_weather_data(self):
        """Load recent weather data from database"""
        try:
            session = self.get_db_session()
            try:
                # Get latest weather data from database
                latest_weather = session.query(WeatherData).order_by(
                    WeatherData.timestamp.desc()
                ).first()
                
                if latest_weather:
                    self.logger.info(f"Loaded weather data: {latest_weather.temperature}°C")
                
            finally:
                session.close()
                
        except Exception as e:
            self.logger.error(f"Failed to load initial weather data: {e}")
    
    async def _initialize_temperature_history(self):
        """Initialize temperature history from database"""
        try:
            session = self.get_db_session()
            try:
                # Get last 24 hours of temperature data
                cutoff_time = datetime.utcnow() - timedelta(hours=24)
                recent_weather = session.query(WeatherData).filter(
                    WeatherData.timestamp > cutoff_time
                ).order_by(WeatherData.timestamp.asc()).all()
                
                self.temperature_history = [
                    {
                        'timestamp': weather.timestamp,
                        'temperature': weather.temperature,
                        'humidity': weather.humidity
                    }
                    for weather in recent_weather
                ]
                
                self.logger.info(f"Initialized with {len(self.temperature_history)} temperature readings")
                
            finally:
                session.close()
                
        except Exception as e:
            self.logger.error(f"Failed to initialize temperature history: {e}")
    
    def get_current_weather_summary(self) -> Dict[str, Any]:
        """Get current weather summary for external access"""
        if not self.current_weather:
            return {'status': 'no_data'}
        
        current = self.current_weather['current']
        return {
            'temperature': current['main']['temp'],
            'humidity': current['main']['humidity'],
            'condition': current['weather'][0]['main'],
            'optimal_ac_temp': None,  # Calculate if needed
            'last_update': self.current_weather['timestamp'].isoformat(),
            'source': self.current_weather['source'],
            'prediction_stats': self.prediction_stats
        } 