"""
EcoSmart AI Database Models and Connection Management
SQLAlchemy models for multi-agent energy optimization system
"""

import json
from datetime import datetime, date
from typing import Dict, Any, Optional, List
from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, DateTime, Date, Text, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session, relationship
from sqlalchemy.types import TypeDecorator, VARCHAR
import aiosqlite
import asyncio
from .config import settings

Base = declarative_base()


class JSONColumn(TypeDecorator):
    """Custom JSON column type for SQLite"""
    impl = VARCHAR
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is not None:
            return json.dumps(value)
        return value

    def process_result_value(self, value, dialect):
        if value is not None:
            return json.loads(value)
        return value


# ===== DATABASE MODELS =====

class Device(Base):
    """Device definitions table"""
    __tablename__ = "devices"
    
    id = Column(String, primary_key=True)  # e.g., 'living_room_ac'
    name = Column(String, nullable=False)
    power_watts = Column(Integer, nullable=False)
    priority = Column(String, nullable=False)  # 'critical', 'high', 'medium', 'low'
    controllable = Column(Boolean, nullable=False)
    room = Column(String)
    usage_pattern = Column(String)  # 'temperature_dependent', 'schedule_based', etc.
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    consumption_logs = relationship("ConsumptionLog", back_populates="device")
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'name': self.name,
            'power_watts': self.power_watts,
            'priority': self.priority,
            'controllable': self.controllable,
            'room': self.room,
            'usage_pattern': self.usage_pattern,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class ConsumptionLog(Base):
    """Real-time consumption logs"""
    __tablename__ = "consumption_logs"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    device_id = Column(String, ForeignKey('devices.id'), nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    power_watts = Column(Integer)
    status = Column(String)  # 'on', 'off', 'standby'
    temperature = Column(Float, nullable=True)  # For AC units
    efficiency_rating = Column(Float, nullable=True)  # 0.0 to 1.0
    
    # Relationships
    device = relationship("Device", back_populates="consumption_logs")
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'device_id': self.device_id,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'power_watts': self.power_watts,
            'status': self.status,
            'temperature': self.temperature,
            'efficiency_rating': self.efficiency_rating
        }


class WeatherData(Base):
    """Weather data cache"""
    __tablename__ = "weather_data"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    temperature = Column(Float)  # Current temperature in Celsius
    humidity = Column(Float)  # Humidity percentage
    forecast_temp = Column(Float)  # Forecasted temperature
    optimal_ac_temp = Column(Float)  # Calculated optimal AC temperature
    weather_condition = Column(String)  # 'sunny', 'cloudy', 'rainy', etc.
    wind_speed = Column(Float)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'temperature': self.temperature,
            'humidity': self.humidity,
            'forecast_temp': self.forecast_temp,
            'optimal_ac_temp': self.optimal_ac_temp,
            'weather_condition': self.weather_condition,
            'wind_speed': self.wind_speed
        }


class AgentDecision(Base):
    """Agent decisions and communications"""
    __tablename__ = "agent_decisions"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    agent_name = Column(String, nullable=False)
    decision_type = Column(String)  # 'optimization', 'override', 'schedule'
    timestamp = Column(DateTime, default=datetime.utcnow)
    data = Column(JSONColumn)  # JSON data for decision details
    executed = Column(Boolean, default=False)
    execution_result = Column(String, nullable=True)
    confidence_score = Column(Float, nullable=True)  # 0.0 to 1.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'agent_name': self.agent_name,
            'decision_type': self.decision_type,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'data': self.data,
            'executed': self.executed,
            'execution_result': self.execution_result,
            'confidence_score': self.confidence_score
        }


class OptimizationResult(Base):
    """Optimization results tracking"""
    __tablename__ = "optimization_results"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(Date, default=date.today)
    original_cost_dh = Column(Float)  # Cost without optimization
    optimized_cost_dh = Column(Float)  # Cost with optimization
    savings_dh = Column(Float)  # Savings in Moroccan Dirhams
    savings_percentage = Column(Float)  # Savings percentage
    total_consumption_kwh = Column(Float)
    peak_consumption_kwh = Column(Float)
    off_peak_consumption_kwh = Column(Float)
    optimization_strategy = Column(String)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'date': self.date.isoformat() if self.date else None,
            'original_cost_dh': self.original_cost_dh,
            'optimized_cost_dh': self.optimized_cost_dh,
            'savings_dh': self.savings_dh,
            'savings_percentage': self.savings_percentage,
            'total_consumption_kwh': self.total_consumption_kwh,
            'peak_consumption_kwh': self.peak_consumption_kwh,
            'off_peak_consumption_kwh': self.off_peak_consumption_kwh,
            'optimization_strategy': self.optimization_strategy
        }


class MessageLog(Base):
    """Message broker logs for debugging"""
    __tablename__ = "message_logs"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    from_agent = Column(String)
    to_agent = Column(String)
    message_type = Column(String)
    content = Column(JSONColumn)
    processing_time_ms = Column(Float, nullable=True)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'from_agent': self.from_agent,
            'to_agent': self.to_agent,
            'message_type': self.message_type,
            'content': self.content,
            'processing_time_ms': self.processing_time_ms
        }


# ===== DATABASE CONNECTION MANAGEMENT =====

class DatabaseManager:
    """Database connection and session management"""
    
    def __init__(self, database_url: str = None):
        self.database_url = database_url or "sqlite:///ecosmart.db"
        self.engine = None
        self.SessionLocal = None
        
    def initialize(self):
        """Initialize database connection and create tables"""
        self.engine = create_engine(
            self.database_url,
            echo=False,
            connect_args={"check_same_thread": False}  # For SQLite
        )
        
        self.SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=self.engine
        )
        
        # Create all tables
        Base.metadata.create_all(bind=self.engine)
        
        # Initialize with default data
        self._initialize_default_data()
    
    def get_session(self) -> Session:
        """Get database session"""
        return self.SessionLocal()
    
    def _initialize_default_data(self):
        """Initialize database with default devices and settings"""
        from .config import DEFAULT_DEVICES
        
        session = self.get_session()
        try:
            # Check if devices already exist
            existing_devices = session.query(Device).count()
            if existing_devices == 0:
                # Add default devices
                for device_id, device_data in DEFAULT_DEVICES.items():
                    device = Device(
                        id=device_id,
                        name=device_data["name"],
                        power_watts=device_data["power_watts"],
                        priority=device_data["priority"],
                        controllable=device_data["controllable"],
                        room=device_data["room"],
                        usage_pattern=device_data["usage_pattern"]
                    )
                    session.add(device)
                
                session.commit()
                print(f"✅ Initialized {len(DEFAULT_DEVICES)} default devices")
            
        except Exception as e:
            print(f"❌ Error initializing default data: {e}")
            session.rollback()
        finally:
            session.close()


# ===== ASYNC DATABASE OPERATIONS =====

class AsyncDatabaseManager:
    """Async database operations for high-performance agent communication"""
    
    def __init__(self, database_path: str = "ecosmart.db"):
        self.database_path = database_path
    
    async def execute_query(self, query: str, params: tuple = ()):
        """Execute async database query"""
        async with aiosqlite.connect(self.database_path) as db:
            cursor = await db.execute(query, params)
            await db.commit()
            return cursor
    
    async def fetch_all(self, query: str, params: tuple = ()):
        """Fetch all results from query"""
        async with aiosqlite.connect(self.database_path) as db:
            cursor = await db.execute(query, params)
            return await cursor.fetchall()
    
    async def fetch_one(self, query: str, params: tuple = ()):
        """Fetch one result from query"""
        async with aiosqlite.connect(self.database_path) as db:
            cursor = await db.execute(query, params)
            return await cursor.fetchone()


# ===== UTILITY FUNCTIONS =====

def get_current_consumption_summary(session: Session) -> Dict[str, Any]:
    """Get current consumption summary across all devices"""
    from sqlalchemy import func
    
    # Get latest consumption for each device
    latest_consumption = session.query(
        ConsumptionLog.device_id,
        func.max(ConsumptionLog.timestamp).label('latest_timestamp')
    ).group_by(ConsumptionLog.device_id).subquery()
    
    current_logs = session.query(ConsumptionLog).join(
        latest_consumption,
        (ConsumptionLog.device_id == latest_consumption.c.device_id) &
        (ConsumptionLog.timestamp == latest_consumption.c.latest_timestamp)
    ).all()
    
    total_consumption = sum(log.power_watts for log in current_logs if log.power_watts)
    active_devices = len([log for log in current_logs if log.status == 'on'])
    
    return {
        'total_consumption_watts': total_consumption,
        'active_devices': active_devices,
        'device_count': len(current_logs),
        'timestamp': datetime.utcnow().isoformat(),
        'devices': [log.to_dict() for log in current_logs]
    }


def get_daily_savings(session: Session, target_date: date = None) -> Dict[str, Any]:
    """Get daily savings calculation"""
    if target_date is None:
        target_date = date.today()
    
    result = session.query(OptimizationResult).filter(
        OptimizationResult.date == target_date
    ).first()
    
    if result:
        return result.to_dict()
    
    return {
        'date': target_date.isoformat(),
        'savings_dh': 0.0,
        'savings_percentage': 0.0,
        'total_consumption_kwh': 0.0
    }


# Global database manager instance (lazy initialization)
db_manager = None

# Global engine instance for agent access
engine = None


# Dependency for FastAPI
def get_db_session():
    """Dependency to get database session for FastAPI endpoints"""
    global db_manager
    if db_manager is None:
        db_manager = DatabaseManager()
        db_manager.initialize()
    session = db_manager.get_session()
    try:
        yield session
    finally:
        session.close()


# Alias for FastAPI dependency
def get_db():
    """FastAPI dependency function - alias for get_db_session"""
    return get_db_session()


# Initialize database on module import
def init_database():
    """Initialize the database with tables and sample data"""
    try:
        global db_manager
        if db_manager is None:
            db_manager = DatabaseManager()
            db_manager.initialize()
        print("✅ Database initialized successfully")
    except Exception as e:
        print(f"❌ Failed to initialize database: {e}")
        raise

def get_db_connection():
    """Get a direct SQLite connection for simple queries"""
    import sqlite3
    return sqlite3.connect("ecosmart.db") 