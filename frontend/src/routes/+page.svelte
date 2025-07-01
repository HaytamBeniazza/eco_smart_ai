<script lang="ts">
  import EnergyMeter from '$lib/components/EnergyMeter.svelte';
  import WeatherWidget from '$lib/components/WeatherWidget.svelte';
  import CostSavings from '$lib/components/CostSavings.svelte';
  import DeviceGrid from '$lib/components/DeviceGrid.svelte';
  import AgentStatus from '$lib/components/AgentStatus.svelte';
  import OptimizationChart from '$lib/components/OptimizationChart.svelte';

  // Import WebSocket client and initialize connections
  import { wsClient } from '$lib/stores/api.js';
  import { 
    initializeEnergyWebSocket 
  } from '$lib/stores/energyStore.js';
  import { 
    initializeWeatherWebSocket 
  } from '$lib/stores/weatherStore.js';
  import { 
    initializeAgentsWebSocket 
  } from '$lib/stores/agentsStore.js';
  import { 
    initializeOptimizationWebSocket 
  } from '$lib/stores/optimizationStore.js';
  import { onMount, onDestroy } from 'svelte';

  // Modal state
  let showReportsModal = false;
  let showSettingsModal = false;

  // Button click handlers
  function openReports() {
    showReportsModal = true;
  }

  function openSettings() {
    showSettingsModal = true;
  }

  function closeModal() {
    showReportsModal = false;
    showSettingsModal = false;
  }

  onMount(() => {
    // Initialize WebSocket connection
    wsClient.connect();
    
    // Initialize all store WebSocket subscriptions
    initializeEnergyWebSocket();
    initializeWeatherWebSocket();
    initializeAgentsWebSocket();
    initializeOptimizationWebSocket();
  });

  onDestroy(() => {
    // Clean up WebSocket connection
    wsClient.disconnect();
  });
</script>

<svelte:head>
  <title>EcoSmart AI Dashboard</title>
  <meta name="description" content="Smart Energy Management Dashboard" />
</svelte:head>

<!-- Dashboard Header -->
<div class="mb-8">
  <div class="flex items-center justify-between">
    <div>
      <h1 class="text-3xl font-bold text-gray-900 mb-2">Energy Dashboard</h1>
      <p class="text-gray-600">Real-time monitoring and AI-powered optimization</p>
    </div>
    <div class="flex items-center space-x-4">
      <div class="text-right">
        <div class="text-sm text-gray-500">System Status</div>
        <div class="flex items-center space-x-2">
          <div class="status-indicator status-online"></div>
          <span class="text-sm font-medium text-green-600">All Systems Operational</span>
        </div>
      </div>
    </div>
  </div>
</div>

<!-- Main Dashboard Grid -->
<div class="grid grid-cols-1 lg:grid-cols-12 gap-6 mb-8">
  <!-- Left Column - Primary Metrics -->
  <div class="lg:col-span-4 space-y-6">
    <EnergyMeter />
    <WeatherWidget />
    <CostSavings />
  </div>
  
  <!-- Middle Column - Devices -->
  <div class="lg:col-span-5">
    <DeviceGrid />
  </div>
  
  <!-- Right Column - Agents -->
  <div class="lg:col-span-3">
    <AgentStatus />
  </div>
</div>

<!-- Bottom Row - Charts -->
<div class="grid grid-cols-1 gap-6">
  <OptimizationChart title="Energy Optimization Analytics" />
</div>

<!-- Quick Actions -->
<div class="mt-8 p-6 bg-gradient-to-r from-eco-green to-eco-blue rounded-lg text-white">
  <div class="flex items-center justify-between">
    <div>
      <h3 class="text-lg font-semibold mb-1">AI Optimization Active</h3>
      <p class="text-sm opacity-90">Your system is continuously learning and optimizing energy usage</p>
    </div>
    <div class="flex space-x-3">
      <button 
        on:click={openReports}
        class="bg-white bg-opacity-20 hover:bg-opacity-30 px-4 py-2 rounded-lg font-medium transition-colors">
        View Reports
      </button>
      <button 
        on:click={openSettings}
        class="bg-white text-eco-green px-4 py-2 rounded-lg font-medium hover:bg-gray-100 transition-colors">
        Settings
      </button>
    </div>
  </div>
</div>

<!-- Reports Modal -->
{#if showReportsModal}
<div class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50" on:click={closeModal}>
  <div class="bg-white rounded-lg p-6 m-4 max-w-4xl w-full max-h-[90vh] overflow-y-auto" on:click|stopPropagation>
    <div class="flex justify-between items-center mb-6">
      <h2 class="text-2xl font-bold text-gray-900">Energy Reports & Analytics</h2>
      <button on:click={closeModal} class="text-gray-500 hover:text-gray-700 text-xl">×</button>
    </div>
    
    <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
      <!-- Daily Summary -->
      <div class="bg-gray-50 p-4 rounded-lg">
        <h3 class="font-semibold text-lg mb-3">Today's Summary</h3>
        <div class="space-y-2">
          <div class="flex justify-between">
            <span>Total Consumption:</span>
            <span class="font-medium">47.3 kWh</span>
          </div>
          <div class="flex justify-between">
            <span>Cost Today:</span>
            <span class="font-medium">$6.84</span>
          </div>
          <div class="flex justify-between text-green-600">
            <span>Savings:</span>
            <span class="font-medium">$2.31 (25%)</span>
          </div>
          <div class="flex justify-between">
            <span>Peak Usage:</span>
            <span class="font-medium">2:30 PM</span>
          </div>
        </div>
      </div>

      <!-- Weekly Trends -->
      <div class="bg-gray-50 p-4 rounded-lg">
        <h3 class="font-semibold text-lg mb-3">Weekly Trends</h3>
        <div class="space-y-2">
          <div class="flex justify-between">
            <span>Average Daily Usage:</span>
            <span class="font-medium">45.8 kWh</span>
          </div>
          <div class="flex justify-between">
            <span>Best Day:</span>
            <span class="font-medium">Tuesday (-18%)</span>
          </div>
          <div class="flex justify-between">
            <span>Total Savings:</span>
            <span class="font-medium text-green-600">$16.47</span>
          </div>
          <div class="flex justify-between">
            <span>Efficiency Score:</span>
            <span class="font-medium">87/100</span>
          </div>
        </div>
      </div>

      <!-- AI Insights -->
      <div class="bg-blue-50 p-4 rounded-lg md:col-span-2">
        <h3 class="font-semibold text-lg mb-3">AI Optimization Insights</h3>
        <div class="space-y-3">
          <div class="flex items-start space-x-3">
            <div class="w-2 h-2 bg-blue-500 rounded-full mt-2"></div>
            <p class="text-sm">Your HVAC system is running 23% more efficiently since AI optimization began</p>
          </div>
          <div class="flex items-start space-x-3">
            <div class="w-2 h-2 bg-green-500 rounded-full mt-2"></div>
            <p class="text-sm">Solar panel output prediction accuracy improved to 94%</p>
          </div>
          <div class="flex items-start space-x-3">
            <div class="w-2 h-2 bg-yellow-500 rounded-full mt-2"></div>
            <p class="text-sm">Recommended: Consider scheduling dishwasher during off-peak hours (11 PM - 6 AM)</p>
          </div>
        </div>
      </div>
    </div>

    <div class="mt-6 flex justify-end space-x-3">
      <button on:click={closeModal} class="px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50">
        Close
      </button>
      <button class="px-4 py-2 bg-eco-green text-white rounded-lg hover:bg-green-600">
        Export Report
      </button>
    </div>
  </div>
</div>
{/if}

<!-- Settings Modal -->
{#if showSettingsModal}
<div class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50" on:click={closeModal}>
  <div class="bg-white rounded-lg p-6 m-4 max-w-2xl w-full max-h-[90vh] overflow-y-auto" on:click|stopPropagation>
    <div class="flex justify-between items-center mb-6">
      <h2 class="text-2xl font-bold text-gray-900">System Settings</h2>
      <button on:click={closeModal} class="text-gray-500 hover:text-gray-700 text-xl">×</button>
    </div>
    
    <div class="space-y-6">
      <!-- AI Optimization Settings -->
      <div class="border-b pb-4">
        <h3 class="font-semibold text-lg mb-3">AI Optimization</h3>
        <div class="space-y-4">
          <div class="flex items-center justify-between">
            <label class="text-sm font-medium">Auto-optimization enabled</label>
            <input type="checkbox" checked class="toggle-checkbox" />
          </div>
          <div class="flex items-center justify-between">
            <label class="text-sm font-medium">Aggressive savings mode</label>
            <input type="checkbox" class="toggle-checkbox" />
          </div>
          <div>
            <label class="text-sm font-medium block mb-2">Optimization sensitivity</label>
            <input type="range" min="1" max="10" value="7" class="w-full" />
            <div class="flex justify-between text-xs text-gray-500 mt-1">
              <span>Conservative</span>
              <span>Aggressive</span>
            </div>
          </div>
        </div>
      </div>

      <!-- Device Control Settings -->
      <div class="border-b pb-4">
        <h3 class="font-semibold text-lg mb-3">Device Control</h3>
        <div class="space-y-4">
          <div class="flex items-center justify-between">
            <label class="text-sm font-medium">Allow automatic device scheduling</label>
            <input type="checkbox" checked class="toggle-checkbox" />
          </div>
          <div class="flex items-center justify-between">
            <label class="text-sm font-medium">Peak hours avoidance</label>
            <input type="checkbox" checked class="toggle-checkbox" />
          </div>
          <div>
            <label class="text-sm font-medium block mb-2">Temperature comfort range</label>
            <div class="flex space-x-4">
              <input type="number" value="68" min="60" max="80" class="w-20 px-2 py-1 border rounded" />
              <span class="py-1">to</span>
              <input type="number" value="76" min="60" max="80" class="w-20 px-2 py-1 border rounded" />
              <span class="py-1">°F</span>
            </div>
          </div>
        </div>
      </div>

      <!-- Notifications -->
      <div class="border-b pb-4">
        <h3 class="font-semibold text-lg mb-3">Notifications</h3>
        <div class="space-y-4">
          <div class="flex items-center justify-between">
            <label class="text-sm font-medium">Energy alerts</label>
            <input type="checkbox" checked class="toggle-checkbox" />
          </div>
          <div class="flex items-center justify-between">
            <label class="text-sm font-medium">Weekly reports</label>
            <input type="checkbox" checked class="toggle-checkbox" />
          </div>
          <div class="flex items-center justify-between">
            <label class="text-sm font-medium">Device malfunction alerts</label>
            <input type="checkbox" checked class="toggle-checkbox" />
          </div>
        </div>
      </div>

      <!-- Data & Privacy -->
      <div>
        <h3 class="font-semibold text-lg mb-3">Data & Privacy</h3>
        <div class="space-y-4">
          <div class="flex items-center justify-between">
            <label class="text-sm font-medium">Share usage data for optimization</label>
            <input type="checkbox" checked class="toggle-checkbox" />
          </div>
          <div class="flex items-center justify-between">
            <label class="text-sm font-medium">Cloud backup</label>
            <input type="checkbox" checked class="toggle-checkbox" />
          </div>
          <button class="text-sm text-blue-600 hover:text-blue-800">Export my data</button>
        </div>
      </div>
    </div>

    <div class="mt-6 flex justify-end space-x-3">
      <button on:click={closeModal} class="px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50">
        Cancel
      </button>
      <button class="px-4 py-2 bg-eco-green text-white rounded-lg hover:bg-green-600">
        Save Settings
      </button>
    </div>
  </div>
</div>
{/if}
