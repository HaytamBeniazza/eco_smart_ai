"""
Controller Agent - Agent 4
Device control orchestration and execution for energy optimization
"""

import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Set
from dataclasses import dataclass
from enum import Enum

from .base_agent import BaseAgent, AgentStatus
from core.message_broker import MessageType, MessagePriority, Message
from core.database import Device, ConsumptionLog
from core.config import settings


class DeviceStatus(Enum):
    """Device status enumeration"""
    ON = "on"
    OFF = "off"
    STANDBY = "standby"
    MAINTENANCE = "maintenance"
    ERROR = "error"


class ControlAction(Enum):
    """Control action enumeration"""
    TURN_ON = "turn_on"
    TURN_OFF = "turn_off"
    SET_POWER = "set_power"
    REDUCE_POWER = "reduce_power"
    DELAY_OPERATION = "delay_operation"
    SCHEDULE_CHANGE = "schedule_change"


@dataclass
class DeviceControlCommand:
    """Data class for device control commands"""
    device_id: str
    device_name: str
    action: ControlAction
    target_value: int  # Power level, temperature, etc.
    scheduled_time: datetime
    priority: str
    reason: str
    source_agent: str
    safety_checks_passed: bool = False


@dataclass
class ExecutionResult:
    """Data class for execution results"""
    device_id: str
    command: DeviceControlCommand
    success: bool
    actual_power: int
    execution_time: datetime
    error_message: Optional[str]
    actual_savings_dh: float


class ControllerAgent(BaseAgent):
    """
    Controller Agent - Orchestrates device control and executes optimization schedules
    
    Responsibilities:
    - Execute device control commands
    - Handle manual overrides
    - Monitor device health and safety
    - Coordinate with optimization schedules
    - Provide real-time device status
    """
    
    def __init__(self):
        super().__init__(
            agent_name="controller_agent",
            description="Device control orchestration and execution for energy optimization"
        )
        
        # Device control state
        self.device_states = {}  # device_id -> current state
        self.pending_commands = []  # Queue of commands to execute
        self.scheduled_commands = []  # Future scheduled commands
        self.manual_overrides = {}  # device_id -> override status
        
        # Safety and constraints
        self.safety_limits = {
            'max_power_change_per_minute': 500,  # Max 500W change per minute
            'min_device_rest_time': 300,  # 5 minutes minimum between changes
            'critical_device_protection': True,
            'temperature_safety_range': (16, 30)  # Safe temperature range for HVAC
        }
        
        # Execution tracking
        self.execution_history = []
        self.last_device_interaction = {}  # device_id -> last interaction time
        self.failed_executions = {}  # device_id -> failure count
        
        # Performance metrics
        self.controller_stats = {
            'commands_executed': 0,
            'successful_executions': 0,
            'failed_executions': 0,
            'manual_overrides_handled': 0,
            'safety_blocks': 0,
            'total_energy_controlled_kwh': 0.0,
            'last_execution_time': None
        }
        
        # Device capabilities mapping
        self.device_capabilities = {}
        
        self.logger.info("Controller Agent initialized")
    
    async def initialize(self):
        """Initialize agent-specific resources"""
        try:
            self.logger.info("Initializing Controller Agent...")
            
            # Load device capabilities and current states
            await self._load_device_capabilities()
            await self._initialize_device_states()
            
            # Set up safety monitoring
            await self._initialize_safety_systems()
            
            self.logger.info("Controller Agent initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize Controller Agent: {e}")
            raise
    
    async def execute_cycle(self):
        """Execute one control cycle"""
        try:
            # Process pending commands
            await self._process_pending_commands()
            
            # Check scheduled commands for execution
            await self._check_scheduled_commands()
            
            # Update device states
            await self._update_device_states()
            
            # Perform health checks
            await self._perform_device_health_checks()
            
            # Clean up old execution history
            await self._cleanup_execution_history()
            
            # Broadcast device status updates
            await self._broadcast_device_status()
            
        except Exception as e:
            self.logger.error(f"Error in controller cycle: {e}")
            raise
    
    async def handle_message(self, message: Message):
        """Handle incoming messages from other agents"""
        try:
            self.logger.debug(f"Received message: {message.type.value} from {message.from_agent}")
            
            if message.type == MessageType.OPTIMIZATION_RESULT:
                await self._handle_optimization_schedule(message.content, message.from_agent)
            
            elif message.type == MessageType.MANUAL_OVERRIDE:
                await self._handle_manual_override(message.content)
            
            elif message.type == MessageType.DEVICE_CONTROL:
                await self._handle_device_control_request(message.content, message.from_agent)
            
            elif message.type == MessageType.EMERGENCY_STOP:
                await self._handle_emergency_stop(message.content)
            
            elif message.type == MessageType.SYSTEM_STATUS:
                await self._send_controller_status(message.from_agent)
            
            elif message.type == MessageType.HEALTH_CHECK:
                await self._handle_health_check_request(message.content, message.from_agent)
            
            else:
                self.logger.debug(f"Unhandled message type: {message.type.value}")
                
        except Exception as e:
            self.logger.error(f"Error handling message: {e}")
    
    async def cleanup(self):
        """Cleanup agent resources"""
        self.logger.info("Cleaning up Controller Agent resources")
        
        # Emergency stop all non-critical devices
        await self._emergency_stop_all_devices()
        
        # Clear command queues
        self.pending_commands.clear()
        self.scheduled_commands.clear()
        self.execution_history.clear()
    
    def get_capabilities(self) -> List[str]:
        """Return agent capabilities"""
        return [
            "device_control",
            "schedule_execution",
            "manual_override_handling",
            "safety_monitoring",
            "device_health_monitoring",
            "real_time_control"
        ]
    
    def get_execution_interval(self) -> float:
        """Return execution interval (30 seconds for responsive control)"""
        return 30  # 30 seconds
    
    # ===== COMMAND PROCESSING METHODS =====
    
    async def _process_pending_commands(self):
        """Process commands in the pending queue"""
        try:
            if not self.pending_commands:
                return
            
            # Sort commands by priority and time
            self.pending_commands.sort(key=lambda cmd: (
                cmd.priority != 'high',  # High priority first
                cmd.scheduled_time
            ))
            
            executed_commands = []
            
            for command in self.pending_commands[:5]:  # Process max 5 commands per cycle
                if await self._can_execute_command(command):
                    result = await self._execute_device_command(command)
                    executed_commands.append(command)
                    
                    # Send execution result
                    await self._send_execution_result(result)
                    
                    # Log execution
                    self.execution_history.append(result)
                    
                    # Update statistics
                    self.controller_stats['commands_executed'] += 1
                    if result.success:
                        self.controller_stats['successful_executions'] += 1
                    else:
                        self.controller_stats['failed_executions'] += 1
                    
                    self.logger.info(f"Executed command for {command.device_name}: {result.success}")
            
            # Remove executed commands
            for cmd in executed_commands:
                self.pending_commands.remove(cmd)
            
        except Exception as e:
            self.logger.error(f"Error processing pending commands: {e}")
    
    async def _check_scheduled_commands(self):
        """Check if any scheduled commands are ready for execution"""
        try:
            current_time = datetime.utcnow()
            ready_commands = []
            
            for command in self.scheduled_commands:
                if command.scheduled_time <= current_time:
                    ready_commands.append(command)
            
            # Move ready commands to pending queue
            for command in ready_commands:
                self.pending_commands.append(command)
                self.scheduled_commands.remove(command)
                self.logger.info(f"Scheduled command for {command.device_name} is ready for execution")
            
        except Exception as e:
            self.logger.error(f"Error checking scheduled commands: {e}")
    
    async def _can_execute_command(self, command: DeviceControlCommand) -> bool:
        """Check if a command can be safely executed"""
        try:
            device_id = command.device_id
            
            # Check if device is under manual override
            if device_id in self.manual_overrides:
                override = self.manual_overrides[device_id]
                if override.get('active', False) and override.get('block_automation', True):
                    self.logger.warning(f"Command blocked by manual override for device {device_id}")
                    return False
            
            # Check safety constraints
            if not await self._check_safety_constraints(command):
                self.controller_stats['safety_blocks'] += 1
                return False
            
            # Check device availability
            if not await self._check_device_availability(command.device_id):
                return False
            
            # Check minimum rest time between operations
            if device_id in self.last_device_interaction:
                time_since_last = (datetime.utcnow() - self.last_device_interaction[device_id]).total_seconds()
                if time_since_last < self.safety_limits['min_device_rest_time']:
                    self.logger.debug(f"Device {device_id} needs rest time: {time_since_last}s < {self.safety_limits['min_device_rest_time']}s")
                    return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error checking command execution capability: {e}")
            return False
    
    async def _execute_device_command(self, command: DeviceControlCommand) -> ExecutionResult:
        """Execute a device control command"""
        try:
            device_id = command.device_id
            device_name = command.device_name
            execution_time = datetime.utcnow()
            
            self.logger.info(f"Executing {command.action.value} for {device_name}")
            
            # Simulate device control (in real implementation, this would interface with actual IoT devices)
            success, actual_power, error_message = await self._simulate_device_control(command)
            
            # Update device state
            if success:
                await self._update_device_state(device_id, command.action, actual_power)
                self.last_device_interaction[device_id] = execution_time
            
            # Calculate actual savings
            actual_savings = await self._calculate_actual_savings(command, actual_power, success)
            
            result = ExecutionResult(
                device_id=device_id,
                command=command,
                success=success,
                actual_power=actual_power,
                execution_time=execution_time,
                error_message=error_message,
                actual_savings_dh=actual_savings
            )
            
            # Update controller statistics
            self.controller_stats['last_execution_time'] = execution_time
            if success:
                self.controller_stats['total_energy_controlled_kwh'] += abs(actual_power - command.target_value) / 1000
            
            return result
            
        except Exception as e:
            self.logger.error(f"Failed to execute command for {device_id}: {e}")
            return ExecutionResult(
                device_id=device_id,
                command=command,
                success=False,
                actual_power=0,
                execution_time=execution_time,
                error_message=str(e),
                actual_savings_dh=0.0
            )
    
    async def _simulate_device_control(self, command: DeviceControlCommand) -> tuple[bool, int, Optional[str]]:
        """Simulate device control operation (replace with real IoT integration)"""
        try:
            device_id = command.device_id
            action = command.action
            target_value = command.target_value
            
            # Get current device state
            current_state = self.device_states.get(device_id, {})
            current_power = current_state.get('current_power', 0)
            
            # Simulate different device responses
            if action == ControlAction.TURN_ON:
                # Simulate turning device on
                if current_power < 10:  # Device was off
                    actual_power = target_value if target_value > 0 else self._get_device_default_power(device_id)
                    return True, actual_power, None
                else:
                    return True, current_power, "Device was already on"
            
            elif action == ControlAction.TURN_OFF:
                # Simulate turning device off
                actual_power = 5  # Standby power
                return True, actual_power, None
            
            elif action == ControlAction.SET_POWER:
                # Simulate setting specific power level
                actual_power = target_value
                # Add some realistic variance (±5%)
                variance = int(target_value * 0.05)
                actual_power += variance if target_value > 100 else 0
                return True, actual_power, None
            
            elif action == ControlAction.REDUCE_POWER:
                # Simulate reducing power
                reduction_factor = target_value / 100 if target_value <= 100 else 0.7
                actual_power = int(current_power * reduction_factor)
                return True, actual_power, None
            
            elif action == ControlAction.DELAY_OPERATION:
                # Simulate delaying operation (turn off for now)
                actual_power = 5  # Standby power
                return True, actual_power, f"Operation delayed to {command.scheduled_time}"
            
            else:
                return False, current_power, f"Unknown action: {action.value}"
            
        except Exception as e:
            return False, 0, f"Simulation error: {str(e)}"
    
    # ===== SAFETY AND MONITORING METHODS =====
    
    async def _check_safety_constraints(self, command: DeviceControlCommand) -> bool:
        """Check safety constraints for command execution"""
        try:
            device_id = command.device_id
            action = command.action
            target_value = command.target_value
            
            # Get device information
            device_info = await self._get_device_info(device_id)
            if not device_info:
                self.logger.error(f"Device {device_id} not found for safety check")
                return False
            
            # Check critical device protection
            if (self.safety_limits['critical_device_protection'] and 
                device_info.get('priority') == 'critical' and 
                action in [ControlAction.TURN_OFF, ControlAction.REDUCE_POWER]):
                self.logger.warning(f"Blocked operation on critical device {device_id}")
                return False
            
            # Check power limits
            max_power = device_info.get('power_watts', 1000)
            if target_value > max_power * 1.1:  # Allow 10% overhead
                self.logger.warning(f"Target power {target_value}W exceeds safe limit for {device_id}")
                return False
            
            # Check power change rate
            current_power = self.device_states.get(device_id, {}).get('current_power', 0)
            power_change = abs(target_value - current_power)
            if power_change > self.safety_limits['max_power_change_per_minute']:
                self.logger.warning(f"Power change rate too high for {device_id}: {power_change}W")
                return False
            
            # Check temperature constraints for HVAC devices
            if device_info.get('usage_pattern') == 'temperature_dependent':
                if action == ControlAction.SET_POWER:
                    # Estimate temperature impact (simplified)
                    estimated_temp = self._estimate_temperature_impact(device_info, target_value)
                    temp_range = self.safety_limits['temperature_safety_range']
                    if not (temp_range[0] <= estimated_temp <= temp_range[1]):
                        self.logger.warning(f"Temperature safety violation for {device_id}: {estimated_temp}°C")
                        return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error checking safety constraints: {e}")
            return False
    
    async def _check_device_availability(self, device_id: str) -> bool:
        """Check if device is available for control"""
        try:
            device_state = self.device_states.get(device_id)
            if not device_state:
                self.logger.warning(f"No state information for device {device_id}")
                return False
            
            status = device_state.get('status', DeviceStatus.ERROR)
            
            # Check if device is in a controllable state
            if status in [DeviceStatus.ERROR, DeviceStatus.MAINTENANCE]:
                self.logger.warning(f"Device {device_id} is not available: {status.value}")
                return False
            
            # Check failure history
            failure_count = self.failed_executions.get(device_id, 0)
            if failure_count >= 3:  # Too many recent failures
                self.logger.warning(f"Device {device_id} has too many recent failures: {failure_count}")
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error checking device availability: {e}")
            return False
    
    async def _perform_device_health_checks(self):
        """Perform health checks on all controlled devices"""
        try:
            for device_id, state in self.device_states.items():
                # Check for anomalous power consumption
                current_power = state.get('current_power', 0)
                expected_power = state.get('expected_power', current_power)
                
                if abs(current_power - expected_power) > expected_power * 0.3:  # 30% deviation
                    self.logger.warning(f"Power anomaly detected for {device_id}: {current_power}W vs expected {expected_power}W")
                    await self._report_device_anomaly(device_id, 'power_anomaly', {
                        'current_power': current_power,
                        'expected_power': expected_power
                    })
                
                # Check device responsiveness
                last_interaction = self.last_device_interaction.get(device_id)
                if last_interaction:
                    time_since_interaction = (datetime.utcnow() - last_interaction).total_seconds()
                    if time_since_interaction > 3600:  # 1 hour without interaction
                        await self._check_device_responsiveness(device_id)
            
        except Exception as e:
            self.logger.error(f"Error performing device health checks: {e}")
    
    # ===== MESSAGE HANDLERS =====
    
    async def _handle_optimization_schedule(self, content: Dict[str, Any], from_agent: str):
        """Handle optimization schedule from Optimizer Agent"""
        try:
            schedule_data = content.get('optimization_schedule', [])
            optimization_enabled = content.get('optimization_enabled', True)
            
            if not optimization_enabled:
                self.logger.info("Optimization disabled, ignoring schedule")
                return
            
            commands_added = 0
            
            for schedule_item in schedule_data:
                try:
                    # Convert schedule item to control command
                    command = DeviceControlCommand(
                        device_id=schedule_item['device_id'],
                        device_name=schedule_item['device_name'],
                        action=ControlAction(schedule_item['action'].replace(' ', '_').lower()),
                        target_value=schedule_item['target_power'],
                        scheduled_time=datetime.fromisoformat(schedule_item['scheduled_time']),
                        priority=schedule_item['priority'],
                        reason=schedule_item['reason'],
                        source_agent=from_agent
                    )
                    
                    # Perform safety checks
                    if await self._check_safety_constraints(command):
                        # Add to appropriate queue
                        if command.scheduled_time <= datetime.utcnow() + timedelta(minutes=5):
                            self.pending_commands.append(command)
                        else:
                            self.scheduled_commands.append(command)
                        
                        commands_added += 1
                        command.safety_checks_passed = True
                    else:
                        self.logger.warning(f"Safety check failed for optimization command: {command.device_name}")
                
                except Exception as e:
                    self.logger.error(f"Error processing schedule item: {e}")
            
            self.logger.info(f"Added {commands_added} optimization commands from {from_agent}")
            
            # Send acknowledgment
            await self.send_message(
                from_agent,
                MessageType.EXECUTION_RESULT,
                {
                    'schedule_received': True,
                    'commands_accepted': commands_added,
                    'total_commands': len(schedule_data),
                    'timestamp': datetime.utcnow().isoformat()
                },
                MessagePriority.MEDIUM
            )
            
        except Exception as e:
            self.logger.error(f"Failed to handle optimization schedule: {e}")
    
    async def _handle_manual_override(self, content: Dict[str, Any]):
        """Handle manual override requests"""
        try:
            device_id = content.get('device_id')
            action = content.get('action')
            override_duration = content.get('duration_minutes', 60)
            block_automation = content.get('block_automation', True)
            
            if not device_id:
                self.logger.error("Manual override request missing device_id")
                return
            
            # Set manual override
            self.manual_overrides[device_id] = {
                'active': True,
                'block_automation': block_automation,
                'start_time': datetime.utcnow(),
                'duration_minutes': override_duration,
                'reason': content.get('reason', 'Manual user override')
            }
            
            # If immediate action requested, create command
            if action and action != 'block_only':
                try:
                    target_value = content.get('target_value', 0)
                    
                    command = DeviceControlCommand(
                        device_id=device_id,
                        device_name=content.get('device_name', f'Device {device_id}'),
                        action=ControlAction(action),
                        target_value=target_value,
                        scheduled_time=datetime.utcnow(),
                        priority='high',
                        reason='Manual override command',
                        source_agent='user_interface'
                    )
                    
                    # Execute immediately (bypass some automation checks)
                    if await self._check_safety_constraints(command):
                        self.pending_commands.insert(0, command)  # High priority
                        self.logger.info(f"Manual override command added for {device_id}")
                    else:
                        self.logger.error(f"Manual override command failed safety check for {device_id}")
                
                except Exception as e:
                    self.logger.error(f"Error creating manual override command: {e}")
            
            self.controller_stats['manual_overrides_handled'] += 1
            
            self.logger.info(f"Manual override set for {device_id}: {action} (duration: {override_duration}min)")
            
        except Exception as e:
            self.logger.error(f"Failed to handle manual override: {e}")
    
    async def _handle_device_control_request(self, content: Dict[str, Any], from_agent: str):
        """Handle direct device control requests"""
        try:
            device_id = content.get('device_id')
            action = content.get('action')
            target_value = content.get('target_value', 0)
            priority = content.get('priority', 'medium')
            
            if not device_id or not action:
                self.logger.error("Device control request missing required fields")
                return
            
            command = DeviceControlCommand(
                device_id=device_id,
                device_name=content.get('device_name', f'Device {device_id}'),
                action=ControlAction(action),
                target_value=target_value,
                scheduled_time=datetime.utcnow(),
                priority=priority,
                reason=content.get('reason', f'Direct control from {from_agent}'),
                source_agent=from_agent
            )
            
            # Add to pending queue if safety checks pass
            if await self._check_safety_constraints(command):
                self.pending_commands.append(command)
                self.logger.info(f"Device control request added for {device_id} from {from_agent}")
            else:
                self.logger.warning(f"Device control request failed safety check: {device_id}")
            
        except Exception as e:
            self.logger.error(f"Failed to handle device control request: {e}")
    
    async def _handle_emergency_stop(self, content: Dict[str, Any]):
        """Handle emergency stop requests"""
        try:
            device_id = content.get('device_id')
            reason = content.get('reason', 'Emergency stop')
            
            if device_id:
                # Emergency stop specific device
                await self._emergency_stop_device(device_id, reason)
            else:
                # Emergency stop all devices
                await self._emergency_stop_all_devices(reason)
            
            self.logger.critical(f"Emergency stop executed: {reason}")
            
        except Exception as e:
            self.logger.error(f"Failed to handle emergency stop: {e}")
    
    # ===== UTILITY AND STATE MANAGEMENT METHODS =====
    
    async def _update_device_states(self):
        """Update device states from database"""
        try:
            session = self.get_db_session()
            try:
                devices = session.query(Device).all()
                
                for device in devices:
                    # Get latest consumption data
                    latest_log = session.query(ConsumptionLog).filter(
                        ConsumptionLog.device_id == device.id
                    ).order_by(ConsumptionLog.timestamp.desc()).first()
                    
                    if latest_log:
                        self.device_states[device.id] = {
                            'device_info': device,
                            'current_power': latest_log.power_watts,
                            'status': DeviceStatus(latest_log.status),
                            'last_update': latest_log.timestamp,
                            'temperature': latest_log.temperature,
                            'efficiency': latest_log.efficiency_rating,
                            'expected_power': device.power_watts  # Default expected power
                        }
            
            finally:
                session.close()
                
        except Exception as e:
            self.logger.error(f"Failed to update device states: {e}")
    
    async def _update_device_state(self, device_id: str, action: ControlAction, actual_power: int):
        """Update device state after command execution"""
        try:
            if device_id in self.device_states:
                state = self.device_states[device_id]
                state['current_power'] = actual_power
                state['last_update'] = datetime.utcnow()
                
                # Update status based on power level
                if actual_power < 10:
                    state['status'] = DeviceStatus.OFF
                elif actual_power < 50:
                    state['status'] = DeviceStatus.STANDBY
                else:
                    state['status'] = DeviceStatus.ON
                
                # Update expected power for future comparisons
                state['expected_power'] = actual_power
                
        except Exception as e:
            self.logger.error(f"Failed to update device state: {e}")
    
    async def _load_device_capabilities(self):
        """Load device capabilities from database"""
        try:
            session = self.get_db_session()
            try:
                devices = session.query(Device).all()
                
                for device in devices:
                    self.device_capabilities[device.id] = {
                        'controllable': device.controllable,
                        'power_watts': device.power_watts,
                        'priority': device.priority,
                        'usage_pattern': device.usage_pattern,
                        'room': device.room,
                        'actions_supported': self._get_supported_actions(device)
                    }
                
                self.logger.info(f"Loaded capabilities for {len(devices)} devices")
                
            finally:
                session.close()
                
        except Exception as e:
            self.logger.error(f"Failed to load device capabilities: {e}")
    
    async def _initialize_device_states(self):
        """Initialize device states from latest database readings"""
        try:
            await self._update_device_states()
            
            # Initialize any missing states
            for device_id in self.device_capabilities:
                if device_id not in self.device_states:
                    self.device_states[device_id] = {
                        'current_power': 0,
                        'status': DeviceStatus.OFF,
                        'last_update': datetime.utcnow(),
                        'temperature': 22,  # Default room temperature
                        'efficiency': 1.0,
                        'expected_power': 0
                    }
            
            self.logger.info(f"Initialized states for {len(self.device_states)} devices")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize device states: {e}")
    
    async def _initialize_safety_systems(self):
        """Initialize safety monitoring systems"""
        try:
            # Reset failure counters
            self.failed_executions = {}
            
            # Clear manual overrides older than 24 hours
            current_time = datetime.utcnow()
            expired_overrides = []
            
            for device_id, override in self.manual_overrides.items():
                start_time = override.get('start_time', current_time)
                duration = override.get('duration_minutes', 60)
                if (current_time - start_time).total_seconds() > duration * 60:
                    expired_overrides.append(device_id)
            
            for device_id in expired_overrides:
                del self.manual_overrides[device_id]
                self.logger.info(f"Expired manual override for device {device_id}")
            
            self.logger.info("Safety systems initialized")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize safety systems: {e}")
    
    # ===== COMMUNICATION METHODS =====
    
    async def _send_execution_result(self, result: ExecutionResult):
        """Send execution result to relevant agents"""
        try:
            result_data = {
                'device_id': result.device_id,
                'success': result.success,
                'actual_power': result.actual_power,
                'execution_time': result.execution_time.isoformat(),
                'actual_savings_dh': result.actual_savings_dh,
                'error_message': result.error_message,
                'command_source': result.command.source_agent
            }
            
            # Send to source agent
            if result.command.source_agent != self.agent_name:
                await self.send_message(
                    result.command.source_agent,
                    MessageType.EXECUTION_RESULT,
                    result_data,
                    MessagePriority.HIGH
                )
            
            # Broadcast to monitor agent for tracking
            await self.send_message(
                "monitor_agent",
                MessageType.DEVICE_STATUS,
                {
                    'device_id': result.device_id,
                    'current_power': result.actual_power,
                    'status': self.device_states.get(result.device_id, {}).get('status', DeviceStatus.ON).value,
                    'timestamp': result.execution_time.isoformat(),
                    'controlled_by': self.agent_name
                },
                MessagePriority.MEDIUM
            )
            
        except Exception as e:
            self.logger.error(f"Failed to send execution result: {e}")
    
    async def _broadcast_device_status(self):
        """Broadcast current device status to all agents"""
        try:
            status_data = {
                'timestamp': datetime.utcnow().isoformat(),
                'total_devices': len(self.device_states),
                'devices_controlled': len([d for d in self.device_states.values() if d.get('status') != DeviceStatus.OFF]),
                'pending_commands': len(self.pending_commands),
                'scheduled_commands': len(self.scheduled_commands),
                'manual_overrides': len(self.manual_overrides),
                'controller_stats': self.controller_stats,
                'device_summary': {
                    device_id: {
                        'current_power': state.get('current_power', 0),
                        'status': state.get('status', DeviceStatus.OFF).value,
                        'last_update': state.get('last_update', datetime.utcnow()).isoformat()
                    }
                    for device_id, state in self.device_states.items()
                }
            }
            
            await self.broadcast_message(
                MessageType.DEVICE_STATUS,
                status_data,
                MessagePriority.LOW
            )
            
        except Exception as e:
            self.logger.error(f"Failed to broadcast device status: {e}")
    
    async def _send_controller_status(self, requesting_agent: str):
        """Send controller status to requesting agent"""
        try:
            status_data = {
                'agent_name': self.agent_name,
                'controller_stats': self.controller_stats,
                'device_count': len(self.device_states),
                'pending_commands': len(self.pending_commands),
                'scheduled_commands': len(self.scheduled_commands),
                'manual_overrides': len(self.manual_overrides),
                'safety_systems_active': True,
                'execution_queue_health': len(self.pending_commands) < 10,  # Healthy if queue not too long
                'agent_health': self.get_status()
            }
            
            await self.send_message(
                requesting_agent,
                MessageType.SYSTEM_STATUS,
                status_data,
                MessagePriority.MEDIUM
            )
            
        except Exception as e:
            self.logger.error(f"Failed to send controller status: {e}")
    
    # ===== HELPER METHODS =====
    
    def _get_supported_actions(self, device: Device) -> List[str]:
        """Get supported actions for a device"""
        actions = [ControlAction.TURN_ON.value, ControlAction.TURN_OFF.value]
        
        if device.controllable:
            actions.extend([
                ControlAction.SET_POWER.value,
                ControlAction.REDUCE_POWER.value
            ])
            
        if device.priority in ['low', 'medium']:
            actions.append(ControlAction.DELAY_OPERATION.value)
            
        return actions
    
    def _get_device_default_power(self, device_id: str) -> int:
        """Get default power for a device when turned on"""
        capabilities = self.device_capabilities.get(device_id, {})
        return capabilities.get('power_watts', 100)  # Default 100W
    
    async def _get_device_info(self, device_id: str) -> Optional[Dict[str, Any]]:
        """Get device information"""
        return self.device_capabilities.get(device_id)
    
    def _estimate_temperature_impact(self, device_info: Dict[str, Any], power_level: int) -> float:
        """Estimate temperature impact of HVAC power level (simplified)"""
        # Very simplified estimation - in reality this would be much more complex
        base_temp = 22  # Room temperature
        if 'AC' in device_info.get('name', ''):
            # AC cooling effect
            cooling_effect = (power_level / 1000) * 2  # 2°C per kW
            return base_temp - cooling_effect
        else:
            # Heating effect
            heating_effect = (power_level / 1000) * 1.5  # 1.5°C per kW
            return base_temp + heating_effect
    
    async def _calculate_actual_savings(self, command: DeviceControlCommand, actual_power: int, success: bool) -> float:
        """Calculate actual energy cost savings from command execution"""
        if not success:
            return 0.0
        
        try:
            # Get previous power level
            device_state = self.device_states.get(command.device_id, {})
            previous_power = device_state.get('current_power', 0)
            
            # Calculate power difference
            power_diff = previous_power - actual_power  # Positive = savings
            
            if power_diff <= 0:
                return 0.0
            
            # Calculate cost savings (simplified - assumes 1 hour of operation)
            from core.config import get_current_pricing_tier
            current_hour = datetime.now().hour
            pricing = get_current_pricing_tier(current_hour)
            
            savings_kwh = power_diff / 1000  # Convert to kWh
            savings_dh = savings_kwh * pricing['rate']
            
            return max(0.0, savings_dh)
            
        except Exception as e:
            self.logger.error(f"Failed to calculate actual savings: {e}")
            return 0.0
    
    async def _report_device_anomaly(self, device_id: str, anomaly_type: str, details: Dict[str, Any]):
        """Report device anomaly to monitor agent"""
        try:
            await self.send_message(
                "monitor_agent",
                MessageType.CONSUMPTION_UPDATE,
                {
                    'device_id': device_id,
                    'anomaly_type': anomaly_type,
                    'details': details,
                    'timestamp': datetime.utcnow().isoformat(),
                    'reported_by': self.agent_name
                },
                MessagePriority.HIGH
            )
            
        except Exception as e:
            self.logger.error(f"Failed to report device anomaly: {e}")
    
    async def _check_device_responsiveness(self, device_id: str):
        """Check if device is responding to commands"""
        # This would implement a ping/status check in a real system
        self.logger.info(f"Checking responsiveness for device {device_id}")
    
    async def _emergency_stop_device(self, device_id: str, reason: str):
        """Emergency stop for a specific device"""
        try:
            command = DeviceControlCommand(
                device_id=device_id,
                device_name=f"Device {device_id}",
                action=ControlAction.TURN_OFF,
                target_value=0,
                scheduled_time=datetime.utcnow(),
                priority='high',
                reason=f"Emergency stop: {reason}",
                source_agent=self.agent_name
            )
            
            # Execute immediately without normal safety checks
            result = await self._execute_device_command(command)
            self.logger.critical(f"Emergency stop executed for {device_id}: {result.success}")
            
        except Exception as e:
            self.logger.error(f"Failed emergency stop for {device_id}: {e}")
    
    async def _emergency_stop_all_devices(self, reason: str = "System shutdown"):
        """Emergency stop for all non-critical devices"""
        try:
            for device_id, capabilities in self.device_capabilities.items():
                if capabilities.get('priority') != 'critical':
                    await self._emergency_stop_device(device_id, reason)
            
        except Exception as e:
            self.logger.error(f"Failed emergency stop all devices: {e}")
    
    async def _cleanup_execution_history(self):
        """Clean up old execution history"""
        try:
            # Keep only last 100 execution records
            if len(self.execution_history) > 100:
                self.execution_history = self.execution_history[-100:]
            
            # Clean up old failed execution counters
            current_time = datetime.utcnow()
            for device_id in list(self.failed_executions.keys()):
                last_interaction = self.last_device_interaction.get(device_id)
                if last_interaction and (current_time - last_interaction).total_seconds() > 3600:  # 1 hour
                    self.failed_executions[device_id] = 0  # Reset counter
            
        except Exception as e:
            self.logger.error(f"Failed to cleanup execution history: {e}")
    
    def get_current_controller_summary(self) -> Dict[str, Any]:
        """Get current controller summary for external access"""
        return {
            'total_devices': len(self.device_states),
            'active_devices': len([d for d in self.device_states.values() if d.get('status') != DeviceStatus.OFF]),
            'pending_commands': len(self.pending_commands),
            'scheduled_commands': len(self.scheduled_commands),
            'manual_overrides': len(self.manual_overrides),
            'controller_stats': self.controller_stats,
            'safety_systems_active': True
        }