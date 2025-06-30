"""
Weather Endpoints - Weather data and HVAC optimization
"""

from fastapi import APIRouter, HTTPException, Query, Depends
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from pydantic import BaseModel

from core.database import get_db, WeatherData
from core.config import settings


# Response models
class CurrentWeather(BaseModel):
    timestamp: datetime
    temperature: float
    humidity: float
    description: str
    feels_like: float
    wind_speed: float
    city: str


class WeatherForecast(BaseModel):
    timestamp: datetime
    temperature: float
    humidity: float
    description: str
    precipitation_probability: float
    hour: int


class HVACRecommendation(BaseModel):
    device_id: str
    device_name: str
    action: str  # 'cooling', 'heating', 'off', 'reduce'
    target_temperature: Optional[float] = None
    power_adjustment: Optional[int] = None
    reason: str
    urgency: str  # 'low', 'medium', 'high'
    estimated_savings_dh: float


class EnergyImpactAnalysis(BaseModel):
    current_temperature: float
    predicted_consumption_increase: float
    hvac_load_factor: float
    cooling_demand_24h: List[Dict[str, Any]]
    optimization_opportunities: List[str]
    comfort_vs_cost_analysis: Dict[str, Any]


router = APIRouter(prefix="/api/weather", tags=["weather"])


@router.get("/current", response_model=CurrentWeather)
async def get_current_weather(db: Session = Depends(get_db)):
    """Get current weather conditions"""
    try:
        # Get latest weather data from database
        latest_weather = db.query(WeatherData).order_by(
            WeatherData.timestamp.desc()
        ).first()
        
        if not latest_weather:
            # Return simulated weather data if no real data available
            return _get_simulated_current_weather()
        
        return CurrentWeather(
            timestamp=latest_weather.timestamp,
            temperature=latest_weather.temperature,
            humidity=latest_weather.humidity,
            description=latest_weather.description,
            feels_like=latest_weather.feels_like,
            wind_speed=latest_weather.wind_speed,
            city=latest_weather.city
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get current weather: {str(e)}")


@router.get("/forecast", response_model=List[WeatherForecast])
async def get_weather_forecast(
    hours: int = Query(24, description="Number of hours to forecast"),
    db: Session = Depends(get_db)
):
    """Get weather forecast for next N hours"""
    try:
        # Get forecast data from database
        since_time = datetime.utcnow()
        until_time = since_time + timedelta(hours=hours)
        
        forecast_data = db.query(WeatherData).filter(
            WeatherData.timestamp >= since_time,
            WeatherData.timestamp <= until_time
        ).order_by(WeatherData.timestamp.asc()).all()
        
        if len(forecast_data) < hours // 2:  # If we don't have enough real data
            return _get_simulated_forecast(hours)
        
        forecasts = []
        for weather in forecast_data[:hours]:
            forecasts.append(WeatherForecast(
                timestamp=weather.timestamp,
                temperature=weather.temperature,
                humidity=weather.humidity,
                description=weather.description,
                precipitation_probability=getattr(weather, 'precipitation_probability', 0.0),
                hour=weather.timestamp.hour
            ))
        
        return forecasts
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get weather forecast: {str(e)}")


@router.get("/hvac/recommendations", response_model=List[HVACRecommendation])
async def get_hvac_recommendations(db: Session = Depends(get_db)):
    """Get HVAC optimization recommendations based on weather"""
    try:
        # Get current weather
        current_weather = await get_current_weather(db)
        
        # Get forecast for next 6 hours
        forecast = await get_weather_forecast(6, db)
        
        # Import devices to get HVAC devices
        from core.database import Device
        hvac_devices = db.query(Device).filter(
            Device.usage_pattern == 'temperature_dependent'
        ).all()
        
        recommendations = []
        
        for device in hvac_devices:
            recommendation = _generate_hvac_recommendation(
                device, current_weather, forecast
            )
            if recommendation:
                recommendations.append(recommendation)
        
        return recommendations
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get HVAC recommendations: {str(e)}")


@router.get("/energy-impact", response_model=EnergyImpactAnalysis)
async def get_weather_energy_impact(db: Session = Depends(get_db)):
    """Get weather impact analysis on energy consumption"""
    try:
        # Get current weather and forecast
        current_weather = await get_current_weather(db)
        forecast_24h = await get_weather_forecast(24, db)
        
        # Calculate energy impact
        impact_analysis = _calculate_energy_impact(current_weather, forecast_24h)
        
        return impact_analysis
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get energy impact analysis: {str(e)}")


@router.get("/historical/{date}")
async def get_historical_weather(
    date: str,
    db: Session = Depends(get_db)
):
    """Get historical weather data for a specific date"""
    try:
        # Parse date
        try:
            target_date = datetime.strptime(date, '%Y-%m-%d').date()
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
        
        # Get weather data for the day
        start_time = datetime.combine(target_date, datetime.min.time())
        end_time = start_time + timedelta(days=1)
        
        historical_data = db.query(WeatherData).filter(
            WeatherData.timestamp >= start_time,
            WeatherData.timestamp < end_time
        ).order_by(WeatherData.timestamp.asc()).all()
        
        if not historical_data:
            raise HTTPException(status_code=404, detail=f"No weather data found for {date}")
        
        # Calculate daily statistics
        temperatures = [w.temperature for w in historical_data]
        humidity_values = [w.humidity for w in historical_data]
        
        daily_stats = {
            'date': date,
            'min_temperature': min(temperatures),
            'max_temperature': max(temperatures),
            'avg_temperature': sum(temperatures) / len(temperatures),
            'min_humidity': min(humidity_values),
            'max_humidity': max(humidity_values),
            'avg_humidity': sum(humidity_values) / len(humidity_values),
            'hourly_data': [
                {
                    'timestamp': w.timestamp.isoformat(),
                    'temperature': w.temperature,
                    'humidity': w.humidity,
                    'description': w.description,
                    'feels_like': w.feels_like,
                    'wind_speed': w.wind_speed
                }
                for w in historical_data
            ]
        }
        
        return daily_stats
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get historical weather: {str(e)}")


@router.get("/comfort-zone")
async def get_comfort_zone_analysis(db: Session = Depends(get_db)):
    """Get comfort zone analysis and optimization suggestions"""
    try:
        current_weather = await get_current_weather(db)
        
        # Define comfort zones
        comfort_zones = {
            'optimal': {'temp_range': (20, 24), 'humidity_range': (40, 60)},
            'acceptable': {'temp_range': (18, 26), 'humidity_range': (30, 70)},
            'uncomfortable': {'temp_range': (15, 30), 'humidity_range': (20, 80)}
        }
        
        # Determine current comfort level
        current_temp = current_weather.temperature
        current_humidity = current_weather.humidity
        
        comfort_level = 'uncomfortable'
        for level, ranges in comfort_zones.items():
            temp_range = ranges['temp_range']
            humidity_range = ranges['humidity_range']
            
            if (temp_range[0] <= current_temp <= temp_range[1] and 
                humidity_range[0] <= current_humidity <= humidity_range[1]):
                comfort_level = level
                break
        
        # Generate recommendations
        recommendations = []
        energy_savings_potential = 0
        
        if current_temp > 26:  # Too hot
            recommendations.append({
                'action': 'Enable smart cooling',
                'description': 'Activate AC with optimal temperature setting',
                'energy_impact': 'Medium increase',
                'comfort_impact': 'High improvement'
            })
            energy_savings_potential = 15  # 15% potential savings with optimization
        elif current_temp < 18:  # Too cold
            recommendations.append({
                'action': 'Enable smart heating',
                'description': 'Activate heating with efficient schedule',
                'energy_impact': 'Medium increase',
                'comfort_impact': 'High improvement'
            })
            energy_savings_potential = 12
        else:
            recommendations.append({
                'action': 'Maintain current settings',
                'description': 'Temperature is in comfortable range',
                'energy_impact': 'No change',
                'comfort_impact': 'Maintained'
            })
            energy_savings_potential = 5  # Minor optimization opportunities
        
        if current_humidity > 70:
            recommendations.append({
                'action': 'Reduce humidity',
                'description': 'Use dehumidification or AC dry mode',
                'energy_impact': 'Low increase',
                'comfort_impact': 'Medium improvement'
            })
        elif current_humidity < 30:
            recommendations.append({
                'action': 'Increase humidity',
                'description': 'Use humidifier or reduce AC usage',
                'energy_impact': 'Low decrease',
                'comfort_impact': 'Medium improvement'
            })
        
        return {
            'current_conditions': {
                'temperature': current_temp,
                'humidity': current_humidity,
                'comfort_level': comfort_level
            },
            'comfort_zones': comfort_zones,
            'recommendations': recommendations,
            'energy_savings_potential_percent': energy_savings_potential,
            'comfort_score': _calculate_comfort_score(current_temp, current_humidity),
            'suggested_temperature_range': (22, 24) if comfort_level != 'optimal' else (current_temp - 1, current_temp + 1)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get comfort zone analysis: {str(e)}")


# ===== UTILITY FUNCTIONS =====

def _get_simulated_current_weather() -> CurrentWeather:
    """Generate simulated current weather data"""
    import math
    
    # Simulate Morocco climate (Casablanca area)
    current_hour = datetime.now().hour
    base_temp = 22  # Base temperature
    
    # Daily temperature variation
    if 6 <= current_hour <= 18:  # Daytime
        temp_variation = 8 * math.sin((current_hour - 6) * math.pi / 12)
    else:  # Nighttime
        temp_variation = -3
    
    temperature = base_temp + temp_variation + (hash(str(datetime.now().date())) % 10 - 5)
    
    return CurrentWeather(
        timestamp=datetime.utcnow(),
        temperature=round(temperature, 1),
        humidity=60 + (hash(str(current_hour)) % 20 - 10),  # 50-70% humidity
        description="Partly cloudy" if current_hour % 3 == 0 else "Clear sky",
        feels_like=round(temperature + 2, 1),
        wind_speed=round(5 + (hash(str(current_hour)) % 10), 1),
        city="Casablanca"
    )


def _get_simulated_forecast(hours: int) -> List[WeatherForecast]:
    """Generate simulated weather forecast"""
    import math
    
    forecast = []
    current_time = datetime.utcnow()
    base_temp = 22
    
    for i in range(hours):
        forecast_time = current_time + timedelta(hours=i)
        hour = forecast_time.hour
        
        # Daily temperature cycle
        if 6 <= hour <= 18:  # Daytime
            temp_variation = 8 * math.sin((hour - 6) * math.pi / 12)
        else:  # Nighttime
            temp_variation = -3
        
        temperature = base_temp + temp_variation + (hash(str(forecast_time.date())) % 6 - 3)
        
        forecast.append(WeatherForecast(
            timestamp=forecast_time,
            temperature=round(temperature, 1),
            humidity=60 + (hash(str(hour)) % 20 - 10),
            description="Clear sky" if hour % 4 != 0 else "Partly cloudy",
            precipitation_probability=0.1 if hour % 8 == 0 else 0.0,
            hour=hour
        ))
    
    return forecast


def _generate_hvac_recommendation(
    device: 'Device', 
    current_weather: CurrentWeather, 
    forecast: List[WeatherForecast]
) -> Optional[HVACRecommendation]:
    """Generate HVAC recommendation for a device"""
    
    current_temp = current_weather.temperature
    device_name = device.name
    device_id = device.id
    
    # Analyze forecast to predict needs
    avg_forecast_temp = sum(f.temperature for f in forecast[:6]) / len(forecast[:6])
    temp_trend = avg_forecast_temp - current_temp
    
    # Generate recommendations based on temperature
    if current_temp > 28:  # Very hot
        if 'AC' in device_name:
            return HVACRecommendation(
                device_id=device_id,
                device_name=device_name,
                action='cooling',
                target_temperature=24,
                power_adjustment=device.power_watts,
                reason=f'High temperature ({current_temp}°C) requires cooling',
                urgency='high',
                estimated_savings_dh=0.0  # No savings when cooling is necessary
            )
    
    elif current_temp > 26:  # Moderately hot
        if 'AC' in device_name:
            return HVACRecommendation(
                device_id=device_id,
                device_name=device_name,
                action='cooling',
                target_temperature=25,
                power_adjustment=int(device.power_watts * 0.7),  # Reduced power
                reason=f'Moderate temperature ({current_temp}°C) - efficient cooling',
                urgency='medium',
                estimated_savings_dh=2.5  # Some savings from reduced power
            )
    
    elif 20 <= current_temp <= 25:  # Comfortable range
        if temp_trend > 3:  # Getting warmer
            return HVACRecommendation(
                device_id=device_id,
                device_name=device_name,
                action='reduce',
                target_temperature=23,
                power_adjustment=int(device.power_watts * 0.3),
                reason='Pre-cooling before temperature rise',
                urgency='low',
                estimated_savings_dh=4.0  # Savings from pre-cooling strategy
            )
        else:
            return HVACRecommendation(
                device_id=device_id,
                device_name=device_name,
                action='off',
                target_temperature=None,
                power_adjustment=0,
                reason='Temperature in comfort zone - HVAC not needed',
                urgency='low',
                estimated_savings_dh=8.0  # Maximum savings by turning off
            )
    
    elif current_temp < 18:  # Cold
        if 'heating' in device_name.lower() or 'heater' in device_name.lower():
            return HVACRecommendation(
                device_id=device_id,
                device_name=device_name,
                action='heating',
                target_temperature=20,
                power_adjustment=device.power_watts,
                reason=f'Low temperature ({current_temp}°C) requires heating',
                urgency='medium',
                estimated_savings_dh=0.0
            )
    
    return None  # No recommendation needed


def _calculate_energy_impact(
    current_weather: CurrentWeather, 
    forecast: List[WeatherForecast]
) -> EnergyImpactAnalysis:
    """Calculate weather impact on energy consumption"""
    
    current_temp = current_weather.temperature
    
    # Calculate predicted consumption increase based on temperature
    if current_temp > 30:
        consumption_increase = 40  # 40% increase for very hot weather
    elif current_temp > 26:
        consumption_increase = 25  # 25% increase for hot weather
    elif current_temp < 16:
        consumption_increase = 30  # 30% increase for cold weather
    elif current_temp < 20:
        consumption_increase = 15  # 15% increase for cool weather
    else:
        consumption_increase = 0   # No increase in comfortable range
    
    # Calculate HVAC load factor
    comfort_range = (20, 25)
    if comfort_range[0] <= current_temp <= comfort_range[1]:
        hvac_load_factor = 0.2  # Minimal HVAC usage
    else:
        temp_deviation = min(abs(current_temp - comfort_range[0]), 
                           abs(current_temp - comfort_range[1]))
        hvac_load_factor = min(1.0, 0.2 + (temp_deviation * 0.1))
    
    # Generate 24-hour cooling demand forecast
    cooling_demand_24h = []
    for forecast_item in forecast:
        temp = forecast_item.temperature
        if temp > 25:
            demand_level = min(100, (temp - 25) * 20)  # Scale cooling demand
        else:
            demand_level = 0
        
        cooling_demand_24h.append({
            'hour': forecast_item.hour,
            'temperature': temp,
            'cooling_demand_percent': demand_level,
            'estimated_power_watts': demand_level * 20  # Estimate power needed
        })
    
    # Identify optimization opportunities
    optimization_opportunities = []
    
    # Check for pre-cooling opportunities
    hot_hours = [f for f in forecast if f.temperature > 28]
    if hot_hours:
        next_hot_hour = min(hot_hours, key=lambda x: x.timestamp)
        hours_until_hot = (next_hot_hour.timestamp - datetime.utcnow()).total_seconds() / 3600
        if 2 <= hours_until_hot <= 6:
            optimization_opportunities.append(
                f"Pre-cool buildings {int(hours_until_hot)} hours before peak heat"
            )
    
    # Check for off-peak optimization
    cool_hours = [f for f in forecast[:12] if f.temperature < 22]
    if cool_hours:
        optimization_opportunities.append(
            "Reduce HVAC usage during naturally cool periods"
        )
    
    # Check for thermal mass utilization
    if len([f for f in forecast[:6] if f.temperature > 26]) > 3:
        optimization_opportunities.append(
            "Utilize thermal mass for gradual cooling"
        )
    
    # Comfort vs cost analysis
    comfort_vs_cost = {
        'current_comfort_score': _calculate_comfort_score(current_temp, current_weather.humidity),
        'cost_to_maintain_comfort': _estimate_comfort_cost(current_temp),
        'savings_scenarios': [
            {
                'scenario': 'Increase temperature by 2°C',
                'comfort_impact': -15,  # 15% comfort reduction
                'cost_savings_percent': 20
            },
            {
                'scenario': 'Smart scheduling',
                'comfort_impact': -5,   # 5% comfort reduction
                'cost_savings_percent': 15
            },
            {
                'scenario': 'Pre-cooling strategy',
                'comfort_impact': 0,    # No comfort reduction
                'cost_savings_percent': 12
            }
        ]
    }
    
    return EnergyImpactAnalysis(
        current_temperature=current_temp,
        predicted_consumption_increase=consumption_increase,
        hvac_load_factor=hvac_load_factor,
        cooling_demand_24h=cooling_demand_24h,
        optimization_opportunities=optimization_opportunities,
        comfort_vs_cost_analysis=comfort_vs_cost
    )


def _calculate_comfort_score(temperature: float, humidity: float) -> float:
    """Calculate comfort score (0-100) based on temperature and humidity"""
    
    # Optimal ranges
    optimal_temp_range = (22, 24)
    optimal_humidity_range = (40, 60)
    
    # Temperature score
    if optimal_temp_range[0] <= temperature <= optimal_temp_range[1]:
        temp_score = 100
    else:
        temp_deviation = min(abs(temperature - optimal_temp_range[0]), 
                           abs(temperature - optimal_temp_range[1]))
        temp_score = max(0, 100 - (temp_deviation * 10))
    
    # Humidity score
    if optimal_humidity_range[0] <= humidity <= optimal_humidity_range[1]:
        humidity_score = 100
    else:
        humidity_deviation = min(abs(humidity - optimal_humidity_range[0]), 
                               abs(humidity - optimal_humidity_range[1]))
        humidity_score = max(0, 100 - (humidity_deviation * 2))
    
    # Combined score (temperature weighted more heavily)
    comfort_score = (temp_score * 0.7) + (humidity_score * 0.3)
    
    return round(comfort_score, 1)


def _estimate_comfort_cost(temperature: float) -> float:
    """Estimate daily cost to maintain comfort in DH"""
    
    # Base cost for HVAC operation
    base_cost = 15  # DH per day
    
    # Additional cost based on temperature deviation from comfort zone
    comfort_range = (20, 25)
    
    if comfort_range[0] <= temperature <= comfort_range[1]:
        return base_cost * 0.3  # Minimal cost in comfort zone
    
    temp_deviation = min(abs(temperature - comfort_range[0]), 
                        abs(temperature - comfort_range[1]))
    
    # Cost increases exponentially with temperature deviation
    additional_cost = base_cost * (temp_deviation * 0.4)
    
    return round(base_cost + additional_cost, 2)