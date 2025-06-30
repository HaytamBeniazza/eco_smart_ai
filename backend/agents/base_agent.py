"""
EcoSmart AI Base Agent Class
Abstract base class for all agents in the multi-agent system
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, Any, Optional, List
from enum import Enum

from core.message_broker import message_broker, MessageType, MessagePriority, Message
from core.database import db_manager, get_db_session


class AgentStatus(Enum):
    """Agent status enumeration"""
    STARTING = "starting"
    RUNNING = "running"
    PAUSED = "paused"
    ERROR = "error"
    STOPPED = "stopped"


class BaseAgent(ABC):
    """Abstract base class for all EcoSmart AI agents"""
    
    def __init__(self, agent_name: str, description: str = ""):
        self.agent_name = agent_name
        self.description = description
        self.status = AgentStatus.STARTING
        self.last_heartbeat = datetime.utcnow()
        self.error_count = 0
        self.max_errors = 5
        
        # Agent lifecycle
        self._running = False
        self._task = None
        self._heartbeat_task = None
        
        # Performance metrics
        self.stats = {
            'start_time': None,
            'messages_sent': 0,
            'messages_received': 0,
            'tasks_completed': 0,
            'errors_encountered': 0,
            'last_activity': None
        }
        
        # Setup logging
        self.logger = logging.getLogger(f"{self.__class__.__name__}")
        self.logger.setLevel(logging.INFO)
        
        self.logger.info(f"Agent {self.agent_name} initialized")
    
    async def start(self):
        """Start the agent and register with message broker"""
        try:
            self.logger.info(f"Starting agent {self.agent_name}")
            
            # Register with message broker
            success = message_broker.register_agent(
                self.agent_name, 
                {
                    'description': self.description,
                    'class': self.__class__.__name__,
                    'capabilities': self.get_capabilities()
                }
            )
            
            if not success:
                raise Exception(f"Failed to register agent {self.agent_name}")
            
            # Initialize agent-specific setup
            await self.initialize()
            
            # Start main execution loop
            self._running = True
            self.status = AgentStatus.RUNNING
            self.stats['start_time'] = datetime.utcnow()
            
            # Start background tasks
            self._task = asyncio.create_task(self._run_loop())
            self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
            
            self.logger.info(f"Agent {self.agent_name} started successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to start agent {self.agent_name}: {e}")
            self.status = AgentStatus.ERROR
            raise
    
    async def stop(self):
        """Stop the agent gracefully"""
        self.logger.info(f"Stopping agent {self.agent_name}")
        
        self._running = False
        self.status = AgentStatus.STOPPED
        
        # Cancel background tasks
        if self._task:
            self._task.cancel()
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
        
        # Cleanup agent-specific resources
        await self.cleanup()
        
        # Unregister from message broker
        message_broker.unregister_agent(self.agent_name)
        
        self.logger.info(f"Agent {self.agent_name} stopped")
    
    async def pause(self):
        """Pause agent execution"""
        self.logger.info(f"Pausing agent {self.agent_name}")
        self.status = AgentStatus.PAUSED
    
    async def resume(self):
        """Resume agent execution"""
        self.logger.info(f"Resuming agent {self.agent_name}")
        self.status = AgentStatus.RUNNING
    
    async def _run_loop(self):
        """Main agent execution loop"""
        while self._running:
            try:
                if self.status == AgentStatus.RUNNING:
                    # Process incoming messages
                    await self._process_messages()
                    
                    # Execute agent-specific logic
                    await self.execute_cycle()
                    
                    # Update activity timestamp
                    self.stats['last_activity'] = datetime.utcnow()
                    self.stats['tasks_completed'] += 1
                
                # Sleep based on agent's execution interval
                await asyncio.sleep(self.get_execution_interval())
                
            except Exception as e:
                await self._handle_error(e)
    
    async def _heartbeat_loop(self):
        """Send periodic heartbeats to message broker"""
        while self._running:
            try:
                await message_broker.send_heartbeat(self.agent_name)
                self.last_heartbeat = datetime.utcnow()
                await asyncio.sleep(30)  # Heartbeat every 30 seconds
                
            except Exception as e:
                self.logger.error(f"Heartbeat error: {e}")
                await asyncio.sleep(5)
    
    async def _process_messages(self):
        """Process incoming messages from message broker"""
        try:
            messages = await message_broker.receive_messages(self.agent_name, max_messages=10)
            
            for message in messages:
                self.stats['messages_received'] += 1
                await self.handle_message(message)
                
        except Exception as e:
            self.logger.error(f"Error processing messages: {e}")
    
    async def _handle_error(self, error: Exception):
        """Handle errors during agent execution"""
        self.error_count += 1
        self.stats['errors_encountered'] += 1
        
        self.logger.error(f"Agent {self.agent_name} error #{self.error_count}: {error}")
        
        if self.error_count >= self.max_errors:
            self.logger.critical(f"Agent {self.agent_name} exceeded max errors ({self.max_errors})")
            self.status = AgentStatus.ERROR
            await self.stop()
        else:
            # Brief pause before retrying
            await asyncio.sleep(min(self.error_count * 2, 30))
    
    async def send_message(self, 
                          to_agent: str,
                          message_type: MessageType,
                          content: Dict[str, Any],
                          priority: MessagePriority = MessagePriority.MEDIUM) -> str:
        """Send message to another agent"""
        try:
            message_id = await message_broker.send_message(
                from_agent=self.agent_name,
                to_agent=to_agent,
                message_type=message_type,
                content=content,
                priority=priority
            )
            
            self.stats['messages_sent'] += 1
            self.logger.debug(f"Sent message {message_id} to {to_agent}")
            
            return message_id
            
        except Exception as e:
            self.logger.error(f"Failed to send message: {e}")
            raise
    
    async def broadcast_message(self,
                               message_type: MessageType,
                               content: Dict[str, Any],
                               priority: MessagePriority = MessagePriority.MEDIUM) -> str:
        """Broadcast message to all agents"""
        return await self.send_message("broadcast", message_type, content, priority)
    
    def get_status(self) -> Dict[str, Any]:
        """Get current agent status and metrics"""
        uptime = (datetime.utcnow() - self.stats['start_time']).total_seconds() if self.stats['start_time'] else 0
        
        return {
            'agent_name': self.agent_name,
            'description': self.description,
            'status': self.status.value,
            'last_heartbeat': self.last_heartbeat.isoformat(),
            'error_count': self.error_count,
            'uptime_seconds': uptime,
            'stats': self.stats.copy(),
            'capabilities': self.get_capabilities()
        }
    
    # ===== ABSTRACT METHODS (Must be implemented by subclasses) =====
    
    @abstractmethod
    async def initialize(self):
        """Initialize agent-specific resources and setup"""
        pass
    
    @abstractmethod
    async def execute_cycle(self):
        """Execute one cycle of agent-specific logic"""
        pass
    
    @abstractmethod
    async def handle_message(self, message: Message):
        """Handle incoming message from other agents"""
        pass
    
    @abstractmethod
    async def cleanup(self):
        """Cleanup agent-specific resources"""
        pass
    
    @abstractmethod
    def get_capabilities(self) -> List[str]:
        """Return list of agent capabilities"""
        pass
    
    @abstractmethod
    def get_execution_interval(self) -> float:
        """Return execution cycle interval in seconds"""
        pass
    
    # ===== UTILITY METHODS =====
    
    def get_db_session(self):
        """Get database session for agent operations"""
        return db_manager.get_session()
    
    async def log_decision(self, decision_type: str, data: Dict[str, Any], confidence: float = 1.0):
        """Log agent decision to database"""
        try:
            from core.database import AgentDecision
            
            session = self.get_db_session()
            try:
                decision = AgentDecision(
                    agent_name=self.agent_name,
                    decision_type=decision_type,
                    data=data,
                    confidence_score=confidence
                )
                session.add(decision)
                session.commit()
                
                self.logger.debug(f"Logged decision: {decision_type}")
                
            finally:
                session.close()
                
        except Exception as e:
            self.logger.error(f"Failed to log decision: {e}")
    
    def is_healthy(self) -> bool:
        """Check if agent is healthy"""
        if self.status == AgentStatus.ERROR:
            return False
        
        if self.error_count >= self.max_errors:
            return False
        
        # Check if heartbeat is recent (within 2 minutes)
        time_since_heartbeat = (datetime.utcnow() - self.last_heartbeat).total_seconds()
        if time_since_heartbeat > 120:
            return False
        
        return True
    
    def reset_error_count(self):
        """Reset error count (useful for recovery)"""
        self.error_count = 0
        if self.status == AgentStatus.ERROR:
            self.status = AgentStatus.RUNNING
        self.logger.info(f"Error count reset for agent {self.agent_name}") 