"""
Monitoring orchestrator - integrates all monitoring components into a unified system.
Provides a single entry point for initializing and managing the comprehensive monitoring suite.
"""

import asyncio
import os
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
from pathlib import Path
import logging
from dataclasses import dataclass, field

from .enhanced_logging import initialize_enhanced_logging, get_monitoring_stats
from .health_monitoring import initialize_health_monitoring, get_health_monitor
from .monitoring_dashboard import initialize_dashboard, get_dashboard
from .monitoring_api import initialize_monitoring_api, MonitoringAPIConfig, create_default_config
from .log_aggregation import initialize_centralized_logging, get_logging_service


@dataclass
class MonitoringConfig:
    """Configuration for the monitoring system"""
    # Service configuration
    service_name: str = "selfology"
    environment: str = "development"
    
    # Database configuration - selfology-postgres (порт 5434)
    database: Dict[str, Any] = field(default_factory=lambda: {
        "host": os.getenv("DB_HOST", "localhost"),
        "port": int(os.getenv("DB_PORT", "5434")),
        "user": os.getenv("DB_USER", "selfology_user"),
        "password": os.getenv("DB_PASSWORD", "selfology_secure_2024"),
        "database": os.getenv("DB_NAME", "selfology")
    })
    
    # AI services configuration
    ai_services: Dict[str, Dict[str, str]] = field(default_factory=lambda: {
        "openai": {
            "api_key": os.getenv("OPENAI_API_KEY", "")
        },
        "claude": {
            "api_key": os.getenv("ANTHROPIC_API_KEY", "")
        }
    })
    
    # Vector database configuration
    vector_db: Dict[str, str] = field(default_factory=lambda: {
        "url": os.getenv("QDRANT_URL", "http://localhost:6333"),
        "api_key": os.getenv("QDRANT_API_KEY", "")
    })
    
    # Telegram bot configuration
    telegram_bot: Dict[str, str] = field(default_factory=lambda: {
        "token": os.getenv("BOT_TOKEN", "")
    })
    
    # Dashboard configuration
    dashboard_host: str = "localhost"
    dashboard_port: int = 8000
    
    # API configuration
    api_host: str = "localhost"
    api_port: int = 8001
    api_keys: List[str] = field(default_factory=lambda: [
        os.getenv("MONITORING_API_KEY", "selfology_monitoring_key_123")
    ])
    
    # Log aggregation configuration
    log_storage_path: str = "logs/aggregation.db"
    log_retention_days: int = 30
    
    # Monitoring features
    enable_dashboard: bool = True
    enable_api: bool = True
    enable_log_aggregation: bool = True
    enable_health_monitoring: bool = True
    enable_webhooks: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary"""
        return {
            'service_name': self.service_name,
            'environment': self.environment,
            'database': self.database,
            'ai_services': self.ai_services,
            'vector_db': self.vector_db,
            'telegram_bot': self.telegram_bot,
            'dashboard': {
                'host': self.dashboard_host,
                'port': self.dashboard_port,
                'enabled': self.enable_dashboard
            },
            'api': {
                'host': self.api_host,
                'port': self.api_port,
                'enabled': self.enable_api
            },
            'log_aggregation': {
                'storage_path': self.log_storage_path,
                'retention_days': self.log_retention_days,
                'enabled': self.enable_log_aggregation
            },
            'health_monitoring': {
                'enabled': self.enable_health_monitoring
            }
        }


class MonitoringOrchestrator:
    """Main orchestrator for the monitoring system"""
    
    def __init__(self, config: MonitoringConfig):
        self.config = config
        self.components = {}
        self.running = False
        self.startup_time = datetime.now(timezone.utc)
        self.logger = logging.getLogger(f'{config.service_name}.monitoring')
    
    async def initialize(self) -> bool:
        """Initialize all monitoring components"""
        try:
            self.logger.info(f"Initializing monitoring system for {self.config.service_name}")
            
            # 1. Initialize enhanced logging system first
            enhanced_logging = initialize_enhanced_logging(
                self.config.service_name, 
                self.config.environment
            )
            self.components['logging'] = enhanced_logging
            self.logger.info("✓ Enhanced logging system initialized")
            
            # 2. Initialize health monitoring
            if self.config.enable_health_monitoring:
                health_monitor = initialize_health_monitoring(self.config.to_dict())
                self.components['health_monitor'] = health_monitor
                self.logger.info("✓ Health monitoring initialized")
            
            # 3. Initialize centralized log aggregation
            if self.config.enable_log_aggregation:
                logging_service = initialize_centralized_logging(self.config.log_storage_path)
                self.components['log_aggregation'] = logging_service
                self.logger.info("✓ Log aggregation service initialized")
            
            # 4. Initialize monitoring dashboard
            if self.config.enable_dashboard:
                dashboard = initialize_dashboard(
                    self.config.dashboard_host,
                    self.config.dashboard_port
                )
                self.components['dashboard'] = dashboard
                self.logger.info("✓ Monitoring dashboard initialized")
            
            # 5. Initialize monitoring API
            if self.config.enable_api:
                api_config = create_default_config(self.config.api_keys)
                api_config.enable_webhooks = self.config.enable_webhooks
                
                monitoring_api = initialize_monitoring_api(
                    api_config,
                    self.config.api_host,
                    self.config.api_port
                )
                self.components['api'] = monitoring_api
                self.logger.info("✓ Monitoring API initialized")
            
            self.logger.info("🎉 All monitoring components initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Failed to initialize monitoring system: {e}")
            return False
    
    async def start(self) -> bool:
        """Start all monitoring components"""
        if self.running:
            self.logger.warning("Monitoring system is already running")
            return True
        
        try:
            self.logger.info("Starting monitoring system...")
            
            # Start components in order
            start_tasks = []
            
            # 1. Start log aggregation service
            if 'log_aggregation' in self.components:
                start_tasks.append(
                    self._start_component('log_aggregation', 
                                        self.components['log_aggregation'].start_service())
                )
            
            # 2. Start health monitoring
            if 'health_monitor' in self.components:
                start_tasks.append(
                    self._start_component('health_monitor', 
                                        self.components['health_monitor'].start_monitoring())
                )
            
            # 3. Start dashboard and API in parallel (they run their own servers)
            if 'dashboard' in self.components:
                start_tasks.append(
                    self._start_component('dashboard', 
                                        self.components['dashboard'].start_dashboard())
                )
            
            if 'api' in self.components:
                start_tasks.append(
                    self._start_component('api', 
                                        self.components['api'].start_api())
                )
            
            # Start all components concurrently
            if start_tasks:
                await asyncio.gather(*start_tasks, return_exceptions=True)
            
            self.running = True
            self.logger.info("🚀 Monitoring system started successfully")
            
            # Log system status
            await self._log_system_status()
            
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Failed to start monitoring system: {e}")
            return False
    
    async def _start_component(self, name: str, coro):
        """Start a component with error handling"""
        try:
            self.logger.info(f"Starting {name}...")
            await coro
            self.logger.info(f"✓ {name} started")
        except Exception as e:
            self.logger.error(f"❌ Failed to start {name}: {e}")
            raise
    
    async def stop(self):
        """Stop all monitoring components"""
        if not self.running:
            return
        
        self.logger.info("Stopping monitoring system...")
        
        # Stop components in reverse order
        stop_tasks = []
        
        if 'health_monitor' in self.components:
            stop_tasks.append(self.components['health_monitor'].stop_monitoring())
        
        if 'log_aggregation' in self.components:
            stop_tasks.append(self.components['log_aggregation'].stop_service())
        
        # API and dashboard servers are stopped when the process exits
        
        if stop_tasks:
            await asyncio.gather(*stop_tasks, return_exceptions=True)
        
        self.running = False
        self.logger.info("🛑 Monitoring system stopped")
    
    async def _log_system_status(self):
        """Log comprehensive system status"""
        status = await self.get_system_status()
        
        self.logger.info("📊 System Status Summary:")
        self.logger.info(f"  Service: {status['service_name']}")
        self.logger.info(f"  Environment: {status['environment']}")
        self.logger.info(f"  Uptime: {status['uptime_seconds']:.1f}s")
        self.logger.info(f"  Components: {len(status['components'])} active")
        
        for component, details in status['components'].items():
            status_icon = "✓" if details['status'] == 'active' else "❌"
            self.logger.info(f"  {status_icon} {component}: {details['status']}")
        
        if status.get('endpoints'):
            self.logger.info("🌐 Available endpoints:")
            for endpoint, url in status['endpoints'].items():
                self.logger.info(f"  • {endpoint}: {url}")
    
    async def get_system_status(self) -> Dict[str, Any]:
        """Get comprehensive system status"""
        uptime = (datetime.now(timezone.utc) - self.startup_time).total_seconds()
        
        status = {
            'service_name': self.config.service_name,
            'environment': self.config.environment,
            'uptime_seconds': uptime,
            'running': self.running,
            'startup_time': self.startup_time.isoformat(),
            'components': {},
            'endpoints': {}
        }
        
        # Check component status
        for component_name, component in self.components.items():
            component_status = 'active' if self.running else 'inactive'
            
            if component_name == 'health_monitor' and hasattr(component, 'current_status'):
                health_data = await component.get_current_health_status()
                component_status = health_data.get('status', 'unknown')
            
            status['components'][component_name] = {
                'status': component_status,
                'type': type(component).__name__
            }
        
        # Add endpoint information
        if self.config.enable_dashboard:
            status['endpoints']['dashboard'] = f"http://{self.config.dashboard_host}:{self.config.dashboard_port}"
        
        if self.config.enable_api:
            status['endpoints']['api'] = f"http://{self.config.api_host}:{self.config.api_port}"
            status['endpoints']['prometheus'] = f"http://{self.config.api_host}:{self.config.api_port}/metrics"
        
        # Add monitoring stats
        try:
            monitoring_stats = get_monitoring_stats()
            status['monitoring_stats'] = monitoring_stats
        except Exception as e:
            self.logger.warning(f"Could not get monitoring stats: {e}")
        
        return status
    
    def get_component(self, component_name: str):
        """Get specific component instance"""
        return self.components.get(component_name)
    
    def is_running(self) -> bool:
        """Check if monitoring system is running"""
        return self.running
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check of monitoring system"""
        health_status = {
            'healthy': True,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'components': {}
        }
        
        # Check each component
        for component_name, component in self.components.items():
            try:
                if component_name == 'health_monitor' and hasattr(component, 'get_current_health_status'):
                    component_health = await component.get_current_health_status()
                    health_status['components'][component_name] = {
                        'healthy': component_health.get('status') == 'healthy',
                        'details': component_health
                    }
                else:
                    # Basic health check - component exists and system is running
                    health_status['components'][component_name] = {
                        'healthy': self.running and component is not None,
                        'details': {'status': 'active' if self.running else 'inactive'}
                    }
            
            except Exception as e:
                health_status['components'][component_name] = {
                    'healthy': False,
                    'details': {'error': str(e)}
                }
                health_status['healthy'] = False
        
        return health_status
    
    async def get_metrics_summary(self) -> Dict[str, Any]:
        """Get comprehensive metrics summary"""
        summary = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'system_status': await self.get_system_status(),
            'health_check': await self.health_check()
        }
        
        # Add component-specific metrics
        if 'dashboard' in self.components:
            try:
                dashboard_metrics = await self.components['dashboard'].data_provider.get_dashboard_data()
                summary['dashboard_metrics'] = dashboard_metrics.to_dict()
            except Exception as e:
                self.logger.warning(f"Could not get dashboard metrics: {e}")
        
        if 'log_aggregation' in self.components:
            try:
                log_analysis = await self.components['log_aggregation'].get_log_analysis(24)
                summary['log_analysis'] = log_analysis
            except Exception as e:
                self.logger.warning(f"Could not get log analysis: {e}")
        
        return summary


# Convenience functions for global orchestrator management
_global_orchestrator = None

def initialize_monitoring_system(config: MonitoringConfig) -> MonitoringOrchestrator:
    """Initialize the global monitoring system"""
    global _global_orchestrator
    _global_orchestrator = MonitoringOrchestrator(config)
    return _global_orchestrator

def get_monitoring_orchestrator() -> Optional[MonitoringOrchestrator]:
    """Get global monitoring orchestrator instance"""
    return _global_orchestrator

async def start_monitoring_system() -> bool:
    """Start the global monitoring system"""
    if _global_orchestrator:
        await _global_orchestrator.initialize()
        return await _global_orchestrator.start()
    return False

async def stop_monitoring_system():
    """Stop the global monitoring system"""
    if _global_orchestrator:
        await _global_orchestrator.stop()

def create_default_monitoring_config() -> MonitoringConfig:
    """Create default monitoring configuration"""
    return MonitoringConfig()

# Integration helpers for the main bot
def setup_monitoring_for_bot(bot_token: str, **kwargs) -> MonitoringConfig:
    """Setup monitoring configuration specifically for the Telegram bot"""
    config = MonitoringConfig(**kwargs)
    config.telegram_bot['token'] = bot_token
    return config

def get_monitoring_stats_for_dashboard() -> Dict[str, Any]:
    """Get monitoring stats formatted for dashboard display"""
    if _global_orchestrator:
        # This would be called periodically to update the dashboard
        import asyncio
        try:
            return asyncio.create_task(_global_orchestrator.get_metrics_summary())
        except:
            return get_monitoring_stats()
    return get_monitoring_stats()
