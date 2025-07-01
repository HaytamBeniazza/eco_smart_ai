"""
EcoSmart AI Performance Configuration
Optimizations for production deployment and high-load scenarios
"""

import asyncio
import logging
from typing import Dict, Any
import psutil
import gc
from datetime import datetime, timedelta

class PerformanceConfig:
    """Performance optimization configuration for EcoSmart AI"""
    
    def __init__(self):
        self.config = {
            # Agent Performance Settings
            "agent_polling_intervals": {
                "monitor": 15,      # Reduced from 30s for better responsiveness
                "weather": 300,     # 5 minutes (was 900s)
                "optimizer": 60,    # 1 minute (was 300s) 
                "controller": 10    # 10 seconds for device control
            },
            
            # WebSocket Configuration
            "websocket": {
                "max_connections": 100,
                "heartbeat_interval": 30,
                "message_queue_size": 1000,
                "compression": True
            },
            
            # Database Optimization
            "database": {
                "connection_pool_size": 20,
                "max_overflow": 30,
                "pool_timeout": 30,
                "pool_recycle": 1800,  # 30 minutes
                "echo": False  # Disable SQL logging in production
            },
            
            # Memory Management
            "memory": {
                "garbage_collection_interval": 300,  # 5 minutes
                "max_memory_usage_mb": 512,
                "scenario_results_retention": 100,  # Keep last 100 results
                "log_retention_hours": 24
            },
            
            # API Rate Limiting
            "rate_limiting": {
                "requests_per_minute": 60,
                "burst_limit": 10,
                "scenarios_per_hour": 20
            },
            
            # Caching Configuration
            "caching": {
                "weather_cache_minutes": 15,
                "device_status_cache_seconds": 5,
                "optimization_cache_minutes": 2,
                "pricing_cache_hours": 24
            }
        }
        
        # System resource monitoring
        self.system_stats = {
            "cpu_usage": 0.0,
            "memory_usage": 0.0,
            "disk_usage": 0.0,
            "active_connections": 0
        }
        
        self.performance_logger = self._setup_performance_logging()
        
    def _setup_performance_logging(self) -> logging.Logger:
        """Setup performance monitoring logger"""
        logger = logging.getLogger("ecosmart.performance")
        logger.setLevel(logging.INFO)
        
        if not logger.handlers:
            handler = logging.FileHandler("logs/performance.log")
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        
        return logger
    
    async def monitor_system_resources(self):
        """Monitor system resource usage"""
        while True:
            try:
                # CPU usage
                self.system_stats["cpu_usage"] = psutil.cpu_percent(interval=1)
                
                # Memory usage
                memory = psutil.virtual_memory()
                self.system_stats["memory_usage"] = memory.percent
                
                # Disk usage
                disk = psutil.disk_usage('/')
                self.system_stats["disk_usage"] = disk.percent
                
                # Log performance metrics
                self.performance_logger.info(
                    f"System Stats - CPU: {self.system_stats['cpu_usage']}%, "
                    f"Memory: {self.system_stats['memory_usage']}%, "
                    f"Disk: {self.system_stats['disk_usage']}%"
                )
                
                # Alert if resources are high
                if self.system_stats["cpu_usage"] > 80:
                    self.performance_logger.warning(f"High CPU usage: {self.system_stats['cpu_usage']}%")
                
                if self.system_stats["memory_usage"] > 85:
                    self.performance_logger.warning(f"High memory usage: {self.system_stats['memory_usage']}%")
                
                await asyncio.sleep(60)  # Check every minute
                
            except Exception as e:
                self.performance_logger.error(f"Error monitoring system resources: {e}")
                await asyncio.sleep(60)
    
    async def cleanup_old_data(self):
        """Cleanup old data to prevent memory bloat"""
        while True:
            try:
                # This would connect to your database and clean old records
                cutoff_time = datetime.now() - timedelta(hours=self.config["memory"]["log_retention_hours"])
                
                # Clean old scenario results (in production, this would use your DB)
                self.performance_logger.info("Cleaning up old data records")
                
                # Force garbage collection
                gc.collect()
                self.performance_logger.info("Garbage collection completed")
                
                await asyncio.sleep(self.config["memory"]["garbage_collection_interval"])
                
            except Exception as e:
                self.performance_logger.error(f"Error during cleanup: {e}")
                await asyncio.sleep(300)  # Retry in 5 minutes
    
    def get_optimized_config(self) -> Dict[str, Any]:
        """Get optimized configuration based on current system load"""
        
        # Adjust polling intervals based on CPU usage
        if self.system_stats["cpu_usage"] > 70:
            # Reduce frequency under high load
            optimized = self.config.copy()
            optimized["agent_polling_intervals"]["monitor"] = 30
            optimized["agent_polling_intervals"]["optimizer"] = 120
            self.performance_logger.info("Applied high-load optimizations")
            return optimized
        
        elif self.system_stats["cpu_usage"] < 30:
            # Increase frequency under low load for better responsiveness
            optimized = self.config.copy()
            optimized["agent_polling_intervals"]["monitor"] = 10
            optimized["agent_polling_intervals"]["optimizer"] = 30
            self.performance_logger.info("Applied low-load optimizations")
            return optimized
        
        return self.config
    
    def get_system_health(self) -> Dict[str, Any]:
        """Get current system health metrics"""
        return {
            "status": "healthy" if all(
                stat < 80 for stat in [
                    self.system_stats["cpu_usage"],
                    self.system_stats["memory_usage"],
                    self.system_stats["disk_usage"]
                ]
            ) else "warning",
            "metrics": self.system_stats,
            "config": self.get_optimized_config(),
            "timestamp": datetime.now().isoformat()
        }
    
    async def start_performance_monitoring(self):
        """Start all performance monitoring tasks"""
        self.performance_logger.info("Starting performance monitoring")
        
        # Create background tasks
        tasks = [
            asyncio.create_task(self.monitor_system_resources()),
            asyncio.create_task(self.cleanup_old_data())
        ]
        
        try:
            await asyncio.gather(*tasks)
        except Exception as e:
            self.performance_logger.error(f"Performance monitoring error: {e}")

# Global performance configuration instance
performance_config = PerformanceConfig()

# Optimized configurations for different deployment scenarios
DEPLOYMENT_CONFIGS = {
    "development": {
        "agent_intervals": {"monitor": 30, "weather": 900, "optimizer": 300, "controller": 30},
        "log_level": "DEBUG",
        "cache_enabled": False
    },
    
    "staging": {
        "agent_intervals": {"monitor": 20, "weather": 600, "optimizer": 120, "controller": 15},
        "log_level": "INFO", 
        "cache_enabled": True
    },
    
    "production": {
        "agent_intervals": {"monitor": 15, "weather": 300, "optimizer": 60, "controller": 10},
        "log_level": "WARNING",
        "cache_enabled": True,
        "monitoring_enabled": True
    }
}

def get_deployment_config(environment: str = "production") -> Dict[str, Any]:
    """Get configuration for specific deployment environment"""
    return DEPLOYMENT_CONFIGS.get(environment, DEPLOYMENT_CONFIGS["production"]) 