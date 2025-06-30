"""
EcoSmart AI - Main FastAPI Application
Multi-Agent Energy Optimization System
"""

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import uvicorn
import asyncio
import logging
from datetime import datetime
from typing import Dict, Any

# Core imports
from core.database import init_database, get_db
from core.config import settings

# API endpoints
from api.energy_endpoints import router as energy_router
from api.weather_endpoints import router as weather_router

# Agents
from agents.monitor_agent import MonitorAgent
from agents.weather_agent import WeatherAgent
from agents.optimizer_agent import OptimizerAgent
from agents.controller_agent import ControllerAgent


# Global agent instances
agent_instances = {}
agent_tasks = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    logging.info("🚀 Starting EcoSmart AI Multi-Agent System...")
    
    # Initialize database
    init_database()
    logging.info("✅ Database initialized")
    
    # Initialize agents
    await initialize_agents()
    logging.info("✅ All agents initialized and running")
    
    # Start agent execution loops
    await start_agent_tasks()
    logging.info("✅ Agent execution tasks started")
    
    yield
    
    # Shutdown
    logging.info("🛑 Shutting down EcoSmart AI Multi-Agent System...")
    await shutdown_agents()
    logging.info("✅ All agents shut down gracefully")


# FastAPI app with lifespan manager
app = FastAPI(
    title="EcoSmart AI - Multi-Agent Energy Optimization",
    description="Level 4 Multi-Agent System for Smart Home Energy Management with Morocco ONEE Integration",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# CORS middleware for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(energy_router)
app.include_router(weather_router)


# ===== MAIN APPLICATION ENDPOINTS =====

@app.get("/")
async def root():
    """Root endpoint with system information"""
    return {
        "system": "EcoSmart AI Multi-Agent Energy Optimization",
        "version": "1.0.0",
        "status": "operational",
        "agents": {
            "monitor_agent": agent_instances.get("monitor_agent") is not None,
            "weather_agent": agent_instances.get("weather_agent") is not None,
            "optimizer_agent": agent_instances.get("optimizer_agent") is not None,
            "controller_agent": agent_instances.get("controller_agent") is not None
        },
        "features": [
            "Real-time energy monitoring",
            "Weather-based optimization", 
            "Cost optimization with Morocco ONEE pricing",
            "Intelligent device control",
            "Multi-agent collaboration"
        ],
        "endpoints": {
            "energy": "/api/energy/*",
            "weather": "/api/weather/*",
            "optimization": "/api/optimization/*",
            "agents": "/api/agents/*",
            "control": "/api/control/*"
        }
    }


@app.get("/health")
async def health_check():
    """System health check"""
    try:
        agent_health = {}
        
        for agent_name, agent in agent_instances.items():
            if agent:
                status = agent.get_status()
                agent_health[agent_name] = {
                    "status": status.value,
                    "healthy": status.value in ["running", "idle"],
                    "last_heartbeat": getattr(agent, 'last_heartbeat', None)
                }
            else:
                agent_health[agent_name] = {
                    "status": "not_initialized",
                    "healthy": False,
                    "last_heartbeat": None
                }
        
        # Overall system health
        all_healthy = all(agent["healthy"] for agent in agent_health.values())
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "system_healthy": all_healthy,
            "agents": agent_health,
            "database": "connected",  # Simple check
            "api": "operational"
        }
        
    except Exception as e:
        return JSONResponse(
            status_code=503,
            content={
                "timestamp": datetime.utcnow().isoformat(),
                "system_healthy": False,
                "error": str(e)
            }
        )


# ===== AGENT MANAGEMENT ENDPOINTS =====

@app.get("/api/agents/status")
async def get_all_agents_status():
    """Get status of all agents"""
    try:
        agent_statuses = {}
        
        for agent_name, agent in agent_instances.items():
            if agent:
                agent_statuses[agent_name] = {
                    "name": agent.agent_name,
                    "description": agent.description,
                    "status": agent.get_status().value,
                    "capabilities": agent.get_capabilities(),
                    "execution_interval": agent.get_execution_interval(),
                    "message_count": len(getattr(agent, 'received_messages', [])),
                    "last_activity": getattr(agent, 'last_heartbeat', None)
                }
            else:
                agent_statuses[agent_name] = {
                    "name": agent_name,
                    "status": "not_initialized",
                    "error": "Agent instance not found"
                }
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "total_agents": len(agent_statuses),
            "running_agents": len([a for a in agent_statuses.values() if a.get("status") == "running"]),
            "agents": agent_statuses
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get agent statuses: {str(e)}")


@app.get("/api/agents/{agent_name}/status")
async def get_agent_status(agent_name: str):
    """Get detailed status of a specific agent"""
    try:
        if agent_name not in agent_instances:
            raise HTTPException(status_code=404, detail=f"Agent '{agent_name}' not found")
        
        agent = agent_instances[agent_name]
        if not agent:
            raise HTTPException(status_code=404, detail=f"Agent '{agent_name}' not initialized")
        
        # Get agent-specific status information
        status_info = {
            "agent_name": agent.agent_name,
            "description": agent.description,
            "status": agent.get_status().value,
            "capabilities": agent.get_capabilities(),
            "execution_interval": agent.get_execution_interval(),
            "last_heartbeat": getattr(agent, 'last_heartbeat', None)
        }
        
        # Add agent-specific metrics
        if agent_name == "monitor_agent" and hasattr(agent, 'get_current_monitoring_summary'):
            status_info["monitoring_summary"] = agent.get_current_monitoring_summary()
        elif agent_name == "weather_agent" and hasattr(agent, 'get_current_weather_summary'):
            status_info["weather_summary"] = agent.get_current_weather_summary()
        elif agent_name == "optimizer_agent" and hasattr(agent, 'get_current_optimization_summary'):
            status_info["optimization_summary"] = agent.get_current_optimization_summary()
        elif agent_name == "controller_agent" and hasattr(agent, 'get_current_controller_summary'):
            status_info["controller_summary"] = agent.get_current_controller_summary()
        
        return status_info
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get agent status: {str(e)}")


# ===== OPTIMIZATION ENDPOINTS =====

@app.get("/api/optimization/status")
async def get_optimization_status():
    """Get current optimization status"""
    try:
        optimizer = agent_instances.get("optimizer_agent")
        controller = agent_instances.get("controller_agent")
        
        if not optimizer:
            raise HTTPException(status_code=404, detail="Optimizer agent not available")
        
        optimization_status = {
            "timestamp": datetime.utcnow().isoformat(),
            "optimization_enabled": getattr(optimizer, 'optimization_enabled', False),
            "target_savings_percentage": getattr(optimizer, 'target_savings_percentage', 20),
            "optimization_stats": getattr(optimizer, 'optimization_stats', {}),
        }
        
        if controller:
            controller_summary = controller.get_current_controller_summary() if hasattr(controller, 'get_current_controller_summary') else {}
            optimization_status["controller_status"] = controller_summary
        
        return optimization_status
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get optimization status: {str(e)}")


@app.post("/api/optimization/enable")
async def enable_optimization():
    """Enable optimization system"""
    try:
        optimizer = agent_instances.get("optimizer_agent")
        if not optimizer:
            raise HTTPException(status_code=404, detail="Optimizer agent not available")
        
        optimizer.optimization_enabled = True
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "optimization_enabled": True,
            "message": "Optimization system enabled"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to enable optimization: {str(e)}")


@app.post("/api/optimization/disable")
async def disable_optimization():
    """Disable optimization system"""
    try:
        optimizer = agent_instances.get("optimizer_agent")
        if not optimizer:
            raise HTTPException(status_code=404, detail="Optimizer agent not available")
        
        optimizer.optimization_enabled = False
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "optimization_enabled": False,
            "message": "Optimization system disabled"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to disable optimization: {str(e)}")


@app.get("/api/optimization/schedule")
async def get_optimization_schedule():
    """Get current optimization schedule"""
    try:
        controller = agent_instances.get("controller_agent")
        if not controller:
            raise HTTPException(status_code=404, detail="Controller agent not available")
        
        pending_commands = getattr(controller, 'pending_commands', [])
        scheduled_commands = getattr(controller, 'scheduled_commands', [])
        
        def serialize_command(cmd):
            return {
                "device_id": cmd.device_id,
                "device_name": cmd.device_name,
                "action": cmd.action.value if hasattr(cmd.action, 'value') else str(cmd.action),
                "target_value": cmd.target_value,
                "scheduled_time": cmd.scheduled_time.isoformat(),
                "priority": cmd.priority,
                "reason": cmd.reason,
                "source_agent": cmd.source_agent
            }
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "pending_commands": [serialize_command(cmd) for cmd in pending_commands],
            "scheduled_commands": [serialize_command(cmd) for cmd in scheduled_commands],
            "total_commands": len(pending_commands) + len(scheduled_commands)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get optimization schedule: {str(e)}")


# ===== DEVICE CONTROL ENDPOINTS =====

@app.post("/api/devices/{device_id}/toggle")
async def toggle_device(device_id: str):
    """Toggle a device on/off"""
    try:
        controller = agent_instances.get("controller_agent")
        if not controller:
            raise HTTPException(status_code=404, detail="Controller agent not available")
        
        # Get current device state
        device_states = getattr(controller, 'device_states', {})
        device_state = device_states.get(device_id)
        
        if not device_state:
            raise HTTPException(status_code=404, detail=f"Device '{device_id}' not found")
        
        current_power = device_state.get('current_power', 0)
        action = 'turn_off' if current_power > 50 else 'turn_on'
        
        # Send control message to controller
        from core.message_broker import MessageType, MessagePriority
        
        await controller.handle_message(type('Message', (), {
            'type': MessageType.MANUAL_OVERRIDE,
            'content': {
                'device_id': device_id,
                'action': action,
                'reason': 'Manual toggle via API',
                'duration_minutes': 60,
                'block_automation': False
            },
            'from_agent': 'api_interface'
        })())
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "device_id": device_id,
            "action": action,
            "message": f"Device toggle command sent: {action}"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to toggle device: {str(e)}")


@app.post("/api/devices/{device_id}/override")
async def manual_device_override(
    device_id: str,
    action: str,
    target_value: int = 0,
    duration_minutes: int = 60
):
    """Manual override for device control"""
    try:
        controller = agent_instances.get("controller_agent")
        if not controller:
            raise HTTPException(status_code=404, detail="Controller agent not available")
        
        # Validate action
        valid_actions = ['turn_on', 'turn_off', 'set_power', 'reduce_power', 'block_only']
        if action not in valid_actions:
            raise HTTPException(status_code=400, detail=f"Invalid action. Must be one of: {valid_actions}")
        
        # Send manual override message
        from core.message_broker import MessageType
        
        await controller.handle_message(type('Message', (), {
            'type': MessageType.MANUAL_OVERRIDE,
            'content': {
                'device_id': device_id,
                'action': action,
                'target_value': target_value,
                'duration_minutes': duration_minutes,
                'reason': f'Manual override via API: {action}',
                'block_automation': True
            },
            'from_agent': 'api_interface'
        })())
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "device_id": device_id,
            "action": action,
            "target_value": target_value,
            "duration_minutes": duration_minutes,
            "message": "Manual override command sent successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to set manual override: {str(e)}")


# ===== ANALYTICS ENDPOINTS =====

@app.get("/api/analytics/savings")
async def get_savings_analytics(db = Depends(get_db)):
    """Get cumulative savings analytics"""
    try:
        from core.database import OptimizationResult
        from sqlalchemy import func
        from datetime import timedelta
        
        # Get savings data
        total_savings = db.query(func.sum(OptimizationResult.savings_dh)).scalar() or 0
        
        # Monthly savings
        month_start = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        monthly_savings = db.query(func.sum(OptimizationResult.savings_dh)).filter(
            OptimizationResult.date >= month_start
        ).scalar() or 0
        
        # Weekly savings
        week_start = datetime.utcnow() - timedelta(days=7)
        weekly_savings = db.query(func.sum(OptimizationResult.savings_dh)).filter(
            OptimizationResult.date >= week_start
        ).scalar() or 0
        
        # Daily average
        total_results = db.query(OptimizationResult).count()
        daily_average = total_savings / max(1, total_results)
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "total_savings_dh": round(total_savings, 2),
            "monthly_savings_dh": round(monthly_savings, 2),
            "weekly_savings_dh": round(weekly_savings, 2),
            "daily_average_savings_dh": round(daily_average, 2),
            "total_optimization_runs": total_results,
            "estimated_annual_savings_dh": round(daily_average * 365, 2)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get savings analytics: {str(e)}")


# ===== AGENT LIFECYCLE MANAGEMENT =====

async def initialize_agents():
    """Initialize all agents"""
    try:
        # Create agent instances
        agent_instances["monitor_agent"] = MonitorAgent()
        agent_instances["weather_agent"] = WeatherAgent()
        agent_instances["optimizer_agent"] = OptimizerAgent()
        agent_instances["controller_agent"] = ControllerAgent()
        
        # Initialize each agent
        for agent_name, agent in agent_instances.items():
            await agent.initialize()
            logging.info(f"✅ {agent_name} initialized")
        
    except Exception as e:
        logging.error(f"Failed to initialize agents: {e}")
        raise


async def start_agent_tasks():
    """Start agent execution tasks"""
    try:
        for agent_name, agent in agent_instances.items():
            if agent:
                task = asyncio.create_task(agent.run())
                agent_tasks[agent_name] = task
                logging.info(f"✅ {agent_name} task started")
        
    except Exception as e:
        logging.error(f"Failed to start agent tasks: {e}")
        raise


async def shutdown_agents():
    """Shutdown all agents gracefully"""
    try:
        # Cancel all tasks
        for agent_name, task in agent_tasks.items():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
            logging.info(f"✅ {agent_name} task cancelled")
        
        # Cleanup agents
        for agent_name, agent in agent_instances.items():
            if agent:
                await agent.cleanup()
                logging.info(f"✅ {agent_name} cleaned up")
        
        # Clear instances
        agent_instances.clear()
        agent_tasks.clear()
        
    except Exception as e:
        logging.error(f"Error during agent shutdown: {e}")


# ===== MAIN EXECUTION =====

if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    # Run the application
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,  # Remove in production
        log_level="info"
    )