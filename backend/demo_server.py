from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import asyncio
import json
from datetime import datetime
import uvicorn
import random
from demo_scenarios import DemoScenarios, ScenarioResult

app = FastAPI(title="EcoSmart AI Demo", description="Multi-Agent Energy Management System Demo")

# Initialize demo scenarios
demo_scenarios = DemoScenarios()
scenario_results = []  # Store scenario results

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# WebSocket connections
websocket_connections = set()

# Demo data
demo_devices = [
    {
        "id": "living_room_ac",
        "name": "Smart Thermostat",
        "type": "HVAC",
        "current_power": 2400,
        "is_on": True,
        "room": "Living Room",
        "controllable": True,
        "priority": 1
    },
    {
        "id": "kitchen_lights",
        "name": "LED Lights",
        "type": "Lighting",
        "current_power": 45,
        "is_on": True,
        "room": "Kitchen",
        "controllable": True,
        "priority": 3
    },
    {
        "id": "washing_machine",
        "name": "Smart Washing Machine",
        "type": "Appliance",
        "current_power": 0,
        "is_on": False,
        "room": "Laundry",
        "controllable": True,
        "priority": 2
    },
    {
        "id": "ev_charger",
        "name": "Electric Vehicle Charger",
        "type": "EV",
        "current_power": 7200,
        "is_on": True,
        "room": "Garage",
        "controllable": True,
        "priority": 1
    }
]

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    websocket_connections.add(websocket)
    
    try:
        while True:
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        websocket_connections.remove(websocket)

async def broadcast_websocket_message(message: dict):
    """Broadcast message to all connected WebSocket clients"""
    if websocket_connections:
        for websocket in websocket_connections.copy():
            try:
                await websocket.send_text(json.dumps(message))
            except:
                websocket_connections.discard(websocket)

# Energy & Device endpoints
@app.get("/api/energy/current")
async def get_current_energy():
    total_power = sum(device["current_power"] for device in demo_devices if device["is_on"])
    return {
        "current_consumption": total_power,
        "daily_total": 18.4,
        "monthly_total": 542.8,
        "current_cost": total_power * 0.12 / 1000,
        "devices": demo_devices
    }

@app.get("/api/energy/devices")
async def get_devices():
    return demo_devices

@app.post("/api/devices/{device_id}/toggle")
async def toggle_device(device_id: str):
    for device in demo_devices:
        if device["id"] == device_id:
            device["is_on"] = not device["is_on"]
            if device["is_on"]:
                # Restore power when turned on
                power_map = {
                    "HVAC": 2400,
                    "Lighting": 45,
                    "Appliance": 1200,
                    "EV": 7200,
                    "Electronics": 150
                }
                device["current_power"] = power_map.get(device["type"], 100)
            else:
                device["current_power"] = 0
            
            # Broadcast device update via WebSocket
            await broadcast_websocket_message({
                "type": "device_update",
                "device_id": device_id,
                "is_on": device["is_on"],
                "current_power": device["current_power"]
            })
            
            return {"success": True, "message": f"Device {device_id} toggled successfully"}
    
    return {"success": False, "message": "Device not found"}

# Weather endpoints
@app.get("/api/weather/current")
async def get_current_weather():
    return {
        "temperature": 22 + random.randint(-5, 8),
        "humidity": 65 + random.randint(-10, 15),
        "wind_speed": 12 + random.randint(-5, 10),
        "description": random.choice(["Sunny", "Partly Cloudy", "Cloudy", "Clear"]),
        "solar_potential": 8.5 + random.random() * 2,
        "cooling_needs": 5.2 + random.random() * 3
    }

# Agent status endpoints
@app.get("/api/agents/status")
async def get_agents_status():
    agents = [
        {
            "id": "monitor",
            "name": "Monitor Agent",
            "status": "active",
            "last_activity": "2 min ago",
            "performance": 98,
            "current_task": "Tracking device consumption"
        },
        {
            "id": "weather",
            "name": "Weather Agent",
            "status": "active",
            "last_activity": "5 min ago",
            "performance": 95,
            "current_task": "Updating weather forecast"
        },
        {
            "id": "optimizer",
            "name": "Optimizer Agent",
            "status": "active",
            "last_activity": "1 min ago",
            "performance": 92,
            "current_task": "Optimizing device schedule"
        },
        {
            "id": "controller",
            "name": "Controller Agent",
            "status": "active",
            "last_activity": "3 min ago",
            "performance": 96,
            "current_task": "Managing device states"
        }
    ]
    return agents

# Optimization endpoints
@app.get("/api/optimization/status")
async def get_optimization_status():
    return {
        "today_savings": 5.23 + random.random() * 2,
        "month_savings": 142.67,
        "year_savings": 1847.89,
        "efficiency_gain": 18.5 + random.random() * 5,
        "schedule": []
    }

@app.get("/api/analytics/savings")
async def get_savings():
    return {
        "today_savings": 5.23 + random.random() * 2,
        "month_savings": 142.67,
        "year_savings": 1847.89,
        "efficiency_gain": 18.5 + random.random() * 5
    }

@app.get("/api/analytics/trends")
async def get_trends():
    return {
        "weekly": {
            "actual": [45.2, 52.8, 48.1, 41.7, 55.3, 38.9, 42.4],
            "optimized": [40.1, 47.2, 43.5, 38.9, 49.1, 35.2, 39.8]
        },
        "hourly": [2.1, 1.8, 4.2, 6.8, 8.9, 12.4, 5.3]
    }

@app.get("/api/analytics/daily/{date}")
async def get_daily_analytics(date: str):
    return {
        "date": date,
        "total_consumption": 45.2,
        "cost": 5.42,
        "savings": 1.23,
        "peak_hour": "18:00"
    }

# Demo Scenarios endpoints
@app.get("/api/scenarios/available")
async def get_available_scenarios():
    """Get list of available demo scenarios"""
    scenarios = demo_scenarios.get_available_scenarios()
    return {
        "scenarios": [
            {
                "id": "morning_optimization",
                "name": "Morning Energy Optimization",
                "description": "Smart pre-cooling strategy for hot Morocco mornings",
                "duration": "8 minutes",
                "expected_savings": "18.2%"
            },
            {
                "id": "peak_hour_intelligence", 
                "name": "Peak Hour Intelligence",
                "description": "Automated load management during peak pricing",
                "duration": "7 minutes",
                "expected_savings": "25.3%"
            },
            {
                "id": "multi_agent_collaboration",
                "name": "Multi-Agent Collaboration", 
                "description": "Coordinated response to system anomalies",
                "duration": "8 minutes",
                "expected_savings": "22.1%"
            }
        ]
    }

@app.post("/api/scenarios/run/{scenario_id}")
async def run_demo_scenario(scenario_id: str):
    """Run a specific demo scenario"""
    try:
        result = await demo_scenarios.run_scenario(scenario_id)
        
        # Store result for later access
        scenario_results.append({
            "id": len(scenario_results) + 1,
            "timestamp": datetime.now().isoformat(),
            "result": result
        })
        
        # Broadcast scenario progress via WebSocket
        await broadcast_websocket_message({
            "type": "scenario_complete",
            "scenario_name": result.scenario_name,
            "energy_savings": result.energy_savings,
            "cost_savings_dh": result.cost_savings_dh,
            "success": result.success
        })
        
        return {
            "success": True,
            "message": f"Scenario '{result.scenario_name}' completed successfully",
            "result": {
                "scenario_name": result.scenario_name,
                "agents_involved": result.agents_involved,
                "actions_taken": result.actions_taken,
                "energy_savings": result.energy_savings,
                "cost_savings_dh": result.cost_savings_dh,
                "duration_minutes": result.duration_minutes,
                "insights": result.insights
            }
        }
        
    except ValueError as e:
        return {"success": False, "message": str(e)}
    except Exception as e:
        return {"success": False, "message": f"Error running scenario: {str(e)}"}

@app.get("/api/scenarios/results")
async def get_scenario_results():
    """Get all scenario execution results"""
    return {
        "total_runs": len(scenario_results),
        "results": scenario_results
    }

@app.get("/api/scenarios/results/{result_id}")
async def get_scenario_result(result_id: int):
    """Get a specific scenario result by ID"""
    if 1 <= result_id <= len(scenario_results):
        return scenario_results[result_id - 1]
    else:
        return {"success": False, "message": "Result not found"}

@app.post("/api/scenarios/run-all")
async def run_all_scenarios():
    """Run all demo scenarios in sequence"""
    try:
        results = await demo_scenarios.run_all_scenarios()
        
        # Store all results
        for result in results:
            scenario_results.append({
                "id": len(scenario_results) + 1,
                "timestamp": datetime.now().isoformat(),
                "result": result
            })
        
        # Calculate summary
        total_savings = sum(r.cost_savings_dh for r in results)
        avg_efficiency = sum(r.energy_savings for r in results) / len(results)
        
        # Broadcast completion
        await broadcast_websocket_message({
            "type": "all_scenarios_complete",
            "total_scenarios": len(results),
            "total_savings_dh": total_savings,
            "avg_efficiency": avg_efficiency
        })
        
        return {
            "success": True,
            "message": "All scenarios completed successfully",
            "summary": {
                "scenarios_run": len(results),
                "total_cost_savings_dh": total_savings,
                "average_efficiency_gain": avg_efficiency,
                "success_rate": "100%"
            },
            "results": [
                {
                    "scenario_name": r.scenario_name,
                    "energy_savings": r.energy_savings,
                    "cost_savings_dh": r.cost_savings_dh,
                    "duration_minutes": r.duration_minutes
                } for r in results
            ]
        }
        
    except Exception as e:
        return {"success": False, "message": f"Error running scenarios: {str(e)}"}

@app.get("/")
async def root():
    return {
        "message": "EcoSmart AI Backend Demo", 
        "status": "running", 
        "agents": 4,
        "scenarios_available": len(demo_scenarios.get_available_scenarios()),
        "scenarios_run": len(scenario_results)
    }

async def simulation_loop():
    """Simulate real-time updates"""
    while True:
        try:
            # Simulate energy updates
            total_power = sum(device["current_power"] for device in demo_devices if device["is_on"])
            await broadcast_websocket_message({
                "type": "energy_update",
                "current_consumption": total_power + random.randint(-100, 100),
                "current_cost": (total_power * 0.12 / 1000) + random.random() * 0.05
            })
            
            # Simulate agent status updates
            for agent_id in ["monitor", "weather", "optimizer", "controller"]:
                await broadcast_websocket_message({
                    "type": "agent_status",
                    "agent_id": agent_id,
                    "status": "active",
                    "performance": 92 + random.randint(0, 8)
                })
            
            await asyncio.sleep(5)  # Update every 5 seconds
            
        except Exception as e:
            print(f"Error in simulation loop: {e}")
            await asyncio.sleep(5)

@app.on_event("startup")
async def startup_event():
    print("🚀 Starting EcoSmart AI Demo Backend...")
    asyncio.create_task(simulation_loop())
    print("🎯 Demo backend running with 4 simulated agents!")

if __name__ == "__main__":
    print("🌟 Starting EcoSmart AI Demo Server...")
    uvicorn.run(
        "demo_server:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    ) 