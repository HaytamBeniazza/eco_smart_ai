"""
EcoSmart AI - Complete System Validation Script
Tests all components for production readiness
"""

import asyncio
import aiohttp
import json
import subprocess
import time
import sys
from datetime import datetime
from typing import Dict, List, Any

class SystemValidator:
    """Comprehensive system validation for EcoSmart AI"""
    
    def __init__(self):
        self.backend_url = "http://localhost:8000"
        self.frontend_url = "http://localhost:5173"
        self.test_results = []
        self.errors = []
        
    def log_test(self, test_name: str, success: bool, details: str = ""):
        """Log test result"""
        status = "✅ PASS" if success else "❌ FAIL"
        result = {
            "test": test_name,
            "status": status,
            "success": success,
            "details": details,
            "timestamp": datetime.now().isoformat()
        }
        self.test_results.append(result)
        print(f"{status} - {test_name}: {details}")
        
        if not success:
            self.errors.append(f"{test_name}: {details}")
    
    async def test_backend_health(self, session: aiohttp.ClientSession):
        """Test backend health and basic endpoints"""
        print("\n🔍 Testing Backend Health...")
        
        try:
            # Test basic health
            async with session.get(f"{self.backend_url}/") as response:
                if response.status == 200:
                    data = await response.json()
                    self.log_test("Backend Health", True, f"Status: {data.get('status')}, Agents: {data.get('agents')}")
                else:
                    self.log_test("Backend Health", False, f"HTTP {response.status}")
        except Exception as e:
            self.log_test("Backend Health", False, f"Connection error: {e}")
    
    async def test_api_endpoints(self, session: aiohttp.ClientSession):
        """Test all critical API endpoints"""
        print("\n🔌 Testing API Endpoints...")
        
        endpoints = [
            ("/api/energy/current", "Energy API"),
            ("/api/weather/current", "Weather API"),
            ("/api/agents/status", "Agents API"),
            ("/api/energy/devices", "Devices API"),
            ("/api/optimization/status", "Optimization API"),
            ("/api/scenarios/available", "Scenarios API"),
            ("/api/system/health", "System Health API"),
            ("/api/system/metrics", "Performance Metrics API")
        ]
        
        for endpoint, name in endpoints:
            try:
                async with session.get(f"{self.backend_url}{endpoint}") as response:
                    if response.status == 200:
                        data = await response.json()
                        self.log_test(name, True, f"Data received: {len(str(data))} chars")
                    else:
                        self.log_test(name, False, f"HTTP {response.status}")
            except Exception as e:
                self.log_test(name, False, f"Error: {e}")
    
    async def test_demo_scenarios(self, session: aiohttp.ClientSession):
        """Test demo scenarios execution"""
        print("\n🎬 Testing Demo Scenarios...")
        
        # Test scenario availability
        try:
            async with session.get(f"{self.backend_url}/api/scenarios/available") as response:
                if response.status == 200:
                    scenarios = await response.json()
                    scenario_count = len(scenarios.get('scenarios', []))
                    self.log_test("Scenarios Available", True, f"{scenario_count} scenarios loaded")
                else:
                    self.log_test("Scenarios Available", False, f"HTTP {response.status}")
                    return
        except Exception as e:
            self.log_test("Scenarios Available", False, f"Error: {e}")
            return
        
        # Test scenario execution
        test_scenario = "morning_optimization"
        try:
            async with session.post(f"{self.backend_url}/api/scenarios/run/{test_scenario}") as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get('success'):
                        result = data.get('result', {})
                        savings = result.get('energy_savings', 0)
                        cost = result.get('cost_savings_dh', 0)
                        self.log_test("Scenario Execution", True, f"Savings: {savings}%, Cost: {cost:.2f} DH")
                    else:
                        self.log_test("Scenario Execution", False, f"Scenario failed: {data.get('message')}")
                else:
                    self.log_test("Scenario Execution", False, f"HTTP {response.status}")
        except Exception as e:
            self.log_test("Scenario Execution", False, f"Error: {e}")
    
    async def test_device_control(self, session: aiohttp.ClientSession):
        """Test device control functionality"""
        print("\n🎮 Testing Device Control...")
        
        # Get device list first
        try:
            async with session.get(f"{self.backend_url}/api/energy/devices") as response:
                if response.status == 200:
                    devices = await response.json()
                    if devices:
                        device_id = devices[0]['id']
                        original_state = devices[0]['is_on']
                        
                        # Test device toggle
                        async with session.post(f"{self.backend_url}/api/devices/{device_id}/toggle") as toggle_response:
                            if toggle_response.status == 200:
                                toggle_data = await toggle_response.json()
                                if toggle_data.get('success'):
                                    self.log_test("Device Control", True, f"Toggled device {device_id}")
                                else:
                                    self.log_test("Device Control", False, f"Toggle failed: {toggle_data.get('message')}")
                            else:
                                self.log_test("Device Control", False, f"HTTP {toggle_response.status}")
                    else:
                        self.log_test("Device Control", False, "No devices found")
                else:
                    self.log_test("Device Control", False, f"HTTP {response.status}")
        except Exception as e:
            self.log_test("Device Control", False, f"Error: {e}")
    
    async def test_websocket_connection(self):
        """Test WebSocket connectivity"""
        print("\n📡 Testing WebSocket Connection...")
        
        try:
            import websockets
            
            async with websockets.connect(f"ws://localhost:8000/ws") as websocket:
                # Send a test message and wait for response
                await asyncio.wait_for(websocket.ping(), timeout=5)
                self.log_test("WebSocket Connection", True, "Connection established and ping successful")
                
        except ImportError:
            self.log_test("WebSocket Connection", False, "websockets library not available")
        except asyncio.TimeoutError:
            self.log_test("WebSocket Connection", False, "Connection timeout")
        except Exception as e:
            self.log_test("WebSocket Connection", False, f"Error: {e}")
    
    async def test_frontend_availability(self, session: aiohttp.ClientSession):
        """Test frontend availability"""
        print("\n🌐 Testing Frontend Availability...")
        
        try:
            async with session.get(self.frontend_url) as response:
                if response.status == 200:
                    content = await response.text()
                    if "EcoSmart" in content or "svelte" in content.lower():
                        self.log_test("Frontend Availability", True, f"Frontend responding (HTML: {len(content)} chars)")
                    else:
                        self.log_test("Frontend Availability", False, "Frontend content doesn't match expected")
                else:
                    self.log_test("Frontend Availability", False, f"HTTP {response.status}")
        except Exception as e:
            self.log_test("Frontend Availability", False, f"Error: {e}")
    
    def test_system_requirements(self):
        """Test system requirements and dependencies"""
        print("\n⚙️ Testing System Requirements...")
        
        # Test Python version
        python_version = sys.version_info
        if python_version >= (3, 8):
            self.log_test("Python Version", True, f"Python {python_version.major}.{python_version.minor}.{python_version.micro}")
        else:
            self.log_test("Python Version", False, f"Python {python_version.major}.{python_version.minor} (requires 3.8+)")
        
        # Test required packages
        required_packages = [
            "fastapi", "uvicorn", "sqlalchemy", "aiosqlite", 
            "requests", "websockets", "psutil"
        ]
        
        for package in required_packages:
            try:
                __import__(package)
                self.log_test(f"Package: {package}", True, "Installed")
            except ImportError:
                self.log_test(f"Package: {package}", False, "Not installed")
    
    def test_file_structure(self):
        """Test project file structure"""
        print("\n📁 Testing File Structure...")
        
        import os
        
        required_files = [
            "backend/demo_server.py",
            "backend/demo_scenarios.py", 
            "backend/performance_config.py",
            "backend/requirements.txt",
            "frontend/package.json",
            "frontend/src/routes/+page.svelte",
            "docker-compose.yml",
            "Dockerfile.backend",
            "Dockerfile.frontend",
            "DEPLOYMENT.md",
            "DEMO_SCRIPT.md"
        ]
        
        for file_path in required_files:
            if os.path.exists(file_path):
                self.log_test(f"File: {file_path}", True, "Exists")
            else:
                self.log_test(f"File: {file_path}", False, "Missing")
    
    async def run_comprehensive_validation(self):
        """Run all validation tests"""
        print("🚀 EcoSmart AI - Comprehensive System Validation")
        print("=" * 60)
        print(f"⏰ Starting validation at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Test system requirements first
        self.test_system_requirements()
        self.test_file_structure()
        
        # Test network connectivity
        async with aiohttp.ClientSession() as session:
            await self.test_backend_health(session)
            await self.test_api_endpoints(session)
            await self.test_demo_scenarios(session)
            await self.test_device_control(session)
            await self.test_frontend_availability(session)
        
        # Test WebSocket separately
        await self.test_websocket_connection()
        
        # Generate summary report
        self.generate_validation_report()
    
    def generate_validation_report(self):
        """Generate final validation report"""
        print("\n" + "=" * 60)
        print("📊 SYSTEM VALIDATION SUMMARY")
        print("=" * 60)
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results if result['success'])
        failed_tests = total_tests - passed_tests
        
        success_rate = (passed_tests / total_tests) * 100 if total_tests > 0 else 0
        
        print(f"📈 Total Tests: {total_tests}")
        print(f"✅ Passed: {passed_tests}")
        print(f"❌ Failed: {failed_tests}")
        print(f"📊 Success Rate: {success_rate:.1f}%")
        
        if success_rate >= 95:
            print("\n🎉 SYSTEM STATUS: PRODUCTION READY! 🚀")
            print("✨ All critical components validated successfully")
        elif success_rate >= 80:
            print("\n⚠️ SYSTEM STATUS: MOSTLY READY")
            print("🔧 Minor issues detected, but system is functional")
        else:
            print("\n🚨 SYSTEM STATUS: NEEDS ATTENTION")
            print("❗ Critical issues detected, review required")
        
        if self.errors:
            print(f"\n🔍 Issues to Address ({len(self.errors)}):")
            for i, error in enumerate(self.errors, 1):
                print(f"   {i}. {error}")
        
        print(f"\n⏰ Validation completed at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60)
        
        # Save detailed report
        report = {
            "validation_time": datetime.now().isoformat(),
            "total_tests": total_tests,
            "passed_tests": passed_tests,
            "failed_tests": failed_tests,
            "success_rate": success_rate,
            "system_status": "PRODUCTION READY" if success_rate >= 95 else "NEEDS REVIEW",
            "test_results": self.test_results,
            "errors": self.errors
        }
        
        with open("validation_report.json", "w") as f:
            json.dump(report, f, indent=2)
        
        print("📄 Detailed report saved to: validation_report.json")

async def main():
    """Main validation function"""
    validator = SystemValidator()
    await validator.run_comprehensive_validation()

if __name__ == "__main__":
    print("🔧 EcoSmart AI System Validator")
    print("Make sure both backend and frontend are running:")
    print("  Backend: cd backend && python demo_server.py")
    print("  Frontend: cd frontend && npm run dev")
    print("\nStarting validation in 3 seconds...")
    time.sleep(3)
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n⚠️ Validation interrupted by user")
    except Exception as e:
        print(f"\n❌ Validation failed with error: {e}")
        sys.exit(1) 