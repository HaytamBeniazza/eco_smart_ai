<script lang="ts">
  import '../app.css';
  
  let currentTime = new Date().toLocaleTimeString();
  
  // Update time every second
  setInterval(() => {
    currentTime = new Date().toLocaleTimeString();
  }, 1000);
</script>

<div class="min-h-screen bg-gray-50">
  <!-- Header -->
  <header class="bg-white shadow-sm border-b border-gray-200">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
      <div class="flex justify-between items-center h-16">
        <div class="flex items-center space-x-3">
          <div class="w-8 h-8 bg-eco-green rounded-lg flex items-center justify-center">
            <svg class="w-5 h-5 text-white" fill="currentColor" viewBox="0 0 20 20">
              <path fill-rule="evenodd" d="M3.172 5.172a4 4 0 015.656 0L10 6.343l1.172-1.171a4 4 0 115.656 5.656L10 17.657l-6.828-6.829a4 4 0 010-5.656z" clip-rule="evenodd" />
            </svg>
          </div>
          <h1 class="text-xl font-semibold text-gray-900">EcoSmart AI</h1>
        </div>
        
        <div class="flex items-center space-x-4">
          <span class="text-sm text-gray-500">{currentTime}</span>
          <div class="flex items-center space-x-2">
            <div class="status-indicator status-online"></div>
            <span class="text-sm text-gray-600">System Online</span>
          </div>
        </div>
      </div>
    </div>
  </header>

  <!-- Main Content -->
  <main class="max-w-7xl mx-auto py-6 px-4 sm:px-6 lg:px-8">
    <slot />
  </main>
</div> 