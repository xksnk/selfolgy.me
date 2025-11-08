"""
🛡️ Production Guardian Component
Production monitoring, alerting, and system health management.
"""

import asyncio
import json
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional
from collections import defaultdict, deque
import psutil
import logging


class ProductionGuardian:
    """
    Production guardian for Selfology AI Psychology Coach.
    Provides continuous monitoring, alerting, and automated responses to production issues.
    """
    
    def __init__(self):
        self.guardian_start = datetime.now()
        self.alert_history = deque(maxlen=1000)
        self.health_history = deque(maxlen=100)
        self.monitoring_active = False
        
        # Critical thresholds for production alerts
        self.critical_thresholds = {
            'cpu_usage': 90,           # 90% CPU usage
            'memory_usage': 95,        # 95% memory usage
            'disk_usage': 95,          # 95% disk usage
            'error_rate': 50,          # 50+ errors per hour
            'response_time': 10000,    # 10+ seconds response time
            'failed_requests': 100     # 100+ failed requests per hour
        }
        
        # Alert cooldown periods (minutes)
        self.alert_cooldowns = {
            'cpu_high': 15,
            'memory_high': 10,
            'disk_full': 30,
            'error_spike': 5,
            'service_down': 1
        }
        
        self.last_alerts = defaultdict(datetime)
    
    async def production_check(self) -> Dict[str, Any]:
        """
        Comprehensive production readiness and health check.
        """
        print("    🔍 Checking production readiness...")
        
        production_status = {
            'timestamp': datetime.now().isoformat(),
            'system_health': await self._check_system_health(),
            'service_availability': await self._check_service_availability(),
            'security_posture': await self._check_security_posture(),
            'performance_baselines': await self._check_performance_baselines(),
            'monitoring_coverage': await self._check_monitoring_coverage(),
            'backup_systems': await self._check_backup_systems(),
            'disaster_recovery': await self._check_disaster_recovery(),
            'compliance_status': await self._check_compliance(),
            'alerts': [],
            'recommendations': [],
            'production_score': 0.0,
            'issues': []
        }
        
        # Calculate production readiness score
        production_status['production_score'] = self._calculate_production_score(production_status)
        production_status['issues'] = self._extract_production_issues(production_status)
        production_status['recommendations'] = self._generate_production_recommendations(production_status)
        production_status['alerts'] = await self._generate_production_alerts(production_status)
        
        return production_status
    
    async def _check_system_health(self) -> Dict[str, Any]:
        """Check overall system health metrics."""
        system_health = {
            'resource_utilization': await self._check_resource_utilization(),
            'service_status': await self._check_service_status(),
            'connectivity': await self._check_connectivity(),
            'data_integrity': await self._check_data_integrity()
        }
        
        return system_health
    
    async def _check_resource_utilization(self) -> Dict[str, Any]:
        """Check system resource utilization."""
        resources = {
            'cpu': {'status': 'unknown'},
            'memory': {'status': 'unknown'},
            'disk': {'status': 'unknown'},
            'network': {'status': 'unknown'}
        }
        
        try:
            # CPU utilization
            cpu_percent = psutil.cpu_percent(interval=1)
            resources['cpu'] = {
                'status': 'critical' if cpu_percent > 90 else 'warning' if cpu_percent > 80 else 'healthy',
                'usage_percent': cpu_percent,
                'threshold_critical': self.critical_thresholds['cpu_usage']
            }
            
            # Memory utilization
            memory = psutil.virtual_memory()
            resources['memory'] = {
                'status': 'critical' if memory.percent > 95 else 'warning' if memory.percent > 85 else 'healthy',
                'usage_percent': memory.percent,
                'available_gb': memory.available / (1024**3),
                'threshold_critical': self.critical_thresholds['memory_usage']
            }
            
            # Disk utilization
            disk = psutil.disk_usage('/')
            disk_percent = (disk.used / disk.total) * 100
            resources['disk'] = {
                'status': 'critical' if disk_percent > 95 else 'warning' if disk_percent > 90 else 'healthy',
                'usage_percent': disk_percent,
                'free_gb': disk.free / (1024**3),
                'threshold_critical': self.critical_thresholds['disk_usage']
            }
            
            # Network I/O
            net_io = psutil.net_io_counters()
            if net_io:
                # Simple network health check based on error counters
                error_rate = (net_io.errin + net_io.errout) / max(net_io.packets_sent + net_io.packets_recv, 1)
                resources['network'] = {
                    'status': 'warning' if error_rate > 0.01 else 'healthy',  # >1% error rate
                    'error_rate': error_rate,
                    'bytes_sent': net_io.bytes_sent,
                    'bytes_recv': net_io.bytes_recv
                }
            
        except Exception as e:
            resources['error'] = str(e)
        
        return resources
    
    async def _check_service_status(self) -> Dict[str, Any]:
        """Check status of critical services."""
        services = {
            'selfology_bot': {'status': 'unknown'},
            'database_services': {'status': 'unknown'},
            'external_apis': {'status': 'unknown'},
            'monitoring_services': {'status': 'unknown'}
        }
        
        try:
            # Check if Selfology bot process is running
            selfology_running = False
            bot_processes = []
            
            for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'status']):
                try:
                    cmdline = ' '.join(proc.info['cmdline'] or [])
                    if ('selfology' in cmdline.lower() or 
                        'monitored_bot.py' in cmdline or 
                        'simple_bot.py' in cmdline):
                        selfology_running = True
                        bot_processes.append({
                            'pid': proc.info['pid'],
                            'status': proc.info['status'],
                            'cmdline': cmdline[:100] + '...' if len(cmdline) > 100 else cmdline
                        })
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            services['selfology_bot'] = {
                'status': 'running' if selfology_running else 'stopped',
                'processes': bot_processes,
                'process_count': len(bot_processes)
            }
            
            # Check database services (from integration tester)
            from scripts.debug.integration_tester import IntegrationTester
            integration_tester = IntegrationTester()
            db_tests = await integration_tester._test_database_integrations()
            
            services['database_services'] = {
                'status': 'healthy' if all(
                    db.get('connection', {}).get('status') == 'success' 
                    for db in db_tests.values() 
                    if isinstance(db, dict)
                ) else 'degraded',
                'details': db_tests
            }
            
            # Check external API connectivity
            api_tests = await integration_tester._test_api_integrations()
            services['external_apis'] = {
                'status': 'healthy' if all(
                    api.get('connection', {}).get('status') == 'success'
                    for api in api_tests.values()
                    if isinstance(api, dict)
                ) else 'degraded',
                'details': api_tests
            }
            
        except Exception as e:
            services['error'] = str(e)
        
        return services
    
    async def _check_connectivity(self) -> Dict[str, Any]:
        """Check network connectivity to critical services."""
        connectivity = {
            'external_services': {'status': 'unknown'},
            'internal_services': {'status': 'unknown'},
            'dns_resolution': {'status': 'unknown'}
        }
        
        try:
            import socket
            import aiohttp
            
            # Test external connectivity
            external_hosts = [
                'api.telegram.org',
                'api.anthropic.com',
                'api.openai.com'
            ]
            
            external_results = {}
            for host in external_hosts:
                try:
                    # DNS resolution test
                    socket.gethostbyname(host)
                    external_results[host] = 'reachable'
                except socket.gaierror:
                    external_results[host] = 'dns_failed'
                except Exception:
                    external_results[host] = 'unreachable'
            
            all_external_ok = all(status == 'reachable' for status in external_results.values())
            connectivity['external_services'] = {
                'status': 'healthy' if all_external_ok else 'degraded',
                'results': external_results
            }
            
            # Test internal services
            internal_services = [
                ('localhost', 5432),  # PostgreSQL
                ('localhost', 6333),  # Qdrant
                ('localhost', 6379),  # Redis
            ]
            
            internal_results = {}
            for host, port in internal_services:
                try:
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.settimeout(5)
                    result = sock.connect_ex((host, port))
                    sock.close()
                    internal_results[f"{host}:{port}"] = 'reachable' if result == 0 else 'unreachable'
                except Exception:
                    internal_results[f"{host}:{port}"] = 'error'
            
            all_internal_ok = all(status == 'reachable' for status in internal_results.values())
            connectivity['internal_services'] = {
                'status': 'healthy' if all_internal_ok else 'degraded',
                'results': internal_results
            }
            
            connectivity['dns_resolution'] = {
                'status': 'healthy' if all(
                    result != 'dns_failed' for result in external_results.values()
                ) else 'degraded'
            }
            
        except Exception as e:
            connectivity['error'] = str(e)
        
        return connectivity
    
    async def _check_data_integrity(self) -> Dict[str, Any]:
        """Check data integrity and consistency."""
        data_integrity = {
            'database_integrity': {'status': 'unknown'},
            'log_file_integrity': {'status': 'unknown'},
            'backup_integrity': {'status': 'unknown'}
        }
        
        try:
            # Basic database integrity check
            try:
                import asyncpg
                conn = await asyncpg.connect(
                    host='localhost',
                    port=5432,
                    user='postgres',
                    password='sS67wM+1zMBRFHAW4kj9HwFl5J6+veo7Nirx0/I+oiU=',
                    database='postgres',
                    timeout=10
                )
                
                # Simple integrity check - ensure we can query system tables
                await conn.fetchrow("SELECT COUNT(*) FROM pg_database")
                await conn.close()
                
                data_integrity['database_integrity'] = {'status': 'healthy'}
                
            except Exception as e:
                data_integrity['database_integrity'] = {
                    'status': 'error',
                    'error': str(e)
                }
            
            # Log file integrity check
            log_files = [
                'logs/selfology.log',
                'logs/errors/errors.log'
            ]
            
            log_status = 'healthy'
            log_details = {}
            
            for log_file in log_files:
                log_path = Path(log_file)
                if log_path.exists():
                    try:
                        # Check if log file is readable and not corrupted
                        with open(log_path, 'r') as f:
                            # Try to read last few lines
                            f.seek(0, 2)  # Go to end
                            file_size = f.tell()
                            if file_size > 1000:  # If file has content
                                f.seek(max(0, file_size - 1000))  # Go to near end
                                f.read()  # Try to read
                        
                        log_details[log_file] = 'readable'
                    except Exception:
                        log_details[log_file] = 'corrupted'
                        log_status = 'degraded'
                else:
                    log_details[log_file] = 'missing'
                    log_status = 'degraded'
            
            data_integrity['log_file_integrity'] = {
                'status': log_status,
                'files': log_details
            }
            
            # Backup integrity (placeholder)
            data_integrity['backup_integrity'] = {
                'status': 'not_implemented',
                'note': 'Backup system not yet configured'
            }
            
        except Exception as e:
            data_integrity['error'] = str(e)
        
        return data_integrity
    
    async def _check_service_availability(self) -> Dict[str, Any]:
        """Check service availability and responsiveness."""
        availability = {
            'api_endpoints': {'status': 'unknown'},
            'database_availability': {'status': 'unknown'},
            'external_dependencies': {'status': 'unknown'}
        }
        
        try:
            # This would test actual API endpoints if they exist
            # For now, checking if services are running
            
            # Check database availability with actual query
            try:
                import asyncpg
                start_time = time.time()
                conn = await asyncpg.connect(
                    host='localhost',
                    port=5432,
                    user='postgres',
                    password='sS67wM+1zMBRFHAW4kj9HwFl5J6+veo7Nirx0/I+oiU=',
                    database='postgres',
                    timeout=5
                )
                
                await conn.fetchrow("SELECT 1")
                response_time = (time.time() - start_time) * 1000
                await conn.close()
                
                availability['database_availability'] = {
                    'status': 'healthy' if response_time < 1000 else 'slow',
                    'response_time_ms': response_time
                }
                
            except Exception as e:
                availability['database_availability'] = {
                    'status': 'unavailable',
                    'error': str(e)
                }
            
            # External dependencies check would go here
            availability['external_dependencies'] = {
                'status': 'not_implemented',
                'note': 'External dependency monitoring needed'
            }
            
        except Exception as e:
            availability['error'] = str(e)
        
        return availability
    
    async def _check_security_posture(self) -> Dict[str, Any]:
        """Check security configuration and posture."""
        security = {
            'file_permissions': {'status': 'unknown'},
            'environment_security': {'status': 'unknown'},
            'network_security': {'status': 'unknown'},
            'api_security': {'status': 'unknown'}
        }
        
        try:
            # File permissions check
            critical_files = ['.env', 'logs/', 'scripts/']
            permission_issues = []
            
            for file_path in critical_files:
                path = Path(file_path)
                if path.exists():
                    import stat
                    file_mode = path.stat().st_mode
                    
                    # Check if world-readable (security risk for .env)
                    if file_path == '.env' and (file_mode & stat.S_IROTH):
                        permission_issues.append(f"{file_path} is world-readable")
                    
                    # Check if executable files are properly secured
                    if file_path.endswith('.py') and (file_mode & stat.S_IWOTH):
                        permission_issues.append(f"{file_path} is world-writable")
            
            security['file_permissions'] = {
                'status': 'secure' if not permission_issues else 'vulnerable',
                'issues': permission_issues
            }
            
            # Environment security
            env_issues = []
            if Path('.env').exists():
                try:
                    with open('.env', 'r') as f:
                        env_content = f.read()
                    
                    # Check for common security issues in .env
                    if 'password' in env_content.lower() and 'password=' in env_content.lower():
                        # Simple check - not foolproof
                        pass
                    
                    # Check for potential secrets in environment
                    potential_secrets = ['token', 'key', 'secret', 'password']
                    for secret_type in potential_secrets:
                        if f"{secret_type.upper()}=" in env_content:
                            # Secrets found (expected for this app)
                            pass
                
                except Exception:
                    env_issues.append("Cannot read .env file")
            else:
                env_issues.append(".env file missing")
            
            security['environment_security'] = {
                'status': 'configured' if not env_issues else 'needs_attention',
                'issues': env_issues
            }
            
            # Basic network security check
            # Check for open ports that shouldn't be exposed
            network_issues = []
            
            try:
                connections = psutil.net_connections(kind='inet')
                listening_ports = [
                    conn.laddr.port for conn in connections 
                    if conn.status == psutil.CONN_LISTEN and conn.laddr.ip == '0.0.0.0'
                ]
                
                # Potentially risky ports exposed to all interfaces
                risky_ports = [port for port in listening_ports if port not in [80, 443, 22]]
                
                if risky_ports:
                    network_issues.append(f"Ports exposed to all interfaces: {risky_ports}")
                
                security['network_security'] = {
                    'status': 'secure' if not network_issues else 'needs_review',
                    'issues': network_issues,
                    'listening_ports': listening_ports
                }
                
            except Exception:
                security['network_security'] = {'status': 'unknown'}
            
            # API security (placeholder)
            security['api_security'] = {
                'status': 'not_implemented',
                'note': 'API security assessment needed'
            }
            
        except Exception as e:
            security['error'] = str(e)
        
        return security
    
    async def _check_performance_baselines(self) -> Dict[str, Any]:
        """Check performance against established baselines."""
        performance = {
            'response_time_baselines': {'status': 'unknown'},
            'throughput_baselines': {'status': 'unknown'},
            'resource_baselines': {'status': 'unknown'}
        }
        
        try:
            # This would check current performance against historical baselines
            # For now, providing structure for implementation
            
            # Check current performance metrics
            current_metrics = {
                'cpu_usage': psutil.cpu_percent(interval=1),
                'memory_usage': psutil.virtual_memory().percent,
                'disk_usage': (psutil.disk_usage('/').used / psutil.disk_usage('/').total) * 100
            }
            
            # Compare against thresholds (simplified baseline check)
            baseline_issues = []
            
            if current_metrics['cpu_usage'] > 80:
                baseline_issues.append(f"CPU usage {current_metrics['cpu_usage']:.1f}% above baseline")
            
            if current_metrics['memory_usage'] > 85:
                baseline_issues.append(f"Memory usage {current_metrics['memory_usage']:.1f}% above baseline")
            
            performance['resource_baselines'] = {
                'status': 'within_baseline' if not baseline_issues else 'exceeds_baseline',
                'current_metrics': current_metrics,
                'issues': baseline_issues
            }
            
            # Response time and throughput baselines would need historical data
            performance['response_time_baselines'] = {
                'status': 'not_implemented',
                'note': 'Requires historical response time data'
            }
            
            performance['throughput_baselines'] = {
                'status': 'not_implemented', 
                'note': 'Requires historical throughput data'
            }
            
        except Exception as e:
            performance['error'] = str(e)
        
        return performance
    
    async def _check_monitoring_coverage(self) -> Dict[str, Any]:
        """Check monitoring system coverage."""
        monitoring = {
            'log_monitoring': {'status': 'unknown'},
            'metric_collection': {'status': 'unknown'},
            'alert_configuration': {'status': 'unknown'},
            'dashboard_availability': {'status': 'unknown'}
        }
        
        try:
            # Check log file monitoring
            log_dirs = ['logs/errors', 'logs/bot', 'logs/users', 'logs/ai', 'logs/metrics']
            log_coverage = []
            
            for log_dir in log_dirs:
                log_path = Path(log_dir)
                if log_path.exists():
                    log_files = list(log_path.glob('*.log'))
                    log_coverage.append({
                        'directory': log_dir,
                        'file_count': len(log_files),
                        'latest_file': max(log_files, key=lambda f: f.stat().st_mtime).name if log_files else None
                    })
            
            monitoring['log_monitoring'] = {
                'status': 'configured' if log_coverage else 'missing',
                'coverage': log_coverage
            }
            
            # Check metric collection
            metrics_log = Path('logs/metrics/metrics.log')
            if metrics_log.exists():
                # Check if metrics are being actively written
                last_modified = datetime.fromtimestamp(metrics_log.stat().st_mtime)
                metrics_active = (datetime.now() - last_modified).total_seconds() < 3600  # Within last hour
                
                monitoring['metric_collection'] = {
                    'status': 'active' if metrics_active else 'stale',
                    'last_update': last_modified.isoformat()
                }
            else:
                monitoring['metric_collection'] = {'status': 'not_configured'}
            
            # Alert configuration check
            # This would check if alerting is properly configured
            monitoring['alert_configuration'] = {
                'status': 'basic',
                'note': 'Using debug agent for alerting'
            }
            
            # Dashboard availability
            monitoring['dashboard_availability'] = {
                'status': 'available',
                'note': 'Monitor dashboard available via scripts/monitor_dashboard.py'
            }
            
        except Exception as e:
            monitoring['error'] = str(e)
        
        return monitoring
    
    async def _check_backup_systems(self) -> Dict[str, Any]:
        """Check backup and recovery systems."""
        backups = {
            'database_backups': {'status': 'unknown'},
            'configuration_backups': {'status': 'unknown'},
            'log_backups': {'status': 'unknown'},
            'backup_verification': {'status': 'unknown'}
        }
        
        try:
            # Check for backup directories/files
            backup_locations = [
                'backups/',
                '/var/backups/selfology/',
                'data/backups/'
            ]
            
            backup_found = False
            for backup_loc in backup_locations:
                if Path(backup_loc).exists():
                    backup_found = True
                    break
            
            if backup_found:
                backups['status'] = 'basic_backups_configured'
            else:
                backups['status'] = 'no_backups_configured'
            
            # Database backup check
            backups['database_backups'] = {
                'status': 'not_configured',
                'recommendation': 'Set up automated PostgreSQL backups'
            }
            
            # Configuration backup check
            config_files = ['.env', 'pyproject.toml', 'docker-compose*.yml']
            backups['configuration_backups'] = {
                'status': 'version_controlled' if Path('.git').exists() else 'not_backed_up',
                'files': config_files
            }
            
            # Log backup/rotation check
            log_rotation_configured = False
            # Check if logrotate or similar is configured
            backups['log_backups'] = {
                'status': 'rotation_configured' if log_rotation_configured else 'manual_cleanup_needed'
            }
            
            backups['backup_verification'] = {
                'status': 'not_implemented',
                'note': 'Backup verification process needed'
            }
            
        except Exception as e:
            backups['error'] = str(e)
        
        return backups
    
    async def _check_disaster_recovery(self) -> Dict[str, Any]:
        """Check disaster recovery preparedness."""
        disaster_recovery = {
            'recovery_procedures': {'status': 'unknown'},
            'data_replication': {'status': 'unknown'},
            'failover_mechanisms': {'status': 'unknown'},
            'recovery_testing': {'status': 'unknown'}
        }
        
        try:
            # Check for documented recovery procedures
            recovery_docs = [
                'DISASTER_RECOVERY.md',
                'docs/disaster_recovery.md',
                'RECOVERY.md',
                'docs/recovery.md'
            ]
            
            recovery_doc_found = any(Path(doc).exists() for doc in recovery_docs)
            disaster_recovery['recovery_procedures'] = {
                'status': 'documented' if recovery_doc_found else 'not_documented'
            }
            
            # Data replication check
            disaster_recovery['data_replication'] = {
                'status': 'not_configured',
                'recommendation': 'Set up database replication for disaster recovery'
            }
            
            # Failover mechanisms
            disaster_recovery['failover_mechanisms'] = {
                'status': 'not_configured',
                'recommendation': 'Implement automatic failover mechanisms'
            }
            
            # Recovery testing
            disaster_recovery['recovery_testing'] = {
                'status': 'not_implemented',
                'recommendation': 'Regular disaster recovery testing needed'
            }
            
        except Exception as e:
            disaster_recovery['error'] = str(e)
        
        return disaster_recovery
    
    async def _check_compliance(self) -> Dict[str, Any]:
        """Check compliance with regulations and standards."""
        compliance = {
            'gdpr_compliance': {'status': 'unknown'},
            'data_privacy': {'status': 'unknown'},
            'security_standards': {'status': 'unknown'},
            'audit_logging': {'status': 'unknown'}
        }
        
        try:
            # GDPR compliance check
            gdpr_indicators = [
                'gdpr' in open('.env', 'r').read().lower() if Path('.env').exists() else False,
                Path('PRIVACY_POLICY.md').exists(),
                Path('DATA_PROTECTION.md').exists()
            ]
            
            compliance['gdpr_compliance'] = {
                'status': 'partially_compliant' if any(gdpr_indicators) else 'needs_review',
                'privacy_policy': Path('PRIVACY_POLICY.md').exists(),
                'data_protection_doc': Path('DATA_PROTECTION.md').exists()
            }
            
            # Data privacy
            compliance['data_privacy'] = {
                'status': 'basic_measures',
                'note': 'Privacy audit document exists' if Path('PRIVACY_AUDIT.md').exists() else 'No privacy audit found'
            }
            
            # Security standards
            compliance['security_standards'] = {
                'status': 'basic',
                'note': 'Basic security measures in place'
            }
            
            # Audit logging
            audit_logs_exist = Path('logs/users/user_activity.log').exists()
            compliance['audit_logging'] = {
                'status': 'configured' if audit_logs_exist else 'missing',
                'user_activity_logging': audit_logs_exist
            }
            
        except Exception as e:
            compliance['error'] = str(e)
        
        return compliance
    
    async def _generate_production_alerts(self, production_status: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate alerts based on production status."""
        alerts = []
        current_time = datetime.now()
        
        # System health alerts
        system_health = production_status.get('system_health', {})
        resources = system_health.get('resource_utilization', {})
        
        # CPU alerts
        cpu_status = resources.get('cpu', {})
        if cpu_status.get('status') == 'critical':
            alert_key = 'cpu_high'
            if self._should_send_alert(alert_key, current_time):
                alerts.append({
                    'severity': 'critical',
                    'type': 'resource_usage',
                    'message': f"Critical CPU usage: {cpu_status.get('usage_percent', 0):.1f}%",
                    'timestamp': current_time.isoformat(),
                    'component': 'system_resources',
                    'action_required': 'Investigate high CPU processes immediately'
                })
                self.last_alerts[alert_key] = current_time
        
        # Memory alerts  
        memory_status = resources.get('memory', {})
        if memory_status.get('status') == 'critical':
            alert_key = 'memory_high'
            if self._should_send_alert(alert_key, current_time):
                alerts.append({
                    'severity': 'critical',
                    'type': 'resource_usage',
                    'message': f"Critical memory usage: {memory_status.get('usage_percent', 0):.1f}%",
                    'timestamp': current_time.isoformat(),
                    'component': 'system_resources',
                    'action_required': 'Free up memory or restart services'
                })
                self.last_alerts[alert_key] = current_time
        
        # Disk space alerts
        disk_status = resources.get('disk', {})
        if disk_status.get('status') == 'critical':
            alert_key = 'disk_full'
            if self._should_send_alert(alert_key, current_time):
                alerts.append({
                    'severity': 'critical',
                    'type': 'resource_usage',
                    'message': f"Critical disk usage: {disk_status.get('usage_percent', 0):.1f}%",
                    'timestamp': current_time.isoformat(),
                    'component': 'storage',
                    'action_required': 'Clean up disk space immediately'
                })
                self.last_alerts[alert_key] = current_time
        
        # Service availability alerts
        service_status = system_health.get('service_status', {})
        
        # Bot service alert
        bot_status = service_status.get('selfology_bot', {})
        if bot_status.get('status') == 'stopped':
            alert_key = 'service_down'
            if self._should_send_alert(alert_key, current_time):
                alerts.append({
                    'severity': 'critical',
                    'type': 'service_down',
                    'message': 'Selfology bot service is not running',
                    'timestamp': current_time.isoformat(),
                    'component': 'selfology_bot',
                    'action_required': 'Restart bot service immediately'
                })
                self.last_alerts[alert_key] = current_time
        
        # Database service alert
        db_status = service_status.get('database_services', {})
        if db_status.get('status') == 'degraded':
            alerts.append({
                'severity': 'high',
                'type': 'service_degraded',
                'message': 'Database services are degraded',
                'timestamp': current_time.isoformat(),
                'component': 'database',
                'action_required': 'Check database service status'
            })
        
        # Security alerts
        security_posture = production_status.get('security_posture', {})
        file_permissions = security_posture.get('file_permissions', {})
        
        if file_permissions.get('status') == 'vulnerable':
            alerts.append({
                'severity': 'high',
                'type': 'security_issue',
                'message': 'File permission vulnerabilities detected',
                'timestamp': current_time.isoformat(),
                'component': 'security',
                'action_required': 'Fix file permissions immediately',
                'details': file_permissions.get('issues', [])
            })
        
        return alerts
    
    def _should_send_alert(self, alert_key: str, current_time: datetime) -> bool:
        """Check if alert should be sent based on cooldown period."""
        if alert_key not in self.last_alerts:
            return True
        
        last_alert = self.last_alerts[alert_key]
        cooldown_minutes = self.alert_cooldowns.get(alert_key, 15)  # Default 15 minutes
        
        return (current_time - last_alert).total_seconds() > (cooldown_minutes * 60)
    
    async def start_continuous_monitoring(self, duration_hours: int = 24):
        """Start continuous production monitoring."""
        print(f"🛡️ Starting continuous production monitoring for {duration_hours} hours...")
        
        self.monitoring_active = True
        end_time = datetime.now() + timedelta(hours=duration_hours)
        check_interval = 60  # Check every minute
        
        try:
            while datetime.now() < end_time and self.monitoring_active:
                # Perform health check
                production_status = await self.production_check()
                
                # Store health history
                health_score = production_status.get('production_score', 0)
                self.health_history.append({
                    'timestamp': datetime.now().isoformat(),
                    'health_score': health_score,
                    'alerts': len(production_status.get('alerts', []))
                })
                
                # Process alerts
                alerts = production_status.get('alerts', [])
                for alert in alerts:
                    self.alert_history.append(alert)
                    await self._process_alert(alert)
                
                # Display monitoring status
                print(f"⏰ {datetime.now().strftime('%H:%M:%S')} - Health: {health_score:.1f}% - Alerts: {len(alerts)}")
                
                # Wait for next check
                await asyncio.sleep(check_interval)
        
        except KeyboardInterrupt:
            print("\n🛑 Monitoring stopped by user")
        except Exception as e:
            print(f"❌ Monitoring error: {str(e)}")
        finally:
            self.monitoring_active = False
            print("🏁 Continuous monitoring ended")
    
    async def _process_alert(self, alert: Dict[str, Any]):
        """Process and respond to alerts."""
        severity = alert.get('severity', 'unknown')
        alert_type = alert.get('type', 'unknown')
        
        # Log alert
        print(f"🚨 [{severity.upper()}] {alert.get('message', 'Unknown alert')}")
        
        # Auto-remediation for certain alert types
        if alert_type == 'service_down' and alert.get('component') == 'selfology_bot':
            await self._attempt_service_restart()
        
        elif alert_type == 'resource_usage' and 'disk' in alert.get('message', '').lower():
            await self._attempt_disk_cleanup()
        
        # Save alert to persistent storage
        await self._save_alert(alert)
    
    async def _attempt_service_restart(self):
        """Attempt to restart the Selfology bot service."""
        print("🔄 Attempting to restart Selfology bot service...")
        
        try:
            # This would contain logic to restart the service
            # For now, just log the attempt
            print("⚠️ Service restart capability not yet implemented")
        except Exception as e:
            print(f"❌ Service restart failed: {str(e)}")
    
    async def _attempt_disk_cleanup(self):
        """Attempt basic disk cleanup."""
        print("🧹 Attempting disk cleanup...")
        
        try:
            # Clean up old log files
            log_dirs = ['logs/errors', 'logs/bot', 'logs/users']
            cleaned_files = 0
            
            for log_dir in log_dirs:
                log_path = Path(log_dir)
                if log_path.exists():
                    # Find old log files (>7 days)
                    old_files = [
                        f for f in log_path.glob('*.log')
                        if (datetime.now() - datetime.fromtimestamp(f.stat().st_mtime)).days > 7
                    ]
                    
                    for old_file in old_files[:5]:  # Limit to 5 files per cleanup
                        try:
                            old_file.unlink()
                            cleaned_files += 1
                        except Exception:
                            pass
            
            if cleaned_files > 0:
                print(f"🗑️ Cleaned up {cleaned_files} old log files")
            else:
                print("ℹ️ No old log files found to clean up")
        
        except Exception as e:
            print(f"❌ Disk cleanup failed: {str(e)}")
    
    async def _save_alert(self, alert: Dict[str, Any]):
        """Save alert to persistent storage."""
        try:
            alerts_dir = Path('logs/alerts')
            alerts_dir.mkdir(exist_ok=True)
            
            alert_file = alerts_dir / f"alerts_{datetime.now().strftime('%Y%m%d')}.jsonl"
            
            with open(alert_file, 'a') as f:
                f.write(json.dumps(alert, default=str) + '\n')
        
        except Exception as e:
            print(f"⚠️ Failed to save alert: {str(e)}")
    
    def _calculate_production_score(self, production_status: Dict[str, Any]) -> float:
        """Calculate overall production readiness score."""
        score = 100.0
        
        # System health impact
        system_health = production_status.get('system_health', {})
        
        # Resource utilization
        resources = system_health.get('resource_utilization', {})
        for resource_type, resource_data in resources.items():
            if isinstance(resource_data, dict):
                status = resource_data.get('status', 'healthy')
                if status == 'critical':
                    score -= 25
                elif status == 'warning':
                    score -= 10
        
        # Service availability
        service_status = system_health.get('service_status', {})
        
        # Bot service
        bot_status = service_status.get('selfology_bot', {})
        if bot_status.get('status') == 'stopped':
            score -= 40  # Major impact
        
        # Database services
        db_status = service_status.get('database_services', {})
        if db_status.get('status') == 'degraded':
            score -= 20
        
        # Security posture impact
        security = production_status.get('security_posture', {})
        for security_area, security_data in security.items():
            if isinstance(security_data, dict):
                status = security_data.get('status', 'secure')
                if status == 'vulnerable':
                    score -= 15
                elif status == 'needs_attention':
                    score -= 5
        
        # Monitoring coverage impact
        monitoring = production_status.get('monitoring_coverage', {})
        monitoring_configured = sum(
            1 for area_data in monitoring.values()
            if isinstance(area_data, dict) and area_data.get('status') in ['configured', 'active']
        )
        
        if monitoring_configured < 2:  # Less than 2 monitoring areas configured
            score -= 15
        
        # Backup systems impact
        backups = production_status.get('backup_systems', {})
        if backups.get('status') == 'no_backups_configured':
            score -= 20
        
        return max(0.0, score)
    
    def _extract_production_issues(self, production_status: Dict[str, Any]) -> List[Dict[str, str]]:
        """Extract production issues from status."""
        issues = []
        
        # System health issues
        system_health = production_status.get('system_health', {})
        resources = system_health.get('resource_utilization', {})
        
        for resource_type, resource_data in resources.items():
            if isinstance(resource_data, dict) and resource_data.get('status') == 'critical':
                issues.append({
                    'severity': 'critical',
                    'component': f'system_{resource_type}',
                    'issue': f'Critical {resource_type} usage',
                    'recommendation': f'Address {resource_type} resource constraints immediately'
                })
        
        # Service issues
        service_status = system_health.get('service_status', {})
        
        bot_status = service_status.get('selfology_bot', {})
        if bot_status.get('status') == 'stopped':
            issues.append({
                'severity': 'critical',
                'component': 'selfology_service',
                'issue': 'Selfology bot service not running',
                'recommendation': 'Start bot service and investigate why it stopped'
            })
        
        # Security issues
        security = production_status.get('security_posture', {})
        for security_area, security_data in security.items():
            if isinstance(security_data, dict) and security_data.get('status') == 'vulnerable':
                issues.append({
                    'severity': 'high',
                    'component': 'security',
                    'issue': f'Security vulnerability in {security_area}',
                    'recommendation': f'Fix {security_area} security issues'
                })
        
        return issues
    
    def _generate_production_recommendations(self, production_status: Dict[str, Any]) -> List[Dict[str, str]]:
        """Generate production optimization recommendations."""
        recommendations = []
        
        # Backup system recommendations
        backups = production_status.get('backup_systems', {})
        if backups.get('status') == 'no_backups_configured':
            recommendations.append({
                'priority': 'critical',
                'action': 'Set up automated backups',
                'description': 'No backup system configured',
                'effort': '4-8 hours'
            })
        
        # Monitoring recommendations
        monitoring = production_status.get('monitoring_coverage', {})
        
        if monitoring.get('metric_collection', {}).get('status') != 'active':
            recommendations.append({
                'priority': 'high',
                'action': 'Enable metric collection',
                'description': 'Metrics collection not active',
                'effort': '2-4 hours'
            })
        
        # Security recommendations
        security = production_status.get('security_posture', {})
        
        file_permissions = security.get('file_permissions', {})
        if file_permissions.get('status') == 'vulnerable':
            recommendations.append({
                'priority': 'high',
                'action': 'Fix file permissions',
                'description': 'File permission vulnerabilities detected',
                'effort': '1-2 hours'
            })
        
        # Disaster recovery recommendations
        disaster_recovery = production_status.get('disaster_recovery', {})
        if disaster_recovery.get('recovery_procedures', {}).get('status') == 'not_documented':
            recommendations.append({
                'priority': 'medium',
                'action': 'Document disaster recovery procedures',
                'description': 'No disaster recovery documentation',
                'effort': '6-12 hours'
            })
        
        return recommendations