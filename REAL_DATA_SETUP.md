# 🌍 EcoSmart AI Real Data Integration Guide

Transform your demo system into a **REAL** smart home energy management platform!

## 🔧 Current Integration Status

| Data Source | Status | Implementation |
|-------------|--------|----------------|
| **Weather Data** | ✅ **ACTIVE** | OpenWeatherMap API integration **WORKING** |
| **Smart Devices** | ❓ Ready for Setup | TP-Link Kasa, Home Assistant frameworks ready |
| **Energy Meters** | ❓ Ready for Setup | Smart meter integration framework ready |

> 🎉 **WEATHER DATA IS LIVE!** Your system is now pulling real weather data from Casablanca, Morocco!

## 🚀 Quick Start Options (Choose Your Path)

### 🌤️ **OPTION 1: Real Weather Data (5 minutes, FREE)**
**What you get:** Real temperature, humidity, wind speed, solar potential for your location

1. **Get FREE API Key:**
   - Go to: https://openweathermap.org/api
   - Sign up (free)
   - Get your API key

2. **Add to your system:**
   ```bash
   # Add to your environment variables
   export OPENWEATHER_API_KEY="your_key_here"
   
   # Or create .env file in backend folder:
   echo "OPENWEATHER_API_KEY=your_key_here" > backend/.env
   ```

3. **Set your location:**
   ```python
   # In backend/real_data_integrations.py, change:
   city = "Your_City"        # e.g., "New York", "London", "Casablanca"
   country = "Your_Country"  # e.g., "US", "GB", "MA"
   ```

### ⚡ **OPTION 2: Real Smart Devices**

#### **2A. TP-Link Kasa Smart Plugs (Recommended)**
**What you need:** TP-Link Kasa smart plugs with energy monitoring

1. **Install Kasa library:**
   ```bash
   cd backend
   pip install python-kasa
   ```

2. **Setup your Kasa devices:**
   - Connect Kasa smart plugs to your WiFi
   - Use Kasa app to name devices
   - Make sure they're on same network as your computer

3. **Test discovery:**
   ```bash
   python -c "import asyncio; import kasa; asyncio.run(kasa.Discover.discover())"
   ```

#### **2B. Home Assistant Integration**
**What you need:** Home Assistant running with energy sensors

1. **Get Home Assistant token:**
   - Go to Home Assistant → Profile → Long-Lived Access Tokens
   - Create new token

2. **Add credentials:**
   ```bash
   export HOMEASSISTANT_URL="http://your-homeassistant:8123"
   export HOMEASSISTANT_TOKEN="your_token_here"
   ```

#### **2C. Smart Electricity Meter**
**What you need:** Smart meter with API access or HAN port

- **Check with your utility company** for API access
- **Look for HAN port** on your smart meter
- **Consider smart meter readers** like:
  - Emporia Vue
  - Sense Home Energy Monitor
  - TP-Link Kasa KP125M (plug-level monitoring)

## 🔧 **Integration Steps**

### **Step 1: Choose Your Location & API Key**
```bash
# Tell me your location for weather integration:
```
**What city/country are you in?** _______________

### **Step 2: Check Your Smart Devices**
**Do you have any of these?** (Check all that apply)
- [ ] TP-Link Kasa smart plugs
- [ ] Home Assistant setup
- [ ] Smart thermostat (Nest, Ecobee, Honeywell)
- [ ] Smart electricity meter
- [ ] Other smart home devices: _______________

### **Step 3: Test Current Hardware**
Run this command to check what's available:

```bash
cd backend
python -c "
import os
print('🔍 Checking for available real data sources...')

# Check for OpenWeather API key
weather_key = os.getenv('OPENWEATHER_API_KEY')
if weather_key:
    print('✅ OpenWeather API key found')
else:
    print('❌ OpenWeather API key missing')

# Check for Python libraries
try:
    import kasa
    print('✅ TP-Link Kasa library available')
except ImportError:
    print('❌ TP-Link Kasa library not installed')

# Check Home Assistant credentials
ha_url = os.getenv('HOMEASSISTANT_URL')
ha_token = os.getenv('HOMEASSISTANT_TOKEN')
if ha_url and ha_token:
    print('✅ Home Assistant credentials found')
else:
    print('❌ Home Assistant credentials missing')

print('\\n🎯 Ready to integrate real data!')
"
```
</function_calls> 