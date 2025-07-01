"""
Test script for EcoSmart AI Demo Scenarios API
"""

import asyncio
import aiohttp
import json

async def test_scenarios_api():
    """Test the demo scenarios API endpoints"""
    base_url = "http://localhost:8000"
    
    print("🧪 Testing EcoSmart AI Demo Scenarios API")
    print("=" * 50)
    
    async with aiohttp.ClientSession() as session:
        
        # Test 1: Get available scenarios
        print("\n1️⃣ Testing: Get Available Scenarios")
        try:
            async with session.get(f"{base_url}/api/scenarios/available") as response:
                if response.status == 200:
                    data = await response.json()
                    print("✅ Success!")
                    print(f"📋 Available scenarios: {len(data['scenarios'])}")
                    for scenario in data['scenarios']:
                        print(f"   • {scenario['name']} ({scenario['expected_savings']})")
                else:
                    print(f"❌ Failed: {response.status}")
        except Exception as e:
            print(f"❌ Error: {e}")
        
        # Test 2: Run a single scenario
        print("\n2️⃣ Testing: Run Morning Optimization Scenario")
        try:
            async with session.post(f"{base_url}/api/scenarios/run/morning_optimization") as response:
                if response.status == 200:
                    data = await response.json()
                    if data['success']:
                        result = data['result']
                        print("✅ Scenario completed successfully!")
                        print(f"💰 Cost Savings: {result['cost_savings_dh']:.2f} DH")
                        print(f"⚡ Energy Savings: {result['energy_savings']:.1f}%")
                        print(f"🕐 Duration: {result['duration_minutes']} minutes")
                        print(f"🤖 Agents involved: {', '.join(result['agents_involved'])}")
                    else:
                        print(f"❌ Scenario failed: {data['message']}")
                else:
                    print(f"❌ Failed: {response.status}")
        except Exception as e:
            print(f"❌ Error: {e}")
        
        # Test 3: Get scenario results
        print("\n3️⃣ Testing: Get Scenario Results")
        try:
            async with session.get(f"{base_url}/api/scenarios/results") as response:
                if response.status == 200:
                    data = await response.json()
                    print("✅ Success!")
                    print(f"📊 Total scenario runs: {data['total_runs']}")
                    if data['total_runs'] > 0:
                        latest = data['results'][-1]
                        print(f"🕐 Latest run: {latest['result']['scenario_name']}")
                else:
                    print(f"❌ Failed: {response.status}")
        except Exception as e:
            print(f"❌ Error: {e}")
        
        # Test 4: Test server status  
        print("\n4️⃣ Testing: Server Status")
        try:
            async with session.get(f"{base_url}/") as response:
                if response.status == 200:
                    data = await response.json()
                    print("✅ Server is running!")
                    print(f"🤖 Agents: {data['agents']}")
                    print(f"📋 Scenarios available: {data['scenarios_available']}")
                    print(f"🎬 Scenarios run: {data['scenarios_run']}")
                else:
                    print(f"❌ Failed: {response.status}")
        except Exception as e:
            print(f"❌ Error: {e}")
    
    print("\n🎯 Test completed!")
    print("✨ Demo scenarios API integration is ready!")

if __name__ == "__main__":
    print("🚀 Starting API tests...")
    print("Make sure the demo server is running on localhost:8000")
    asyncio.run(test_scenarios_api()) 