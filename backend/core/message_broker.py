"""
EcoSmart AI Message Broker System
In-memory message broker for multi-agent communication
"""

import asyncio
import json
from datetime import datetime
from typing import Dict, Any, List, Callable, Optional, Set
from dataclasses import dataclass, asdict
from enum import Enum
from collections import defaultdict, deque
import logging
import weakref

logger = logging.getLogger(__name__)


class MessageType(Enum):
    """Message types for agent communication"""
    # Monitor Agent Messages
    CONSUMPTION_UPDATE = "consumption_update"
    ANOMALY_DETECTED = "anomaly_detected"
    DEVICE_STATUS_CHANGE = "device_status_change"
    
    # Weather Agent Messages
    WEATHER_UPDATE = "weather_update"
    TEMPERATURE_FORECAST = "temperature_forecast"
    COOLING_RECOMMENDATION = "cooling_recommendation"
    
    # Optimizer Agent Messages
    OPTIMIZATION_RESULT = "optimization_result"
    SCHEDULE_UPDATE = "schedule_update"
    COST_ANALYSIS = "cost_analysis"
    SAVINGS_REPORT = "savings_report"
    
    # Controller Agent Messages
    DEVICE_CONTROL = "device_control"
    EXECUTION_RESULT = "execution_result"
    MANUAL_OVERRIDE = "manual_override"
    
    # System Messages
    AGENT_HEARTBEAT = "agent_heartbeat"
    SYSTEM_STATUS = "system_status"
    ERROR_NOTIFICATION = "error_notification"
    SHUTDOWN_SIGNAL = "shutdown_signal"


class MessagePriority(Enum):
    """Message priority levels"""
    CRITICAL = 1
    HIGH = 2
    MEDIUM = 3
    LOW = 4


@dataclass
class Message:
    """Message structure for agent communication"""
    id: str
    type: MessageType
    from_agent: str
    to_agent: str  # Can be "broadcast" for all agents
    timestamp: datetime
    priority: MessagePriority
    content: Dict[str, Any]
    correlation_id: Optional[str] = None  # For request-response tracking
    expires_at: Optional[datetime] = None
    retry_count: int = 0
    max_retries: int = 3
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert message to dictionary"""
        return {
            'id': self.id,
            'type': self.type.value,
            'from_agent': self.from_agent,
            'to_agent': self.to_agent,
            'timestamp': self.timestamp.isoformat(),
            'priority': self.priority.value,
            'content': self.content,
            'correlation_id': self.correlation_id,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'retry_count': self.retry_count,
            'max_retries': self.max_retries
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Message':
        """Create message from dictionary"""
        return cls(
            id=data['id'],
            type=MessageType(data['type']),
            from_agent=data['from_agent'],
            to_agent=data['to_agent'],
            timestamp=datetime.fromisoformat(data['timestamp']),
            priority=MessagePriority(data['priority']),
            content=data['content'],
            correlation_id=data.get('correlation_id'),
            expires_at=datetime.fromisoformat(data['expires_at']) if data.get('expires_at') else None,
            retry_count=data.get('retry_count', 0),
            max_retries=data.get('max_retries', 3)
        )


class MessageBroker:
    """In-memory message broker for agent communication"""
    
    def __init__(self, max_queue_size: int = 1000, enable_persistence: bool = True):
        self.max_queue_size = max_queue_size
        self.enable_persistence = enable_persistence
        
        # Agent registration
        self.registered_agents: Dict[str, Dict[str, Any]] = {}
        self.agent_handlers: Dict[str, Dict[MessageType, Callable]] = defaultdict(dict)
        
        # Message queues (per agent)
        self.message_queues: Dict[str, deque] = defaultdict(lambda: deque(maxlen=max_queue_size))
        
        # Broadcast subscribers
        self.broadcast_subscribers: Set[str] = set()
        
        # Message history for debugging
        self.message_history: deque = deque(maxlen=10000)
        
        # Statistics
        self.stats = {
            'messages_sent': 0,
            'messages_delivered': 0,
            'messages_failed': 0,
            'agents_registered': 0,
            'start_time': datetime.utcnow()
        }
        
        # Background tasks
        self._cleanup_task = None
        self._running = False
        
        # Message ID counter
        self._message_counter = 0
        
        logger.info("Message broker initialized")
    
    async def start(self):
        """Start the message broker"""
        self._running = True
        self._cleanup_task = asyncio.create_task(self._cleanup_expired_messages())
        logger.info("Message broker started")
    
    async def stop(self):
        """Stop the message broker"""
        self._running = False
        if self._cleanup_task:
            self._cleanup_task.cancel()
        logger.info("Message broker stopped")
    
    def register_agent(self, agent_name: str, agent_info: Dict[str, Any] = None) -> bool:
        """Register an agent with the message broker"""
        try:
            self.registered_agents[agent_name] = {
                'name': agent_name,
                'registered_at': datetime.utcnow(),
                'last_heartbeat': datetime.utcnow(),
                'info': agent_info or {},
                'status': 'active'
            }
            
            # Subscribe to broadcasts by default
            self.broadcast_subscribers.add(agent_name)
            
            self.stats['agents_registered'] += 1
            logger.info(f"Agent '{agent_name}' registered successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to register agent '{agent_name}': {e}")
            return False
    
    def unregister_agent(self, agent_name: str) -> bool:
        """Unregister an agent"""
        try:
            if agent_name in self.registered_agents:
                del self.registered_agents[agent_name]
                self.broadcast_subscribers.discard(agent_name)
                
                # Clear message queue
                if agent_name in self.message_queues:
                    del self.message_queues[agent_name]
                
                logger.info(f"Agent '{agent_name}' unregistered")
                return True
            return False
            
        except Exception as e:
            logger.error(f"Failed to unregister agent '{agent_name}': {e}")
            return False
    
    def register_handler(self, agent_name: str, message_type: MessageType, handler: Callable):
        """Register message handler for specific message type"""
        self.agent_handlers[agent_name][message_type] = handler
        logger.debug(f"Handler registered for {agent_name}:{message_type.value}")
    
    async def send_message(self, 
                          from_agent: str,
                          to_agent: str,
                          message_type: MessageType,
                          content: Dict[str, Any],
                          priority: MessagePriority = MessagePriority.MEDIUM,
                          correlation_id: Optional[str] = None) -> str:
        """Send message to another agent or broadcast"""
        
        # Generate unique message ID
        self._message_counter += 1
        message_id = f"msg_{self._message_counter}_{int(datetime.utcnow().timestamp())}"
        
        message = Message(
            id=message_id,
            type=message_type,
            from_agent=from_agent,
            to_agent=to_agent,
            timestamp=datetime.utcnow(),
            priority=priority,
            content=content,
            correlation_id=correlation_id
        )
        
        try:
            # Handle broadcast messages
            if to_agent == "broadcast":
                delivered_count = 0
                for subscriber in self.broadcast_subscribers:
                    if subscriber != from_agent:  # Don't send to sender
                        await self._deliver_message(subscriber, message)
                        delivered_count += 1
                
                logger.debug(f"Broadcast message {message_id} delivered to {delivered_count} agents")
            
            # Handle direct messages
            elif to_agent in self.registered_agents:
                await self._deliver_message(to_agent, message)
                logger.debug(f"Message {message_id} delivered to {to_agent}")
            
            else:
                logger.warning(f"Agent '{to_agent}' not found for message {message_id}")
                self.stats['messages_failed'] += 1
                return message_id
            
            # Store in history
            self.message_history.append(message)
            
            # Update statistics
            self.stats['messages_sent'] += 1
            
            # Persist message if enabled
            if self.enable_persistence:
                await self._persist_message(message)
            
            return message_id
            
        except Exception as e:
            logger.error(f"Failed to send message {message_id}: {e}")
            self.stats['messages_failed'] += 1
            raise
    
    async def _deliver_message(self, agent_name: str, message: Message):
        """Deliver message to specific agent"""
        try:
            # Add to agent's message queue
            self.message_queues[agent_name].append(message)
            
            # Try to call handler if registered
            if agent_name in self.agent_handlers:
                handler = self.agent_handlers[agent_name].get(message.type)
                if handler:
                    try:
                        if asyncio.iscoroutinefunction(handler):
                            await handler(message)
                        else:
                            handler(message)
                    except Exception as e:
                        logger.error(f"Handler error for {agent_name}:{message.type.value}: {e}")
            
            self.stats['messages_delivered'] += 1
            
        except Exception as e:
            logger.error(f"Failed to deliver message to {agent_name}: {e}")
            self.stats['messages_failed'] += 1
    
    async def receive_messages(self, agent_name: str, max_messages: int = 10) -> List[Message]:
        """Receive messages for an agent"""
        if agent_name not in self.registered_agents:
            logger.warning(f"Agent '{agent_name}' not registered")
            return []
        
        messages = []
        queue = self.message_queues[agent_name]
        
        for _ in range(min(max_messages, len(queue))):
            if queue:
                messages.append(queue.popleft())
        
        # Update last heartbeat
        self.registered_agents[agent_name]['last_heartbeat'] = datetime.utcnow()
        
        return messages
    
    async def send_heartbeat(self, agent_name: str):
        """Send heartbeat from agent"""
        if agent_name in self.registered_agents:
            self.registered_agents[agent_name]['last_heartbeat'] = datetime.utcnow()
            self.registered_agents[agent_name]['status'] = 'active'
    
    def get_agent_status(self, agent_name: str) -> Dict[str, Any]:
        """Get status of specific agent"""
        if agent_name in self.registered_agents:
            agent_info = self.registered_agents[agent_name].copy()
            
            # Check if agent is responsive
            last_heartbeat = agent_info['last_heartbeat']
            time_since_heartbeat = (datetime.utcnow() - last_heartbeat).total_seconds()
            
            if time_since_heartbeat > 120:  # 2 minutes
                agent_info['status'] = 'unresponsive'
            elif time_since_heartbeat > 60:  # 1 minute
                agent_info['status'] = 'warning'
            
            agent_info['queue_size'] = len(self.message_queues[agent_name])
            agent_info['time_since_heartbeat'] = time_since_heartbeat
            
            return agent_info
        
        return None
    
    def get_all_agents_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all registered agents"""
        return {
            agent_name: self.get_agent_status(agent_name)
            for agent_name in self.registered_agents
        }
    
    def get_broker_stats(self) -> Dict[str, Any]:
        """Get message broker statistics"""
        uptime_seconds = (datetime.utcnow() - self.stats['start_time']).total_seconds()
        
        return {
            **self.stats,
            'uptime_seconds': uptime_seconds,
            'registered_agents': len(self.registered_agents),
            'total_queue_size': sum(len(queue) for queue in self.message_queues.values()),
            'average_queue_size': sum(len(queue) for queue in self.message_queues.values()) / max(len(self.message_queues), 1),
            'message_history_size': len(self.message_history)
        }
    
    async def _cleanup_expired_messages(self):
        """Background task to cleanup expired messages"""
        while self._running:
            try:
                current_time = datetime.utcnow()
                
                # Clean up message history
                while (self.message_history and 
                       len(self.message_history) > 0 and
                       self.message_history[0].expires_at and
                       self.message_history[0].expires_at < current_time):
                    self.message_history.popleft()
                
                # Clean up agent queues
                for agent_name, queue in self.message_queues.items():
                    expired_messages = []
                    for i, message in enumerate(queue):
                        if message.expires_at and message.expires_at < current_time:
                            expired_messages.append(i)
                    
                    # Remove expired messages (in reverse order to maintain indices)
                    for i in reversed(expired_messages):
                        del queue[i]
                
                await asyncio.sleep(60)  # Run cleanup every minute
                
            except Exception as e:
                logger.error(f"Error in cleanup task: {e}")
                await asyncio.sleep(10)
    
    async def _persist_message(self, message: Message):
        """Persist message to database for debugging"""
        try:
            from .database import db_manager, MessageLog
            
            session = db_manager.get_session()
            try:
                log_entry = MessageLog(
                    from_agent=message.from_agent,
                    to_agent=message.to_agent,
                    message_type=message.type.value,
                    content=message.content
                )
                session.add(log_entry)
                session.commit()
            finally:
                session.close()
                
        except Exception as e:
            logger.error(f"Failed to persist message: {e}")


# Global message broker instance
message_broker = MessageBroker()


# Utility functions for easy message sending
async def broadcast_message(from_agent: str, 
                          message_type: MessageType, 
                          content: Dict[str, Any],
                          priority: MessagePriority = MessagePriority.MEDIUM) -> str:
    """Broadcast message to all agents"""
    return await message_broker.send_message(
        from_agent=from_agent,
        to_agent="broadcast",
        message_type=message_type,
        content=content,
        priority=priority
    )


async def send_direct_message(from_agent: str,
                            to_agent: str,
                            message_type: MessageType,
                            content: Dict[str, Any],
                            priority: MessagePriority = MessagePriority.MEDIUM) -> str:
    """Send direct message to specific agent"""
    return await message_broker.send_message(
        from_agent=from_agent,
        to_agent=to_agent,
        message_type=message_type,
        content=content,
        priority=priority
    )


# Helper functions for common message patterns
async def notify_consumption_update(from_agent: str, device_data: Dict[str, Any]):
    """Helper to notify consumption update"""
    return await broadcast_message(
        from_agent=from_agent,
        message_type=MessageType.CONSUMPTION_UPDATE,
        content=device_data,
        priority=MessagePriority.HIGH
    )


async def notify_weather_update(from_agent: str, weather_data: Dict[str, Any]):
    """Helper to notify weather update"""
    return await broadcast_message(
        from_agent=from_agent,
        message_type=MessageType.WEATHER_UPDATE,
        content=weather_data,
        priority=MessagePriority.MEDIUM
    )


async def send_optimization_result(from_agent: str, to_agent: str, optimization_data: Dict[str, Any]):
    """Helper to send optimization result"""
    return await send_direct_message(
        from_agent=from_agent,
        to_agent=to_agent,
        message_type=MessageType.OPTIMIZATION_RESULT,
        content=optimization_data,
        priority=MessagePriority.HIGH
    )


async def send_device_control(from_agent: str, to_agent: str, control_data: Dict[str, Any]):
    """Helper to send device control command"""
    return await send_direct_message(
        from_agent=from_agent,
        to_agent=to_agent,
        message_type=MessageType.DEVICE_CONTROL,
        content=control_data,
        priority=MessagePriority.CRITICAL
    ) 