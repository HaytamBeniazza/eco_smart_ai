"""
Energy Endpoints - Real-time energy monitoring and device control
"""

from fastapi import APIRouter, HTTPException, Query, Depends
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import desc, func

from core.database import get_db, Device, ConsumptionLog, OptimizationResult
from core.config import get_current_pricing_tier, calculate_energy_cost
from pydantic import BaseModel


# Response models
class DeviceStatus(BaseModel):
    device_id: str
    device_name: str
    current_power_watts: int
    status: str
    last_update: datetime
    room: str
    priority: str
    controllable: bool
    efficiency_rating: float
    temperature: Optional[float] = None


class EnergyConsumption(BaseModel):
    timestamp: datetime
    total_consumption_watts: int
    devices: List[DeviceStatus]
    cost_current_hour_dh: float
    pricing_tier: str
    anomalies: List[Dict[str, Any]]


class DailyEnergyReport(BaseModel):
    date: str
    total_consumption_kwh: float
    total_cost_dh: float
    peak_consumption_kwh: float
    off_peak_consumption_kwh: float
    average_cost_per_kwh: float
    savings_achieved_dh: float
    top_consuming_devices: List[Dict[str, Any]]


class EnergyTrend(BaseModel):
    date: str
    consumption_kwh: float
    cost_dh: float
    savings_dh: float
    efficiency_rating: float


router = APIRouter(prefix="/api/energy", tags=["energy"])


@router.get("/current", response_model=EnergyConsumption)
async def get_current_energy_consumption(db: Session = Depends(get_db)):
    """Get current real-time energy consumption"""
    try:
        # Get all devices with their latest consumption
        devices = db.query(Device).all()
        device_statuses = []
        total_consumption = 0
        anomalies = []
        
        for device in devices:
            # Get latest consumption log
            latest_log = db.query(ConsumptionLog).filter(
                ConsumptionLog.device_id == device.id
            ).order_by(ConsumptionLog.timestamp.desc()).first()
            
            if latest_log:
                device_status = DeviceStatus(
                    device_id=device.id,
                    device_name=device.name,
                    current_power_watts=latest_log.power_watts,
                    status=latest_log.status,
                    last_update=latest_log.timestamp,
                    room=device.room,
                    priority=device.priority,
                    controllable=device.controllable,
                    efficiency_rating=latest_log.efficiency_rating,
                    temperature=latest_log.temperature
                )
                device_statuses.append(device_status)
                total_consumption += latest_log.power_watts
                
                # Check for anomalies (simplified)
                if latest_log.power_watts > device.power_watts * 1.2:
                    anomalies.append({
                        'device_id': device.id,
                        'device_name': device.name,
                        'type': 'high_consumption',
                        'current_power': latest_log.power_watts,
                        'expected_power': device.power_watts,
                        'severity': 'medium'
                    })
        
        # Calculate current cost
        current_hour = datetime.now().hour
        pricing_tier = get_current_pricing_tier(current_hour)
        cost_current_hour = (total_consumption / 1000) * pricing_tier['rate']
        
        return EnergyConsumption(
            timestamp=datetime.utcnow(),
            total_consumption_watts=total_consumption,
            devices=device_statuses,
            cost_current_hour_dh=cost_current_hour,
            pricing_tier=pricing_tier['tier'],
            anomalies=anomalies
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get current consumption: {str(e)}")


@router.get("/devices", response_model=List[DeviceStatus])
async def get_all_device_statuses(db: Session = Depends(get_db)):
    """Get status of all devices"""
    try:
        devices = db.query(Device).all()
        device_statuses = []
        
        for device in devices:
            latest_log = db.query(ConsumptionLog).filter(
                ConsumptionLog.device_id == device.id
            ).order_by(ConsumptionLog.timestamp.desc()).first()
            
            if latest_log:
                device_status = DeviceStatus(
                    device_id=device.id,
                    device_name=device.name,
                    current_power_watts=latest_log.power_watts,
                    status=latest_log.status,
                    last_update=latest_log.timestamp,
                    room=device.room,
                    priority=device.priority,
                    controllable=device.controllable,
                    efficiency_rating=latest_log.efficiency_rating,
                    temperature=latest_log.temperature
                )
                device_statuses.append(device_status)
        
        return device_statuses
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get device statuses: {str(e)}")


@router.get("/devices/{device_id}", response_model=DeviceStatus)
async def get_device_status(device_id: str, db: Session = Depends(get_db)):
    """Get status of a specific device"""
    try:
        device = db.query(Device).filter(Device.id == device_id).first()
        if not device:
            raise HTTPException(status_code=404, detail="Device not found")
        
        latest_log = db.query(ConsumptionLog).filter(
            ConsumptionLog.device_id == device.id
        ).order_by(ConsumptionLog.timestamp.desc()).first()
        
        if not latest_log:
            raise HTTPException(status_code=404, detail="No consumption data found for device")
        
        return DeviceStatus(
            device_id=device.id,
            device_name=device.name,
            current_power_watts=latest_log.power_watts,
            status=latest_log.status,
            last_update=latest_log.timestamp,
            room=device.room,
            priority=device.priority,
            controllable=device.controllable,
            efficiency_rating=latest_log.efficiency_rating,
            temperature=latest_log.temperature
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get device status: {str(e)}")


@router.get("/consumption/history/{device_id}")
async def get_device_consumption_history(
    device_id: str,
    hours: int = Query(24, description="Number of hours of history to retrieve"),
    db: Session = Depends(get_db)
):
    """Get consumption history for a specific device"""
    try:
        device = db.query(Device).filter(Device.id == device_id).first()
        if not device:
            raise HTTPException(status_code=404, detail="Device not found")
        
        # Get consumption logs from the last N hours
        since_time = datetime.utcnow() - timedelta(hours=hours)
        
        logs = db.query(ConsumptionLog).filter(
            ConsumptionLog.device_id == device_id,
            ConsumptionLog.timestamp >= since_time
        ).order_by(ConsumptionLog.timestamp.asc()).all()
        
        history_data = []
        for log in logs:
            current_hour = log.timestamp.hour
            pricing = get_current_pricing_tier(current_hour)
            cost = (log.power_watts / 1000) * pricing['rate']
            
            history_data.append({
                'timestamp': log.timestamp.isoformat(),
                'power_watts': log.power_watts,
                'status': log.status,
                'temperature': log.temperature,
                'efficiency_rating': log.efficiency_rating,
                'cost_dh': cost,
                'pricing_tier': pricing['tier']
            })
        
        return {
            'device_id': device_id,
            'device_name': device.name,
            'period_hours': hours,
            'total_records': len(history_data),
            'history': history_data
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get consumption history: {str(e)}")


@router.get("/consumption/total")
async def get_total_consumption_history(
    hours: int = Query(24, description="Number of hours of history to retrieve"),
    db: Session = Depends(get_db)
):
    """Get total consumption history across all devices"""
    try:
        since_time = datetime.utcnow() - timedelta(hours=hours)
        
        # Query aggregated consumption by hour
        hourly_consumption = db.query(
            func.date_trunc('hour', ConsumptionLog.timestamp).label('hour'),
            func.sum(ConsumptionLog.power_watts).label('total_power')
        ).filter(
            ConsumptionLog.timestamp >= since_time
        ).group_by(
            func.date_trunc('hour', ConsumptionLog.timestamp)
        ).order_by('hour').all()
        
        consumption_data = []
        total_cost = 0
        
        for hour_data in hourly_consumption:
            hour = hour_data.hour
            total_power = hour_data.total_power or 0
            
            # Calculate cost for this hour
            pricing = get_current_pricing_tier(hour.hour)
            hourly_cost = (total_power / 1000) * pricing['rate']
            total_cost += hourly_cost
            
            consumption_data.append({
                'timestamp': hour.isoformat(),
                'total_power_watts': total_power,
                'consumption_kwh': total_power / 1000,
                'cost_dh': hourly_cost,
                'pricing_tier': pricing['tier']
            })
        
        return {
            'period_hours': hours,
            'total_cost_dh': total_cost,
            'total_consumption_kwh': sum(d['consumption_kwh'] for d in consumption_data),
            'average_power_watts': sum(d['total_power_watts'] for d in consumption_data) / len(consumption_data) if consumption_data else 0,
            'hourly_data': consumption_data
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get total consumption history: {str(e)}")


@router.get("/cost/current")
async def get_current_energy_cost():
    """Get current energy pricing information"""
    try:
        current_hour = datetime.now().hour
        pricing = get_current_pricing_tier(current_hour)
        
        # Get next tier change
        next_hour = (current_hour + 1) % 24
        next_pricing = get_current_pricing_tier(next_hour)
        
        return {
            'current_time': datetime.now().isoformat(),
            'current_tier': pricing['tier'],
            'current_rate_dh_kwh': pricing['rate'],
            'next_hour_tier': next_pricing['tier'],
            'next_hour_rate_dh_kwh': next_pricing['rate'],
            'tier_change_in_minutes': 60 - datetime.now().minute,
            'all_pricing_tiers': {
                'peak': {
                    'hours': [16, 17, 18, 19, 20, 21],
                    'rate_dh_kwh': 1.65,
                    'description': "Peak hours (4 PM - 9 PM)"
                },
                'normal': {
                    'hours': [6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 22, 23],
                    'rate_dh_kwh': 1.20,
                    'description': "Normal hours"
                },
                'off_peak': {
                    'hours': [0, 1, 2, 3, 4, 5],
                    'rate_dh_kwh': 0.85,
                    'description': "Off-peak hours (midnight - 5 AM)"
                }
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get current pricing: {str(e)}")


@router.get("/cost/projection")
async def get_cost_projection(
    hours: int = Query(24, description="Number of hours to project"),
    db: Session = Depends(get_db)
):
    """Get energy cost projection based on current consumption patterns"""
    try:
        # Get current average consumption
        recent_logs = db.query(ConsumptionLog).filter(
            ConsumptionLog.timestamp >= datetime.utcnow() - timedelta(hours=1)
        ).all()
        
        if not recent_logs:
            raise HTTPException(status_code=404, detail="No recent consumption data available")
        
        # Calculate average consumption per device
        device_averages = {}
        for log in recent_logs:
            if log.device_id not in device_averages:
                device_averages[log.device_id] = []
            device_averages[log.device_id].append(log.power_watts)
        
        # Calculate averages
        for device_id in device_averages:
            device_averages[device_id] = sum(device_averages[device_id]) / len(device_averages[device_id])
        
        # Project costs for next N hours
        projections = []
        total_projected_cost = 0
        current_time = datetime.now()
        
        for i in range(hours):
            projection_time = current_time + timedelta(hours=i)
            pricing = get_current_pricing_tier(projection_time.hour)
            
            # Estimate consumption (simplified)
            estimated_consumption = sum(device_averages.values())
            
            # Apply time-of-day patterns
            if 6 <= projection_time.hour <= 22:  # Daytime
                estimated_consumption *= 1.1  # 10% higher during day
            else:  # Nighttime
                estimated_consumption *= 0.8  # 20% lower at night
            
            hourly_cost = (estimated_consumption / 1000) * pricing['rate']
            total_projected_cost += hourly_cost
            
            projections.append({
                'hour': projection_time.strftime('%Y-%m-%d %H:00'),
                'estimated_consumption_watts': int(estimated_consumption),
                'estimated_consumption_kwh': estimated_consumption / 1000,
                'pricing_tier': pricing['tier'],
                'rate_dh_kwh': pricing['rate'],
                'estimated_cost_dh': hourly_cost
            })
        
        return {
            'projection_period_hours': hours,
            'total_projected_cost_dh': total_projected_cost,
            'average_hourly_cost_dh': total_projected_cost / hours,
            'hourly_projections': projections
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate cost projection: {str(e)}")


@router.get("/analytics/daily/{date}", response_model=DailyEnergyReport)
async def get_daily_energy_report(date: str, db: Session = Depends(get_db)):
    """Get comprehensive daily energy report"""
    try:
        # Parse date
        try:
            report_date = datetime.strptime(date, '%Y-%m-%d').date()
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
        
        # Get all consumption logs for the day
        start_time = datetime.combine(report_date, datetime.min.time())
        end_time = start_time + timedelta(days=1)
        
        daily_logs = db.query(ConsumptionLog).filter(
            ConsumptionLog.timestamp >= start_time,
            ConsumptionLog.timestamp < end_time
        ).all()
        
        if not daily_logs:
            raise HTTPException(status_code=404, detail=f"No consumption data found for {date}")
        
        # Calculate metrics
        total_consumption_kwh = 0
        total_cost_dh = 0
        peak_consumption_kwh = 0
        off_peak_consumption_kwh = 0
        device_consumption = {}
        
        for log in daily_logs:
            consumption_kwh = log.power_watts / 1000
            total_consumption_kwh += consumption_kwh
            
            # Calculate cost
            pricing = get_current_pricing_tier(log.timestamp.hour)
            cost = consumption_kwh * pricing['rate']
            total_cost_dh += cost
            
            # Categorize by pricing tier
            if pricing['tier'] == 'peak':
                peak_consumption_kwh += consumption_kwh
            elif pricing['tier'] == 'off_peak':
                off_peak_consumption_kwh += consumption_kwh
            
            # Track device consumption
            device_id = log.device_id
            if device_id not in device_consumption:
                device_consumption[device_id] = {'consumption_kwh': 0, 'cost_dh': 0}
            device_consumption[device_id]['consumption_kwh'] += consumption_kwh
            device_consumption[device_id]['cost_dh'] += cost
        
        # Get top consuming devices
        top_devices = []
        for device_id, data in sorted(device_consumption.items(), 
                                    key=lambda x: x[1]['consumption_kwh'], 
                                    reverse=True)[:5]:
            device = db.query(Device).filter(Device.id == device_id).first()
            if device:
                top_devices.append({
                    'device_id': device_id,
                    'device_name': device.name,
                    'consumption_kwh': round(data['consumption_kwh'], 2),
                    'cost_dh': round(data['cost_dh'], 2),
                    'percentage_of_total': round((data['consumption_kwh'] / total_consumption_kwh) * 100, 1)
                })
        
        # Get optimization savings for the day
        optimization_results = db.query(OptimizationResult).filter(
            OptimizationResult.date >= start_time,
            OptimizationResult.date < end_time
        ).all()
        
        savings_achieved_dh = sum(result.savings_dh for result in optimization_results)
        
        return DailyEnergyReport(
            date=date,
            total_consumption_kwh=round(total_consumption_kwh, 2),
            total_cost_dh=round(total_cost_dh, 2),
            peak_consumption_kwh=round(peak_consumption_kwh, 2),
            off_peak_consumption_kwh=round(off_peak_consumption_kwh, 2),
            average_cost_per_kwh=round(total_cost_dh / total_consumption_kwh, 2) if total_consumption_kwh > 0 else 0,
            savings_achieved_dh=round(savings_achieved_dh, 2),
            top_consuming_devices=top_devices
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate daily report: {str(e)}")


@router.get("/analytics/trends", response_model=List[EnergyTrend])
async def get_energy_trends(
    days: int = Query(7, description="Number of days of trend data"),
    db: Session = Depends(get_db)
):
    """Get energy consumption and cost trends"""
    try:
        end_date = datetime.utcnow().date()
        start_date = end_date - timedelta(days=days-1)
        
        trends = []
        
        for i in range(days):
            current_date = start_date + timedelta(days=i)
            start_time = datetime.combine(current_date, datetime.min.time())
            end_time = start_time + timedelta(days=1)
            
            # Get daily consumption
            daily_logs = db.query(ConsumptionLog).filter(
                ConsumptionLog.timestamp >= start_time,
                ConsumptionLog.timestamp < end_time
            ).all()
            
            # Calculate daily metrics
            daily_consumption_kwh = sum(log.power_watts / 1000 for log in daily_logs)
            daily_cost_dh = 0
            
            for log in daily_logs:
                pricing = get_current_pricing_tier(log.timestamp.hour)
                daily_cost_dh += (log.power_watts / 1000) * pricing['rate']
            
            # Get daily savings
            optimization_results = db.query(OptimizationResult).filter(
                OptimizationResult.date >= start_time,
                OptimizationResult.date < end_time
            ).all()
            
            daily_savings_dh = sum(result.savings_dh for result in optimization_results)
            
            # Calculate efficiency rating (simplified)
            efficiency_rating = 1.0
            if daily_consumption_kwh > 0:
                average_efficiency = sum(log.efficiency_rating for log in daily_logs) / len(daily_logs) if daily_logs else 1.0
                efficiency_rating = average_efficiency
            
            trends.append(EnergyTrend(
                date=current_date.strftime('%Y-%m-%d'),
                consumption_kwh=round(daily_consumption_kwh, 2),
                cost_dh=round(daily_cost_dh, 2),
                savings_dh=round(daily_savings_dh, 2),
                efficiency_rating=round(efficiency_rating, 2)
            ))
        
        return trends
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get energy trends: {str(e)}")


@router.get("/analytics/summary")
async def get_energy_analytics_summary(db: Session = Depends(get_db)):
    """Get overall energy analytics summary"""
    try:
        # Current month data
        now = datetime.utcnow()
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        # Get monthly consumption
        monthly_logs = db.query(ConsumptionLog).filter(
            ConsumptionLog.timestamp >= month_start
        ).all()
        
        monthly_consumption_kwh = sum(log.power_watts / 1000 for log in monthly_logs)
        monthly_cost_dh = 0
        
        for log in monthly_logs:
            pricing = get_current_pricing_tier(log.timestamp.hour)
            monthly_cost_dh += (log.power_watts / 1000) * pricing['rate']
        
        # Get monthly savings
        monthly_optimizations = db.query(OptimizationResult).filter(
            OptimizationResult.date >= month_start
        ).all()
        
        monthly_savings_dh = sum(result.savings_dh for result in monthly_optimizations)
        
        # Calculate some key metrics
        days_in_month = (now - month_start).days + 1
        daily_average_consumption = monthly_consumption_kwh / days_in_month
        daily_average_cost = monthly_cost_dh / days_in_month
        
        # Get current day consumption
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        today_logs = db.query(ConsumptionLog).filter(
            ConsumptionLog.timestamp >= today_start
        ).all()
        
        today_consumption_kwh = sum(log.power_watts / 1000 for log in today_logs)
        
        return {
            'current_month': now.strftime('%Y-%m'),
            'monthly_consumption_kwh': round(monthly_consumption_kwh, 2),
            'monthly_cost_dh': round(monthly_cost_dh, 2),
            'monthly_savings_dh': round(monthly_savings_dh, 2),
            'daily_average_consumption_kwh': round(daily_average_consumption, 2),
            'daily_average_cost_dh': round(daily_average_cost, 2),
            'today_consumption_kwh': round(today_consumption_kwh, 2),
            'consumption_vs_average': round((today_consumption_kwh / daily_average_consumption - 1) * 100, 1) if daily_average_consumption > 0 else 0,
            'total_devices': db.query(Device).count(),
            'total_optimization_runs': len(monthly_optimizations),
            'average_savings_percentage': round((monthly_savings_dh / (monthly_cost_dh + monthly_savings_dh)) * 100, 1) if (monthly_cost_dh + monthly_savings_dh) > 0 else 0
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get analytics summary: {str(e)}")