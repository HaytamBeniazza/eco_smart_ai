"""
Optimizer Agent - Agent 3
Cost optimization and intelligent scheduling for energy efficiency
"""

import asyncio
import json
from datetime import datetime, timedelta, time
from typing import Dict, Any, List, Optional, Tuple
import math
from dataclasses import dataclass

from .base_agent import BaseAgent, AgentStatus
from core.message_broker import MessageType, MessagePriority, Message
from core.database import OptimizationResult, Device, ConsumptionLog
from core.config import settings, get_current_pricing_tier, calculate_energy_cost


@dataclass
class OptimizationSchedule:
    """Data class for device optimization schedule"""
    device_id: str
    device_name: str
    action: str  # 'on', 'off', 'reduce', 'delay'
    scheduled_time: datetime
    target_power: int
    priority: str
    reason: str
    estimated_savings_dh: float


@dataclass
class CostAnalysis:
    """Data class for cost analysis results"""
    current_cost_dh: float
    optimized_cost_dh: float
    savings_dh: float
    savings_percentage: float
    peak_usage_reduction: float
    off_peak_usage_increase: float


class OptimizerAgent(BaseAgent):
    """
    Optimizer Agent - Analyzes energy consumption and generates cost-optimal schedules
    
    Responsibilities:
    - Analyze energy pricing tiers (peak/normal/off-peak)
    - Generate optimal device schedules
    - Calculate potential cost savings
    - Coordinate with other agents for decisions
    """
    
    def __init__(self):
        super().__init__(
            agent_name="optimizer_agent",
            description="Cost optimization and intelligent scheduling for energy efficiency"
        )
        
        # Optimization state
        self.current_schedule = []
        self.optimization_enabled = True
        self.target_savings_percentage = 20.0  # Target 20% savings
        self.last_optimization = None
        
        # Energy pricing data
        self.pricing_tiers = settings.energy_pricing
        self.monthly_base_fee = settings.monthly_base_fee_dh
        
        # Device priority weights
        self.priority_weights = {
            'critical': 1.0,    # Never optimize critical devices
            'high': 0.8,        # Minimal optimization
            'medium': 0.6,      # Moderate optimization
            'low': 0.3          # Aggressive optimization
        }
        
        # Optimization constraints
        self.max_delay_hours = 4  # Maximum delay for low-priority devices
        self.comfort_temp_range = (20, 26)  # Acceptable temperature range
        self.peak_hours = self.pricing_tiers['peak']['hours']
        self.off_peak_hours = self.pricing_tiers['off_peak']['hours']
        
        # Performance metrics
        self.optimization_stats = {
            'optimizations_performed': 0,
            'total_savings_calculated': 0.0,
            'schedules_generated': 0,
            'peak_reductions_achieved': 0,
            'last_optimization_time': None
        }
        
        # Learning data for future improvements
        self.historical_performance = []
        
        self.logger.info("Optimizer Agent initialized")
    
    async def initialize(self):
        """Initialize agent-specific resources"""
        try:
            self.logger.info("Initializing Optimizer Agent...")
            
            # Load historical optimization data
            await self._load_historical_performance()
            
            # Initialize optimization models
            await self._initialize_optimization_models()
            
            self.logger.info("Optimizer Agent initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize Optimizer Agent: {e}")
            raise
    
    async def execute_cycle(self):
        """Execute one optimization cycle"""
        try:
            if not self.optimization_enabled:
                self.logger.debug("Optimization disabled, skipping cycle")
                return
            
            # Get current consumption data
            consumption_data = await self._get_current_consumption_data()
            
            if not consumption_data:
                self.logger.warning("No consumption data available for optimization")
                return
            
            # Get weather forecast for energy predictions
            weather_data = await self._get_weather_forecast()
            
            # Perform cost analysis
            cost_analysis = await self._analyze_current_costs(consumption_data)
            
            # Generate optimization schedule
            optimization_schedule = await self._generate_optimization_schedule(
                consumption_data, weather_data, cost_analysis
            )
            
            # Calculate potential savings
            savings_analysis = await self._calculate_savings_potential(
                consumption_data, optimization_schedule
            )
            
            # Send optimization results to Controller Agent
            if optimization_schedule:
                await self._send_optimization_to_controller(optimization_schedule, savings_analysis)
            
            # Broadcast optimization status to all agents
            await self._broadcast_optimization_status(cost_analysis, savings_analysis)
            
            # Store optimization results
            await self._store_optimization_results(cost_analysis, savings_analysis)
            
            # Update statistics
            self.optimization_stats['optimizations_performed'] += 1
            self.optimization_stats['last_optimization_time'] = datetime.utcnow()
            
            if savings_analysis.savings_dh > 0:
                self.optimization_stats['total_savings_calculated'] += savings_analysis.savings_dh
            
        except Exception as e:
            self.logger.error(f"Error in optimization cycle: {e}")
            raise
    
    async def handle_message(self, message: Message):
        """Handle incoming messages from other agents"""
        try:
            self.logger.debug(f"Received message: {message.type.value} from {message.from_agent}")
            
            if message.type == MessageType.CONSUMPTION_UPDATE:
                await self._handle_consumption_update(message.content)
            
            elif message.type == MessageType.WEATHER_UPDATE:
                await self._handle_weather_update(message.content)
            
            elif message.type == MessageType.TEMPERATURE_FORECAST:
                await self._handle_temperature_forecast(message.content)
            
            elif message.type == MessageType.EXECUTION_RESULT:
                await self._handle_execution_result(message.content)
            
            elif message.type == MessageType.MANUAL_OVERRIDE:
                await self._handle_manual_override(message.content)
            
            elif message.type == MessageType.SYSTEM_STATUS:
                await self._send_optimizer_status(message.from_agent)
            
            else:
                self.logger.debug(f"Unhandled message type: {message.type.value}")
                
        except Exception as e:
            self.logger.error(f"Error handling message: {e}")
    
    async def cleanup(self):
        """Cleanup agent resources"""
        self.logger.info("Cleaning up Optimizer Agent resources")
        self.current_schedule.clear()
        self.historical_performance.clear()
    
    def get_capabilities(self) -> List[str]:
        """Return agent capabilities"""
        return [
            "cost_optimization",
            "intelligent_scheduling",
            "peak_load_management",
            "savings_calculation",
            "device_prioritization",
            "energy_arbitrage"
        ]
    
    def get_execution_interval(self) -> float:
        """Return execution interval (5 minutes for active optimization)"""
        return 300  # 5 minutes
    
    # ===== OPTIMIZATION CORE METHODS =====
    
    async def _get_current_consumption_data(self) -> Optional[Dict[str, Any]]:
        """Get current consumption data from database"""
        try:
            session = self.get_db_session()
            try:
                # Get latest consumption for each device
                devices = session.query(Device).all()
                device_data = {}
                
                for device in devices:
                    latest_log = session.query(ConsumptionLog).filter(
                        ConsumptionLog.device_id == device.id
                    ).order_by(ConsumptionLog.timestamp.desc()).first()
                    
                    if latest_log:
                        device_data[device.id] = {
                            'device': device,
                            'current_power': latest_log.power_watts,
                            'status': latest_log.status,
                            'last_reading': latest_log.timestamp,
                            'temperature': latest_log.temperature,
                            'efficiency': latest_log.efficiency_rating
                        }
                
                if device_data:
                    total_consumption = sum(data['current_power'] for data in device_data.values())
                    return {
                        'devices': device_data,
                        'total_consumption': total_consumption,
                        'timestamp': datetime.utcnow()
                    }
                
            finally:
                session.close()
                
        except Exception as e:
            self.logger.error(f"Failed to get consumption data: {e}")
        
        return None
    
    async def _get_weather_forecast(self) -> Optional[Dict[str, Any]]:
        """Get weather forecast data (simplified for optimization)"""
        # In a real implementation, this would get data from Weather Agent
        # For now, we'll use basic temperature assumptions
        current_hour = datetime.now().hour
        
        # Predict next 24 hours based on typical patterns
        forecast = []
        for i in range(24):
            hour = (current_hour + i) % 24
            if 6 <= hour <= 18:  # Daytime
                temp = 25 + 5 * math.sin((hour - 6) * math.pi / 12)
            else:  # Nighttime
                temp = 20 - 3 * math.cos((hour - 18) * math.pi / 12)
            
            forecast.append({
                'hour': hour,
                'temperature': temp,
                'cooling_needed': temp > 24,
                'heating_needed': temp < 18
            })
        
        return {'forecast': forecast}
    
    async def _analyze_current_costs(self, consumption_data: Dict[str, Any]) -> CostAnalysis:
        """Analyze current energy costs and identify optimization opportunities"""
        try:
            current_hour = datetime.now().hour
            current_pricing = get_current_pricing_tier(current_hour)
            
            # Calculate current hourly cost
            total_consumption_kw = consumption_data['total_consumption'] / 1000
            current_hourly_cost = total_consumption_kw * current_pricing['rate']
            
            # Project daily cost based on current consumption
            daily_cost = current_hourly_cost * 24
            
            # Estimate optimized cost (assuming 20% savings)
            optimized_daily_cost = daily_cost * 0.8
            savings = daily_cost - optimized_daily_cost
            savings_percentage = (savings / daily_cost * 100) if daily_cost > 0 else 0
            
            self.logger.debug(f"Cost analysis: Current {daily_cost:.2f} DH, Optimized {optimized_daily_cost:.2f} DH")
            
            return CostAnalysis(
                current_cost_dh=daily_cost,
                optimized_cost_dh=optimized_daily_cost,
                savings_dh=savings,
                savings_percentage=savings_percentage,
                peak_usage_reduction=0.25,  # Target 25% peak reduction
                off_peak_usage_increase=0.15  # 15% increase in off-peak usage
            )
            
        except Exception as e:
            self.logger.error(f"Error analyzing costs: {e}")
            return CostAnalysis(0, 0, 0, 0, 0, 0)
    
    async def _generate_optimization_schedule(self, 
                                            consumption_data: Dict[str, Any],
                                            weather_data: Dict[str, Any],
                                            cost_analysis: CostAnalysis) -> List[OptimizationSchedule]:
        """Generate optimal device schedule based on pricing and consumption"""
        try:
            schedule = []
            current_time = datetime.utcnow()
            devices = consumption_data['devices']
            
            for device_id, device_data in devices.items():
                device = device_data['device']
                current_power = device_data['current_power']
                current_status = device_data['status']
                
                # Skip critical devices
                if device.priority == 'critical':
                    continue
                
                # Skip devices that are already off
                if current_status == 'off' and current_power < 10:
                    continue
                
                # Generate optimization recommendations based on device type
                optimization = await self._optimize_device_schedule(
                    device, device_data, weather_data, current_time
                )
                
                if optimization:
                    schedule.append(optimization)
            
            # Sort schedule by priority and potential savings
            schedule.sort(key=lambda x: (x.priority == 'high', x.estimated_savings_dh), reverse=True)
            
            self.logger.info(f"Generated optimization schedule with {len(schedule)} recommendations")
            return schedule
            
        except Exception as e:
            self.logger.error(f"Error generating optimization schedule: {e}")
            return []
    
    async def _optimize_device_schedule(self,
                                      device: Device,
                                      device_data: Dict[str, Any],
                                      weather_data: Dict[str, Any],
                                      current_time: datetime) -> Optional[OptimizationSchedule]:
        """Optimize schedule for a specific device"""
        try:
            current_hour = current_time.hour
            current_power = device_data['current_power']
            
            # Device-specific optimization logic
            if device.usage_pattern == "temperature_dependent":
                return await self._optimize_hvac_device(device, device_data, weather_data, current_time)
            
            elif device.usage_pattern == "manual" and device.priority == "low":
                return await self._optimize_deferrable_device(device, device_data, current_time)
            
            elif device.usage_pattern == "evening_peak":
                return await self._optimize_entertainment_device(device, device_data, current_time)
            
            elif device.usage_pattern == "schedule_based":
                return await self._optimize_scheduled_device(device, device_data, current_time)
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error optimizing device {device.id}: {e}")
            return None
    
    async def _optimize_hvac_device(self,
                                   device: Device,
                                   device_data: Dict[str, Any],
                                   weather_data: Dict[str, Any],
                                   current_time: datetime) -> Optional[OptimizationSchedule]:
        """Optimize HVAC devices based on temperature and pricing"""
        current_hour = current_time.hour
        current_power = device_data['current_power']
        
        # Check if we're in peak hours
        if current_hour in self.peak_hours:
            # Peak hours - reduce HVAC usage if possible
            if current_power > device.power_watts * 0.5:
                target_power = int(device.power_watts * 0.7)  # Reduce to 70%
                estimated_savings = (current_power - target_power) / 1000 * self.pricing_tiers['peak']['rate_dh_kwh']
                
                return OptimizationSchedule(
                    device_id=device.id,
                    device_name=device.name,
                    action='reduce',
                    scheduled_time=current_time,
                    target_power=target_power,
                    priority='high',
                    reason='Peak hour HVAC reduction',
                    estimated_savings_dh=estimated_savings
                )
        
        # Check for pre-cooling opportunity before peak hours
        elif current_hour in [14, 15]:  # 2-3 PM, before peak
            if device.room == "living_room" and current_power < device.power_watts * 0.8:
                target_power = int(device.power_watts * 0.9)  # Pre-cool
                estimated_savings = 5.0  # Estimated savings from peak avoidance
                
                return OptimizationSchedule(
                    device_id=device.id,
                    device_name=device.name,
                    action='on',
                    scheduled_time=current_time,
                    target_power=target_power,
                    priority='medium',
                    reason='Pre-cooling before peak hours',
                    estimated_savings_dh=estimated_savings
                )
        
        return None
    
    async def _optimize_deferrable_device(self,
                                        device: Device,
                                        device_data: Dict[str, Any],
                                        current_time: datetime) -> Optional[OptimizationSchedule]:
        """Optimize deferrable devices like washing machine"""
        current_hour = current_time.hour
        current_power = device_data['current_power']
        
        # If device is running during peak hours, suggest delay
        if current_hour in self.peak_hours and current_power > 100:
            # Calculate next off-peak time
            next_off_peak = None
            for hour in range(24):
                check_hour = (current_hour + hour) % 24
                if check_hour in self.off_peak_hours:
                    next_off_peak = current_time.replace(hour=check_hour, minute=0) + timedelta(days=1 if check_hour <= current_hour else 0)
                    break
            
            if next_off_peak:
                # Calculate savings from peak to off-peak shift
                peak_cost = current_power / 1000 * self.pricing_tiers['peak']['rate_dh_kwh']
                off_peak_cost = current_power / 1000 * self.pricing_tiers['off_peak']['rate_dh_kwh']
                estimated_savings = peak_cost - off_peak_cost
                
                return OptimizationSchedule(
                    device_id=device.id,
                    device_name=device.name,
                    action='delay',
                    scheduled_time=next_off_peak,
                    target_power=0,  # Turn off now
                    priority='medium',
                    reason=f'Delay to off-peak hours ({next_off_peak.strftime("%H:%M")})',
                    estimated_savings_dh=estimated_savings
                )
        
        return None
    
    async def _optimize_entertainment_device(self,
                                           device: Device,
                                           device_data: Dict[str, Any],
                                           current_time: datetime) -> Optional[OptimizationSchedule]:
        """Optimize entertainment devices during peak hours"""
        current_hour = current_time.hour
        current_power = device_data['current_power']
        
        # Reduce entertainment device usage during peak hours
        if current_hour in self.peak_hours and current_power > 50:
            # Suggest reducing to standby mode
            standby_power = getattr(device, 'standby_power', 15)
            estimated_savings = (current_power - standby_power) / 1000 * self.pricing_tiers['peak']['rate_dh_kwh']
            
            return OptimizationSchedule(
                device_id=device.id,
                device_name=device.name,
                action='reduce',
                scheduled_time=current_time,
                target_power=standby_power,
                priority='low',
                reason='Reduce entertainment usage during peak hours',
                estimated_savings_dh=estimated_savings
            )
        
        return None
    
    async def _optimize_scheduled_device(self,
                                       device: Device,
                                       device_data: Dict[str, Any],
                                       current_time: datetime) -> Optional[OptimizationSchedule]:
        """Optimize schedule-based devices like lights"""
        current_hour = current_time.hour
        current_power = device_data['current_power']
        
        # Optimize lighting during peak hours
        if device.name == "LED Lighting System" and current_hour in self.peak_hours:
            if current_power > 40:  # If lights are on full
                dimmed_power = int(current_power * 0.6)  # Dim to 60%
                estimated_savings = (current_power - dimmed_power) / 1000 * self.pricing_tiers['peak']['rate_dh_kwh']
                
                return OptimizationSchedule(
                    device_id=device.id,
                    device_name=device.name,
                    action='reduce',
                    scheduled_time=current_time,
                    target_power=dimmed_power,
                    priority='medium',
                    reason='Dim lights during peak hours',
                    estimated_savings_dh=estimated_savings
                )
        
        return None
    
    async def _calculate_savings_potential(self,
                                         consumption_data: Dict[str, Any],
                                         optimization_schedule: List[OptimizationSchedule]) -> CostAnalysis:
        """Calculate potential savings from optimization schedule"""
        try:
            if not optimization_schedule:
                return CostAnalysis(0, 0, 0, 0, 0, 0)
            
            # Calculate current daily cost
            current_consumption = consumption_data['total_consumption']
            current_hour = datetime.now().hour
            current_rate = get_current_pricing_tier(current_hour)['rate']
            
            # Estimate daily cost assuming current consumption pattern
            daily_consumption_kwh = current_consumption * 24 / 1000
            current_daily_cost = daily_consumption_kwh * 1.2 + self.monthly_base_fee / 30  # Average rate
            
            # Calculate savings from schedule
            total_savings = sum(opt.estimated_savings_dh for opt in optimization_schedule)
            
            # Project optimized daily cost
            optimized_daily_cost = current_daily_cost - total_savings
            savings_percentage = (total_savings / current_daily_cost * 100) if current_daily_cost > 0 else 0
            
            # Calculate peak reduction potential
            peak_devices = [opt for opt in optimization_schedule if any(h in self.peak_hours for h in range(16, 22))]
            peak_reduction = len(peak_devices) / len(optimization_schedule) if optimization_schedule else 0
            
            self.logger.info(f"Calculated savings: {total_savings:.2f} DH ({savings_percentage:.1f}%)")
            
            return CostAnalysis(
                current_cost_dh=current_daily_cost,
                optimized_cost_dh=optimized_daily_cost,
                savings_dh=total_savings,
                savings_percentage=savings_percentage,
                peak_usage_reduction=peak_reduction,
                off_peak_usage_increase=0.1  # Estimated increase in off-peak usage
            )
            
        except Exception as e:
            self.logger.error(f"Error calculating savings potential: {e}")
            return CostAnalysis(0, 0, 0, 0, 0, 0)
    
    # ===== MESSAGE HANDLERS =====
    
    async def _handle_consumption_update(self, content: Dict[str, Any]):
        """Handle consumption update from Monitor Agent"""
        try:
            total_consumption = content.get('total_consumption_watts', 0)
            anomalies = content.get('anomalies', [])
            
            # If anomalies detected, trigger immediate optimization
            if anomalies and self.optimization_enabled:
                self.logger.info(f"Anomalies detected, triggering optimization cycle")
                await self.execute_cycle()
            
            # Log consumption for learning
            await self.log_decision(
                "consumption_analysis",
                {
                    'total_consumption': total_consumption,
                    'anomalies_count': len(anomalies),
                    'timestamp': datetime.utcnow().isoformat()
                }
            )
            
        except Exception as e:
            self.logger.error(f"Failed to handle consumption update: {e}")
    
    async def _handle_weather_update(self, content: Dict[str, Any]):
        """Handle weather update from Weather Agent"""
        try:
            current_temp = content.get('current_weather', {}).get('temperature', 22)
            hvac_recommendations = content.get('hvac_recommendations', {})
            
            # Use weather data for more accurate HVAC optimization
            if hvac_recommendations.get('current_action') in ['cooling', 'heating']:
                urgency = hvac_recommendations.get('urgency', 'low')
                
                if urgency == 'high' and self.optimization_enabled:
                    self.logger.info(f"High urgency weather condition, triggering optimization")
                    await self.execute_cycle()
            
        except Exception as e:
            self.logger.error(f"Failed to handle weather update: {e}")
    
    async def _handle_temperature_forecast(self, content: Dict[str, Any]):
        """Handle temperature forecast from Weather Agent"""
        try:
            recommendations = content.get('recommendations', {})
            urgency = content.get('urgency', 'low')
            
            if urgency in ['high', 'medium']:
                self.logger.info(f"Temperature forecast requires optimization attention")
                # Trigger optimization cycle with weather consideration
                await self.execute_cycle()
            
        except Exception as e:
            self.logger.error(f"Failed to handle temperature forecast: {e}")
    
    async def _handle_execution_result(self, content: Dict[str, Any]):
        """Handle execution result from Controller Agent"""
        try:
            device_id = content.get('device_id')
            success = content.get('success', False)
            actual_savings = content.get('actual_savings', 0)
            
            if success:
                self.optimization_stats['peak_reductions_achieved'] += 1
                
                # Learn from successful optimizations
                self.historical_performance.append({
                    'timestamp': datetime.utcnow(),
                    'device_id': device_id,
                    'success': success,
                    'actual_savings': actual_savings
                })
                
                # Keep only last 100 performance records
                if len(self.historical_performance) > 100:
                    self.historical_performance = self.historical_performance[-100:]
            
            self.logger.info(f"Optimization execution for {device_id}: {'Success' if success else 'Failed'}")
            
        except Exception as e:
            self.logger.error(f"Failed to handle execution result: {e}")
    
    async def _handle_manual_override(self, content: Dict[str, Any]):
        """Handle manual override from user interface"""
        try:
            action = content.get('action')
            device_id = content.get('device_id')
            
            if action == 'disable_optimization':
                self.optimization_enabled = False
                self.logger.info("Optimization disabled by manual override")
            elif action == 'enable_optimization':
                self.optimization_enabled = True
                self.logger.info("Optimization enabled by manual override")
            
            # Log the override
            await self.log_decision(
                "manual_override_handled",
                {
                    'action': action,
                    'device_id': device_id,
                    'timestamp': datetime.utcnow().isoformat()
                }
            )
            
        except Exception as e:
            self.logger.error(f"Failed to handle manual override: {e}")
    
    # ===== COMMUNICATION METHODS =====
    
    async def _send_optimization_to_controller(self,
                                             schedule: List[OptimizationSchedule],
                                             savings_analysis: CostAnalysis):
        """Send optimization schedule to Controller Agent"""
        try:
            schedule_data = {
                'timestamp': datetime.utcnow().isoformat(),
                'optimization_schedule': [
                    {
                        'device_id': opt.device_id,
                        'device_name': opt.device_name,
                        'action': opt.action,
                        'scheduled_time': opt.scheduled_time.isoformat(),
                        'target_power': opt.target_power,
                        'priority': opt.priority,
                        'reason': opt.reason,
                        'estimated_savings_dh': opt.estimated_savings_dh
                    }
                    for opt in schedule
                ],
                'savings_analysis': {
                    'current_cost_dh': savings_analysis.current_cost_dh,
                    'optimized_cost_dh': savings_analysis.optimized_cost_dh,
                    'savings_dh': savings_analysis.savings_dh,
                    'savings_percentage': savings_analysis.savings_percentage
                },
                'optimization_enabled': self.optimization_enabled
            }
            
            await self.send_message(
                "controller_agent",
                MessageType.OPTIMIZATION_RESULT,
                schedule_data,
                MessagePriority.HIGH
            )
            
            self.optimization_stats['schedules_generated'] += 1
            self.logger.info(f"Sent optimization schedule with {len(schedule)} recommendations")
            
        except Exception as e:
            self.logger.error(f"Failed to send optimization to controller: {e}")
    
    async def _broadcast_optimization_status(self,
                                           cost_analysis: CostAnalysis,
                                           savings_analysis: CostAnalysis):
        """Broadcast optimization status to all agents"""
        try:
            status_data = {
                'timestamp': datetime.utcnow().isoformat(),
                'optimization_enabled': self.optimization_enabled,
                'current_savings_percentage': savings_analysis.savings_percentage,
                'total_savings_dh': savings_analysis.savings_dh,
                'optimization_stats': self.optimization_stats,
                'cost_analysis': {
                    'current_cost_dh': cost_analysis.current_cost_dh,
                    'optimized_cost_dh': cost_analysis.optimized_cost_dh,
                    'peak_reduction': cost_analysis.peak_usage_reduction
                }
            }
            
            await self.broadcast_message(
                MessageType.COST_ANALYSIS,
                status_data,
                MessagePriority.MEDIUM
            )
            
        except Exception as e:
            self.logger.error(f"Failed to broadcast optimization status: {e}")
    
    async def _send_optimizer_status(self, requesting_agent: str):
        """Send optimizer status to requesting agent"""
        try:
            status_data = {
                'agent_name': self.agent_name,
                'optimization_enabled': self.optimization_enabled,
                'optimization_stats': self.optimization_stats,
                'current_schedule_count': len(self.current_schedule),
                'target_savings_percentage': self.target_savings_percentage,
                'historical_performance_count': len(self.historical_performance),
                'agent_health': self.get_status()
            }
            
            await self.send_message(
                requesting_agent,
                MessageType.SYSTEM_STATUS,
                status_data,
                MessagePriority.MEDIUM
            )
            
        except Exception as e:
            self.logger.error(f"Failed to send optimizer status: {e}")
    
    # ===== UTILITY METHODS =====
    
    async def _store_optimization_results(self,
                                        cost_analysis: CostAnalysis,
                                        savings_analysis: CostAnalysis):
        """Store optimization results in database"""
        try:
            session = self.get_db_session()
            try:
                result = OptimizationResult(
                    original_cost_dh=cost_analysis.current_cost_dh,
                    optimized_cost_dh=savings_analysis.optimized_cost_dh,
                    savings_dh=savings_analysis.savings_dh,
                    savings_percentage=savings_analysis.savings_percentage,
                    total_consumption_kwh=0,  # Would calculate from actual data
                    peak_consumption_kwh=0,   # Would calculate from actual data
                    off_peak_consumption_kwh=0,  # Would calculate from actual data
                    optimization_strategy="multi_agent_optimization"
                )
                
                session.add(result)
                session.commit()
                
                self.logger.debug(f"Stored optimization result: {savings_analysis.savings_dh:.2f} DH savings")
                
            finally:
                session.close()
                
        except Exception as e:
            self.logger.error(f"Failed to store optimization results: {e}")
    
    async def _load_historical_performance(self):
        """Load historical optimization performance"""
        try:
            session = self.get_db_session()
            try:
                # Get recent optimization results
                recent_results = session.query(OptimizationResult).order_by(
                    OptimizationResult.date.desc()
                ).limit(30).all()
                
                for result in recent_results:
                    self.historical_performance.append({
                        'timestamp': result.date,
                        'savings_percentage': result.savings_percentage,
                        'success': result.savings_dh > 0
                    })
                
                self.logger.info(f"Loaded {len(recent_results)} historical optimization records")
                
            finally:
                session.close()
                
        except Exception as e:
            self.logger.error(f"Failed to load historical performance: {e}")
    
    async def _initialize_optimization_models(self):
        """Initialize optimization models and algorithms"""
        try:
            # Initialize learning parameters based on historical performance
            if self.historical_performance:
                success_rate = sum(1 for p in self.historical_performance if p['success']) / len(self.historical_performance)
                avg_savings = sum(p.get('savings_percentage', 0) for p in self.historical_performance) / len(self.historical_performance)
                
                self.logger.info(f"Historical performance: {success_rate:.1%} success rate, {avg_savings:.1f}% avg savings")
                
                # Adjust target based on historical performance
                if success_rate > 0.8 and avg_savings > 15:
                    self.target_savings_percentage = min(25, avg_savings + 2)
                elif success_rate < 0.5:
                    self.target_savings_percentage = max(10, avg_savings - 2)
            
            self.logger.info(f"Optimization target set to {self.target_savings_percentage}% savings")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize optimization models: {e}")
    
    def get_current_optimization_summary(self) -> Dict[str, Any]:
        """Get current optimization summary for external access"""
        return {
            'optimization_enabled': self.optimization_enabled,
            'target_savings_percentage': self.target_savings_percentage,
            'current_schedule_count': len(self.current_schedule),
            'optimization_stats': self.optimization_stats,
            'last_optimization': self.last_optimization.isoformat() if self.last_optimization else None
        } 