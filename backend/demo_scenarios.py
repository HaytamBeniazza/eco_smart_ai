"""
EcoSmart AI Demo Scenarios
Showcase multi-agent collaboration in realistic energy management scenarios
"""

import asyncio
import json
import random
from datetime import datetime, timedelta
from typing import Dict, List, Any
from dataclasses import dataclass

@dataclass
class ScenarioResult:
    scenario_name: str
    agents_involved: List[str]
    actions_taken: List[Dict[str, Any]]
    energy_savings: float
    cost_savings_dh: float
    duration_minutes: int
    success: bool
    insights: List[str]

class DemoScenarios:
    """Demo scenarios showcasing multi-agent AI collaboration"""
    
    def __init__(self):
        self.scenarios = {
            "morning_optimization": self.morning_energy_optimization,
            "peak_hour_intelligence": self.peak_hour_intelligence,
            "multi_agent_collaboration": self.multi_agent_collaboration
        }
        
    async def run_scenario(self, scenario_name: str) -> ScenarioResult:
        """Run a specific demo scenario"""
        if scenario_name not in self.scenarios:
            raise ValueError(f"Unknown scenario: {scenario_name}")
            
        print(f"🎬 Starting Demo Scenario: {scenario_name}")
        return await self.scenarios[scenario_name]()
    
    async def morning_energy_optimization(self) -> ScenarioResult:
        """
        Scenario 1: Morning Energy Optimization (6:00 AM)
        - Monitor detects rising consumption
        - Weather forecasts hot day (+35°C)
        - Optimizer suggests pre-cooling strategy
        - Controller executes with 18% savings
        """
        scenario_name = "Morning Energy Optimization"
        agents_involved = ["Monitor", "Weather", "Optimizer", "Controller"]
        actions_taken = []
        
        print("📅 6:00 AM - Morocco Morning Energy Optimization")
        
        # Step 1: Monitor Agent detects rising consumption
        print("🔍 Monitor Agent: Detecting rising consumption...")
        await asyncio.sleep(1)
        
        current_consumption = 3200  # Watts
        baseline_consumption = 2100  # Watts
        consumption_increase = ((current_consumption - baseline_consumption) / baseline_consumption) * 100
        
        actions_taken.append({
            "time": "06:00",
            "agent": "Monitor",
            "action": f"Detected {consumption_increase:.1f}% consumption increase",
            "details": f"Current: {current_consumption}W, Baseline: {baseline_consumption}W"
        })
        
        # Step 2: Weather Agent forecasts hot day
        print("🌡️ Weather Agent: Analyzing weather forecast...")
        await asyncio.sleep(1)
        
        forecast_temp = 35  # °C - Hot day in Morocco
        cooling_demand_prediction = 8.5  # kWh
        
        actions_taken.append({
            "time": "06:02",
            "agent": "Weather",
            "action": f"Forecast: Hot day ahead ({forecast_temp}°C)",
            "details": f"Predicted cooling demand: {cooling_demand_prediction} kWh"
        })
        
        # Step 3: Optimizer suggests pre-cooling strategy
        print("🧠 Optimizer Agent: Calculating pre-cooling strategy...")
        await asyncio.sleep(1)
        
        precool_savings = 18.2  # %
        optimal_precool_temp = 22  # °C
        precool_duration = 90  # minutes
        
        actions_taken.append({
            "time": "06:05",
            "agent": "Optimizer",
            "action": f"Recommends pre-cooling strategy ({precool_savings:.1f}% savings)",
            "details": f"Pre-cool to {optimal_precool_temp}°C for {precool_duration} minutes"
        })
        
        # Step 4: Controller executes optimization
        print("🎮 Controller Agent: Executing pre-cooling optimization...")
        await asyncio.sleep(2)
        
        devices_controlled = ["living_room_ac", "bedroom_ac"]
        execution_success = True
        
        for device in devices_controlled:
            actions_taken.append({
                "time": "06:08",
                "agent": "Controller",
                "action": f"Optimizing {device.replace('_', ' ').title()}",
                "details": "Setting optimal temperature and schedule"
            })
        
        # Calculate scenario results
        total_energy_savings = 4.2  # kWh
        cost_savings_dh = total_energy_savings * 1.20  # Normal rate
        
        insights = [
            f"Pre-cooling strategy activated before peak heat",
            f"AC systems optimized for {forecast_temp}°C day",
            f"Energy consumption reduced by {precool_savings:.1f}%",
            f"Comfort maintained while saving {cost_savings_dh:.2f} DH"
        ]
        
        print(f"✅ Scenario Complete: {precool_savings:.1f}% energy savings achieved!")
        
        return ScenarioResult(
            scenario_name=scenario_name,
            agents_involved=agents_involved,
            actions_taken=actions_taken,
            energy_savings=precool_savings,
            cost_savings_dh=cost_savings_dh,
            duration_minutes=8,
            success=execution_success,
            insights=insights
        )
    
    async def peak_hour_intelligence(self) -> ScenarioResult:
        """
        Scenario 2: Peak Hour Intelligence (6:00 PM)
        - Peak pricing alert handling
        - Non-essential device identification
        - Load scheduling optimization
        - 25% peak hour savings
        """
        scenario_name = "Peak Hour Intelligence"
        agents_involved = ["Monitor", "Optimizer", "Controller"]
        actions_taken = []
        
        print("⚡ 6:00 PM - Peak Hour Intelligence Activation")
        
        # Step 1: Monitor detects peak hour onset
        print("🚨 Monitor Agent: Peak hour pricing detected...")
        await asyncio.sleep(1)
        
        peak_rate = 1.65  # DH/kWh
        normal_rate = 1.20  # DH/kWh
        rate_increase = ((peak_rate - normal_rate) / normal_rate) * 100
        
        actions_taken.append({
            "time": "18:00",
            "agent": "Monitor",
            "action": f"Peak pricing alert: {rate_increase:.1f}% rate increase",
            "details": f"Rate: {normal_rate} → {peak_rate} DH/kWh"
        })
        
        # Step 2: Optimizer identifies optimization opportunities
        print("🎯 Optimizer Agent: Analyzing peak hour optimization...")
        await asyncio.sleep(1)
        
        non_essential_devices = ["tv_entertainment", "washing_machine"]
        deferrable_loads = ["washing_machine"]
        
        actions_taken.append({
            "time": "18:02",
            "agent": "Optimizer",
            "action": "Identified non-essential and deferrable devices",
            "details": f"Non-essential: {len(non_essential_devices)}, Deferrable: {len(deferrable_loads)}"
        })
        
        # Step 3: Controller executes load management
        print("🎮 Controller Agent: Executing peak hour optimization...")
        await asyncio.sleep(2)
        
        # Reschedule washing machine to off-peak
        actions_taken.append({
            "time": "18:05",
            "agent": "Controller", 
            "action": "Rescheduled washing machine to off-peak (23:00)",
            "details": "Moved 800W load from peak to off-peak hours"
        })
        
        # Dim non-essential lighting
        actions_taken.append({
            "time": "18:06",
            "agent": "Controller",
            "action": "Dimmed non-essential lighting by 40%",
            "details": "Reduced lighting load from 80W to 48W"
        })
        
        # Optimize AC temperature
        actions_taken.append({
            "time": "18:07",
            "agent": "Controller",
            "action": "Increased AC temperature by 2°C",
            "details": "Temporary adjustment during peak hours"
        })
        
        # Calculate savings
        peak_reduction = 25.3  # %
        energy_saved_kwh = 2.8
        cost_savings_dh = energy_saved_kwh * (peak_rate - normal_rate)
        
        insights = [
            f"Peak hour consumption reduced by {peak_reduction:.1f}%",
            f"Non-essential loads deferred to off-peak hours",
            f"AC temperature temporarily adjusted for savings",
            f"Peak hour cost avoided: {cost_savings_dh:.2f} DH"
        ]
        
        print(f"✅ Peak Hour Optimization: {peak_reduction:.1f}% reduction achieved!")
        
        return ScenarioResult(
            scenario_name=scenario_name,
            agents_involved=agents_involved,
            actions_taken=actions_taken,
            energy_savings=peak_reduction,
            cost_savings_dh=cost_savings_dh,
            duration_minutes=7,
            success=True,
            insights=insights
        )
    
    async def multi_agent_collaboration(self) -> ScenarioResult:
        """
        Scenario 3: Multi-Agent Collaboration
        - All 4 agents communicate via message broker
        - Real-time decision-making coordination
        - Safety systems and override handling
        - Complex optimization scenario
        """
        scenario_name = "Multi-Agent Collaboration Showcase"
        agents_involved = ["Monitor", "Weather", "Optimizer", "Controller"]
        actions_taken = []
        
        print("🤝 Multi-Agent Collaboration Demonstration")
        
        # Step 1: Monitor triggers anomaly alert
        print("🚨 Monitor Agent: Anomaly detected...")
        await asyncio.sleep(1)
        
        anomaly_device = "living_room_ac"
        power_spike = 3200  # Watts (expected: 2000W)
        
        actions_taken.append({
            "time": "14:30",
            "agent": "Monitor",
            "action": f"Anomaly: {anomaly_device} power spike detected",
            "details": f"Power: {power_spike}W (60% above normal)"
        })
        
        # Step 2: Weather agent provides context
        print("🌤️ Weather Agent: Providing context...")
        await asyncio.sleep(1)
        
        current_temp = 32  # °C
        humidity = 78   # %
        heat_index = 38  # °C
        
        actions_taken.append({
            "time": "14:31",
            "agent": "Weather",
            "action": f"High heat index: {heat_index}°C",
            "details": f"Temp: {current_temp}°C, Humidity: {humidity}%"
        })
        
        # Step 3: Optimizer calculates response strategy
        print("🧠 Optimizer Agent: Calculating response strategy...")
        await asyncio.sleep(1)
        
        strategy = "load_balancing_with_comfort"
        alternative_cooling = ["bedroom_ac", "ventilation_fans"]
        
        actions_taken.append({
            "time": "14:33",
            "agent": "Optimizer",
            "action": f"Strategy: {strategy.replace('_', ' ').title()}",
            "details": f"Alternative cooling via: {', '.join(alternative_cooling)}"
        })
        
        # Step 4: Controller implements coordinated response
        print("🎮 Controller Agent: Implementing coordinated response...")
        await asyncio.sleep(2)
        
        # Safety check and AC cycle optimization
        actions_taken.append({
            "time": "14:35",
            "agent": "Controller",
            "action": "AC safety check passed, optimizing cycle",
            "details": "Implemented smart cycling to reduce peak load"
        })
        
        # Activate alternative cooling
        actions_taken.append({
            "time": "14:36",
            "agent": "Controller", 
            "action": "Activated bedroom AC for load balancing",
            "details": "Distributed cooling load across multiple units"
        })
        
        # Step 5: Agents communicate status updates
        print("📡 Inter-agent communication...")
        await asyncio.sleep(1)
        
        message_exchanges = [
            {"from": "Monitor", "to": "Controller", "message": "AC power normalized to 2100W"},
            {"from": "Controller", "to": "Optimizer", "message": "Load balancing successful"},
            {"from": "Optimizer", "to": "All", "message": "System optimization complete"}
        ]
        
        for msg in message_exchanges:
            actions_taken.append({
                "time": "14:38",
                "agent": "Message Broker",
                "action": f"{msg['from']} → {msg['to']}: {msg['message']}",
                "details": "Inter-agent communication"
            })
        
        # Calculate collaboration effectiveness
        efficiency_gain = 22.1  # %
        energy_optimized = 3.6  # kWh
        cost_savings_dh = energy_optimized * 0.35  # Savings rate
        
        insights = [
            "All 4 agents collaborated seamlessly",
            "Anomaly resolved through coordinated response",
            "Safety systems prevented equipment overload",
            "Load balancing maintained comfort and efficiency",
            f"System-wide efficiency improved by {efficiency_gain:.1f}%"
        ]
        
        print(f"✅ Multi-Agent Success: {efficiency_gain:.1f}% efficiency gain!")
        
        return ScenarioResult(
            scenario_name=scenario_name,
            agents_involved=agents_involved,
            actions_taken=actions_taken,
            energy_savings=efficiency_gain,
            cost_savings_dh=cost_savings_dh,
            duration_minutes=8,
            success=True,
            insights=insights
        )
    
    def get_available_scenarios(self) -> List[str]:
        """Get list of available demo scenarios"""
        return list(self.scenarios.keys())
    
    async def run_all_scenarios(self) -> List[ScenarioResult]:
        """Run all demo scenarios in sequence"""
        results = []
        for scenario_name in self.scenarios.keys():
            print(f"\n{'='*60}")
            result = await self.run_scenario(scenario_name)
            results.append(result)
            print(f"{'='*60}\n")
            await asyncio.sleep(2)  # Pause between scenarios
        return results

# Demo scenario runner for testing
async def main():
    """Run demo scenarios for testing"""
    demo = DemoScenarios()
    
    print("🌟 EcoSmart AI Demo Scenarios")
    print("Showcasing Multi-Agent Collaboration\n")
    
    # Run all scenarios
    results = await demo.run_all_scenarios()
    
    # Summary
    print("\n🎯 DEMO SCENARIOS SUMMARY")
    print("=" * 50)
    
    total_savings = sum(r.cost_savings_dh for r in results)
    avg_efficiency = sum(r.energy_savings for r in results) / len(results)
    
    for result in results:
        print(f"✅ {result.scenario_name}")
        print(f"   💰 Savings: {result.cost_savings_dh:.2f} DH")
        print(f"   ⚡ Efficiency: {result.energy_savings:.1f}%")
        print(f"   🕐 Duration: {result.duration_minutes} minutes")
        print()
    
    print(f"📊 Total Cost Savings: {total_savings:.2f} DH")
    print(f"📈 Average Efficiency Gain: {avg_efficiency:.1f}%")
    print(f"🤖 Agents Collaboration: 100% Success Rate")

if __name__ == "__main__":
    asyncio.run(main()) 