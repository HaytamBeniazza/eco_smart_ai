"""
Monitor Agent - Agent 1
Real-time energy consumption tracking and anomaly detection
"""

import random
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import json

from .base_agent import BaseAgent, AgentStatus
from core.message_broker import MessageType, MessagePriority, Message
from core.database import Device, ConsumptionLog
from core.config import settings


class MonitorAgent(BaseAgent):
    """
    Monitor Agent - Tracks real-time energy consumption and detects anomalies
    
    Responsibilities:
    - Simulate IoT device readings every 30 seconds
    - Detect consumption anomalies (>20% variance)
    - Store consumption data in SQLite
    - Broadcast updates to other agents
    """
    
    def __init__(self):
        super().__init__(
            agent_name="monitor_agent",
            description="Real-time energy consumption tracking and anomaly detection"
        )
        
        # Device simulation state
        self.devices = {}
        self.device_history = {}  # For anomaly detection
        self.anomaly_threshold = 0.20  # 20% variance threshold
        self.simulation_patterns = {}
        
        # Monitoring statistics
        self.monitoring_stats = {
            'devices_monitored': 0,
            'anomalies_detected': 0,
            'total_readings': 0,
            'last_reading_time': None
        }
        
        self.logger.info("Monitor Agent initialized")
    
    async def initialize(self):
        """Initialize agent-specific resources"""
        try:
            self.logger.info("Initializing Monitor Agent...")
            
            # Load devices from database
            await self._load_devices()
            
            # Initialize device simulation patterns
            self._initialize_simulation_patterns()
            
            # Initialize device history for anomaly detection
            self._initialize_device_history()
            
            self.logger.info(f"Monitor Agent initialized with {len(self.devices)} devices")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize Monitor Agent: {e}")
            raise
    
    async def execute_cycle(self):
        """Execute one monitoring cycle"""
        try:
            # Read all device consumptions
            device_readings = await self._read_all_devices()
            
            # Store readings in database
            await self._store_consumption_data(device_readings)
            
            # Check for anomalies
            anomalies = await self._detect_anomalies(device_readings)
            
            # Broadcast consumption update to other agents
            await self._broadcast_consumption_update(device_readings, anomalies)
            
            # Update statistics
            self.monitoring_stats['total_readings'] += len(device_readings)
            self.monitoring_stats['last_reading_time'] = datetime.utcnow()
            
            if anomalies:
                self.monitoring_stats['anomalies_detected'] += len(anomalies)
                
        except Exception as e:
            self.logger.error(f"Error in monitor cycle: {e}")
            raise
    
    async def handle_message(self, message: Message):
        """Handle incoming messages from other agents"""
        try:
            self.logger.debug(f"Received message: {message.type.value} from {message.from_agent}")
            
            if message.type == MessageType.DEVICE_STATUS_CHANGE:
                await self._handle_device_status_change(message.content)
            
            elif message.type == MessageType.MANUAL_OVERRIDE:
                await self._handle_manual_override(message.content)
                
            elif message.type == MessageType.SYSTEM_STATUS:
                # Respond with monitoring status
                await self._send_monitoring_status(message.from_agent)
            
            else:
                self.logger.debug(f"Unhandled message type: {message.type.value}")
                
        except Exception as e:
            self.logger.error(f"Error handling message: {e}")
    
    async def cleanup(self):
        """Cleanup agent resources"""
        self.logger.info("Cleaning up Monitor Agent resources")
        self.devices.clear()
        self.device_history.clear()
    
    def get_capabilities(self) -> List[str]:
        """Return agent capabilities"""
        return [
            "device_monitoring",
            "anomaly_detection", 
            "consumption_tracking",
            "real_time_alerts",
            "device_simulation"
        ]
    
    def get_execution_interval(self) -> float:
        """Return execution interval (30 seconds as specified)"""
        return settings.agent_poll_interval  # 30 seconds
    
    # ===== DEVICE MONITORING METHODS =====
    
    async def _load_devices(self):
        """Load devices from database"""
        session = self.get_db_session()
        try:
            devices = session.query(Device).all()
            for device in devices:
                self.devices[device.id] = {
                    'device': device,
                    'current_power': 0,
                    'current_status': 'off',
                    'last_reading': None,
                    'temperature': None  # For AC units
                }
            
            self.monitoring_stats['devices_monitored'] = len(self.devices)
            self.logger.info(f"Loaded {len(self.devices)} devices for monitoring")
            
        finally:
            session.close()
    
    def _initialize_simulation_patterns(self):
        """Initialize realistic consumption patterns for each device"""
        current_hour = datetime.now().hour
        
        for device_id, device_data in self.devices.items():
            device = device_data['device']
            pattern = device.usage_pattern
            
            if pattern == "temperature_dependent":
                # AC units - higher consumption in hot hours
                base_consumption = device.power_watts
                if 12 <= current_hour <= 18:  # Hot afternoon
                    consumption = base_consumption * random.uniform(0.8, 1.0)
                    status = 'on'
                elif 19 <= current_hour <= 23:  # Evening
                    consumption = base_consumption * random.uniform(0.6, 0.8)
                    status = 'on' 
                else:  # Night/early morning
                    consumption = base_consumption * random.uniform(0.1, 0.3)
                    status = 'standby' if random.random() > 0.7 else 'off'
                    
            elif pattern == "schedule_based":
                # Lights, bedroom AC - based on typical schedules
                if device.room == "bedroom" and 22 <= current_hour or current_hour <= 6:
                    consumption = device.power_watts * random.uniform(0.7, 1.0)
                    status = 'on'
                elif 18 <= current_hour <= 23:  # Evening
                    consumption = device.power_watts * random.uniform(0.5, 0.8)
                    status = 'on'
                else:
                    consumption = device.power_watts * random.uniform(0.0, 0.2)
                    status = 'off'
                    
            elif pattern == "constant":
                # Refrigerator - always on with minor variations
                consumption = device.power_watts * random.uniform(0.8, 1.1)
                status = 'on'
                
            elif pattern == "evening_peak":
                # TV & Entertainment - peak usage in evening
                if 19 <= current_hour <= 23:
                    consumption = device.power_watts * random.uniform(0.8, 1.0)
                    status = 'on'
                elif 7 <= current_hour <= 9:  # Morning news
                    consumption = device.power_watts * random.uniform(0.3, 0.5)
                    status = 'on'
                else:
                    consumption = device.power_watts * random.uniform(0.0, 0.1)
                    status = 'standby'
                    
            elif pattern == "manual":
                # Washing machine - random usage
                if random.random() < 0.1:  # 10% chance of being on
                    consumption = device.power_watts * random.uniform(0.8, 1.0)
                    status = 'on'
                else:
                    consumption = 0
                    status = 'off'
            else:
                # Default pattern
                consumption = device.power_watts * random.uniform(0.3, 0.7)
                status = 'on' if consumption > device.power_watts * 0.1 else 'off'
            
            # Store simulation state
            self.simulation_patterns[device_id] = {
                'base_consumption': consumption,
                'status': status,
                'last_update': datetime.utcnow()
            }
    
    def _initialize_device_history(self):
        """Initialize device history for anomaly detection"""
        for device_id in self.devices.keys():
            self.device_history[device_id] = {
                'readings': [],
                'average_consumption': 0,
                'last_anomaly': None
            }
    
    async def _read_all_devices(self) -> Dict[str, Dict[str, Any]]:
        """Simulate reading consumption from all devices"""
        readings = {}
        current_time = datetime.utcnow()
        
        for device_id, device_data in self.devices.items():
            device = device_data['device']
            
            # Get simulated consumption based on patterns
            pattern_data = self.simulation_patterns.get(device_id, {})
            
            # Add some random variation to make it realistic
            base_consumption = pattern_data.get('base_consumption', device.power_watts * 0.5)
            variation = random.uniform(0.95, 1.05)  # ±5% random variation
            current_consumption = max(0, int(base_consumption * variation))
            
            # Determine status
            status = pattern_data.get('status', 'on')
            if current_consumption < device.power_watts * 0.05:
                status = 'off'
            elif current_consumption < device.power_watts * 0.3:
                status = 'standby'
            
            # For AC units, simulate temperature
            temperature = None
            if device.usage_pattern == "temperature_dependent":
                if status == 'on':
                    temperature = random.uniform(20, 26)  # Target temperature range
                else:
                    temperature = random.uniform(26, 32)  # Ambient temperature
            
            readings[device_id] = {
                'device_id': device_id,
                'device_name': device.name,
                'power_watts': current_consumption,
                'status': status,
                'temperature': temperature,
                'timestamp': current_time,
                'efficiency_rating': random.uniform(0.8, 1.0) if status == 'on' else None
            }
            
            # Update device state
            self.devices[device_id].update({
                'current_power': current_consumption,
                'current_status': status,
                'last_reading': current_time,
                'temperature': temperature
            })
        
        return readings
    
    async def _store_consumption_data(self, readings: Dict[str, Dict[str, Any]]):
        """Store consumption readings in database"""
        session = self.get_db_session()
        try:
            for reading in readings.values():
                log_entry = ConsumptionLog(
                    device_id=reading['device_id'],
                    power_watts=reading['power_watts'],
                    status=reading['status'],
                    temperature=reading['temperature'],
                    efficiency_rating=reading['efficiency_rating'],
                    timestamp=reading['timestamp']
                )
                session.add(log_entry)
            
            session.commit()
            self.logger.debug(f"Stored {len(readings)} consumption readings")
            
        except Exception as e:
            self.logger.error(f"Failed to store consumption data: {e}")
            session.rollback()
        finally:
            session.close()
    
    async def _detect_anomalies(self, readings: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Detect consumption anomalies (>20% variance from average)"""
        anomalies = []
        
        for device_id, reading in readings.items():
            device_history = self.device_history[device_id]
            current_consumption = reading['power_watts']
            
            # Add current reading to history
            device_history['readings'].append(current_consumption)
            
            # Keep only last 10 readings for rolling average
            if len(device_history['readings']) > 10:
                device_history['readings'] = device_history['readings'][-10:]
            
            # Calculate average (need at least 3 readings)
            if len(device_history['readings']) >= 3:
                average = sum(device_history['readings']) / len(device_history['readings'])
                device_history['average_consumption'] = average
                
                # Check for anomaly (>20% variance)
                if average > 0:
                    variance = abs(current_consumption - average) / average
                    
                    if variance > self.anomaly_threshold:
                        anomaly = {
                            'device_id': device_id,
                            'device_name': reading['device_name'],
                            'current_consumption': current_consumption,
                            'average_consumption': average,
                            'variance_percentage': variance * 100,
                            'timestamp': reading['timestamp'],
                            'severity': 'high' if variance > 0.5 else 'medium'
                        }
                        
                        anomalies.append(anomaly)
                        device_history['last_anomaly'] = datetime.utcnow()
                        
                        self.logger.warning(
                            f"Anomaly detected on {reading['device_name']}: "
                            f"{current_consumption}W vs {average:.0f}W avg "
                            f"({variance*100:.1f}% variance)"
                        )
        
        return anomalies
    
    async def _broadcast_consumption_update(self, readings: Dict[str, Dict[str, Any]], anomalies: List[Dict[str, Any]]):
        """Broadcast consumption update to other agents"""
        try:
            # Calculate total consumption
            total_consumption = sum(reading['power_watts'] for reading in readings.values())
            active_devices = len([r for r in readings.values() if r['status'] == 'on'])
            
            # Prepare message content
            content = {
                'timestamp': datetime.utcnow().isoformat(),
                'total_consumption_watts': total_consumption,
                'active_devices': active_devices,
                'device_count': len(readings),
                'readings': list(readings.values()),
                'anomalies': anomalies,
                'monitoring_stats': self.monitoring_stats
            }
            
            # Broadcast to all agents
            await self.broadcast_message(
                MessageType.CONSUMPTION_UPDATE,
                content,
                MessagePriority.HIGH
            )
            
            # If anomalies detected, send special alert
            if anomalies:
                await self.broadcast_message(
                    MessageType.ANOMALY_DETECTED,
                    {
                        'timestamp': datetime.utcnow().isoformat(),
                        'anomaly_count': len(anomalies),
                        'anomalies': anomalies,
                        'total_consumption': total_consumption
                    },
                    MessagePriority.CRITICAL
                )
            
            self.logger.debug(f"Broadcasted consumption update: {total_consumption}W total, {len(anomalies)} anomalies")
            
        except Exception as e:
            self.logger.error(f"Failed to broadcast consumption update: {e}")
    
    async def _handle_device_status_change(self, content: Dict[str, Any]):
        """Handle device status change from Controller Agent"""
        try:
            device_id = content.get('device_id')
            new_status = content.get('status')
            
            if device_id in self.devices:
                self.devices[device_id]['current_status'] = new_status
                self.logger.info(f"Updated device {device_id} status to {new_status}")
                
                # Update simulation pattern
                if device_id in self.simulation_patterns:
                    pattern = self.simulation_patterns[device_id]
                    if new_status == 'off':
                        pattern['base_consumption'] = 0
                    elif new_status == 'on':
                        device = self.devices[device_id]['device']
                        pattern['base_consumption'] = device.power_watts * random.uniform(0.8, 1.0)
                    
                    pattern['status'] = new_status
                    pattern['last_update'] = datetime.utcnow()
            
        except Exception as e:
            self.logger.error(f"Failed to handle device status change: {e}")
    
    async def _handle_manual_override(self, content: Dict[str, Any]):
        """Handle manual override from user interface"""
        try:
            device_id = content.get('device_id')
            action = content.get('action')
            
            self.logger.info(f"Manual override: {action} for device {device_id}")
            
            # Log the override decision
            await self.log_decision(
                "manual_override",
                {
                    'device_id': device_id,
                    'action': action,
                    'timestamp': datetime.utcnow().isoformat(),
                    'source': 'user_interface'
                }
            )
            
        except Exception as e:
            self.logger.error(f"Failed to handle manual override: {e}")
    
    async def _send_monitoring_status(self, requesting_agent: str):
        """Send current monitoring status to requesting agent"""
        try:
            status_data = {
                'agent_name': self.agent_name,
                'monitoring_stats': self.monitoring_stats,
                'devices_status': {
                    device_id: {
                        'name': data['device'].name,
                        'current_power': data['current_power'],
                        'status': data['current_status'],
                        'last_reading': data['last_reading'].isoformat() if data['last_reading'] else None
                    }
                    for device_id, data in self.devices.items()
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
            self.logger.error(f"Failed to send monitoring status: {e}")
    
    def get_current_consumption_summary(self) -> Dict[str, Any]:
        """Get current consumption summary for external access"""
        total_consumption = sum(
            data['current_power'] for data in self.devices.values()
        )
        active_devices = len([
            data for data in self.devices.values() 
            if data['current_status'] == 'on'
        ])
        
        return {
            'total_consumption_watts': total_consumption,
            'active_devices': active_devices,
            'device_count': len(self.devices),
            'last_update': self.monitoring_stats['last_reading_time'],
            'monitoring_stats': self.monitoring_stats
        } 