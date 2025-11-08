"""
🔧 System Diagnostics Component
Comprehensive health checking and system analysis for Selfology infrastructure.
"""

import asyncio
import json
import psutil
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional
import aiohttp
import asyncpg
from qdrant_client import QdrantClient


class SystemDiagnostics:
    """
    Comprehensive system diagnostics for all Selfology infrastructure components.
    """
    
    def __init__(self):
        self.start_time = datetime.now()
        self.diagnostics_log = []
    
    async def full_health_check(self, deep: bool = False) -> Dict[str, Any]:
        """
        Complete system health check covering all infrastructure.
        
        Args:
            deep: Enable deep system analysis (slower but comprehensive)
        
        Returns:
            Comprehensive health report
        """
        print("  🔍 Running system health diagnostics...")
        
        health_report = {
            'timestamp': datetime.now().isoformat(),
            'system_info': await self._get_system_info(),
            'infrastructure': await self._check_infrastructure(),
            'databases': await self._check_databases(),
            'external_services': await self._check_external_services(),
            'file_system': await self._check_file_system(),
            'environment': await self._check_environment(),
            'processes': await self._check_processes(),
            'network': await self._check_network(),
            'issues': [],
            'recommendations': [],
            'health_score': 0.0
        }
        
        if deep:
            health_report['deep_analysis'] = await self._run_deep_analysis()
        
        # Analyze results and generate score
        health_report['health_score'] = self._calculate_health_score(health_report)
        health_report['issues'] = self._extract_issues(health_report)
        health_report['recommendations'] = self._generate_system_recommendations(health_report)
        
        return health_report
    
    async def _get_system_info(self) -> Dict[str, Any]:
        """Get basic system information."""
        return {
            'cpu_count': psutil.cpu_count(),
            'cpu_percent': psutil.cpu_percent(interval=1),
            'memory': {
                'total': psutil.virtual_memory().total,
                'available': psutil.virtual_memory().available,
                'percent': psutil.virtual_memory().percent
            },
            'disk': {
                'total': psutil.disk_usage('/').total,
                'free': psutil.disk_usage('/').free,
                'percent': psutil.disk_usage('/').percent
            },
            'uptime': (datetime.now() - datetime.fromtimestamp(psutil.boot_time())).total_seconds()
        }
    
    async def _check_infrastructure(self) -> Dict[str, Any]:
        """Check Docker infrastructure and n8n-enterprise services."""
        infrastructure = {
            'docker': {'status': 'unknown', 'containers': []},
            'n8n_services': {},
            'network': {'status': 'unknown', 'name': 'n8n-enterprise_n8n-network'}
        }
        
        try:
            # Check Docker status
            result = subprocess.run(['docker', 'ps', '--format', 'json'], 
                                  capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                infrastructure['docker']['status'] = 'running'
                containers = []
                for line in result.stdout.strip().split('\n'):
                    if line:
                        container = json.loads(line)
                        containers.append({
                            'name': container.get('Names', 'unknown'),
                            'image': container.get('Image', 'unknown'),
                            'status': container.get('State', 'unknown'),
                            'ports': container.get('Ports', '')
                        })
                infrastructure['docker']['containers'] = containers
                
                # Check specific n8n services
                expected_services = [
                    'n8n-postgres', 'n8n-redis', 'qdrant', 'chromadb', 'ollama', 'n8n-main'
                ]
                
                for service in expected_services:
                    service_container = next((c for c in containers if service in c['name']), None)
                    infrastructure['n8n_services'][service] = {
                        'running': service_container is not None,
                        'details': service_container
                    }
            
        except Exception as e:
            infrastructure['docker']['error'] = str(e)
        
        return infrastructure
    
    async def _check_databases(self) -> Dict[str, Any]:
        """Check database connections and health."""
        databases = {
            'postgresql': {'status': 'unknown', 'connection': None},
            'qdrant': {'status': 'unknown', 'connection': None},
            'redis': {'status': 'unknown', 'connection': None}
        }
        
        # Check PostgreSQL
        try:
            conn = await asyncpg.connect(
                host='localhost',
                port=5432,
                user='postgres',
                password='sS67wM+1zMBRFHAW4kj9HwFl5J6+veo7Nirx0/I+oiU=',
                database='postgres',
                timeout=5
            )
            
            # Check if selfology database exists
            result = await conn.fetchrow("SELECT 1 FROM pg_database WHERE datname = 'selfology'")
            selfology_exists = result is not None
            
            # Get database stats
            stats = await conn.fetchrow("""
                SELECT 
                    pg_database_size('postgres') as db_size,
                    (SELECT count(*) FROM pg_stat_activity) as connections
            """)
            
            await conn.close()
            
            databases['postgresql'] = {
                'status': 'connected',
                'selfology_db_exists': selfology_exists,
                'database_size': stats['db_size'],
                'active_connections': stats['connections']
            }
            
        except Exception as e:
            databases['postgresql'] = {'status': 'error', 'error': str(e)}
        
        # Check Qdrant
        try:
            client = QdrantClient(host='localhost', port=6333, timeout=5)
            collections = client.get_collections()
            
            databases['qdrant'] = {
                'status': 'connected',
                'collections': [c.name for c in collections.collections]
            }
            
        except Exception as e:
            databases['qdrant'] = {'status': 'error', 'error': str(e)}
        
        return databases
    
    async def _check_external_services(self) -> Dict[str, Any]:
        """Check external API connections."""
        services = {
            'telegram_api': {'status': 'unknown'},
            'anthropic_api': {'status': 'unknown'},
            'openai_api': {'status': 'unknown'},
            'n8n_webhook': {'status': 'unknown'}
        }
        
        # Check Telegram API
        try:
            from selfology_bot.core.config import get_config
            config = get_config()
            
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=5)) as session:
                # Test Telegram Bot API
                if hasattr(config, 'TELEGRAM_BOT_TOKEN'):
                    url = f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}/getMe"
                    async with session.get(url) as resp:
                        if resp.status == 200:
                            services['telegram_api']['status'] = 'connected'
                        else:
                            services['telegram_api']['status'] = 'error'
                            services['telegram_api']['error'] = f"HTTP {resp.status}"
                
                # Test n8n webhook if available
                if hasattr(config, 'N8N_BASE_URL'):
                    url = f"{config.N8N_BASE_URL}/webhook-test/health"
                    try:
                        async with session.get(url) as resp:
                            services['n8n_webhook']['status'] = 'connected' if resp.status == 200 else 'error'
                    except:
                        services['n8n_webhook']['status'] = 'unreachable'
        
        except Exception as e:
            services['api_check_error'] = str(e)
        
        return services
    
    async def _check_file_system(self) -> Dict[str, Any]:
        """Check file system health and important directories."""
        fs_check = {
            'directories': {},
            'log_files': {},
            'permissions': {},
            'disk_usage': {}
        }
        
        # Check important directories
        important_dirs = [
            'logs', 'logs/errors', 'logs/bot', 'logs/users', 'logs/ai', 'logs/metrics',
            'selfology_bot', 'scripts', 'intelligent_question_core', 'venv'
        ]
        
        for dir_path in important_dirs:
            path = Path(dir_path)
            fs_check['directories'][dir_path] = {
                'exists': path.exists(),
                'is_dir': path.is_dir() if path.exists() else False,
                'readable': path.exists() and os.access(path, os.R_OK),
                'writable': path.exists() and os.access(path, os.W_OK)
            }
        
        # Check log files
        log_files = [
            'logs/selfology.log', 'logs/errors/errors.log', 'logs/bot/bot_activity.log'
        ]
        
        for log_file in log_files:
            path = Path(log_file)
            if path.exists():
                fs_check['log_files'][log_file] = {
                    'size': path.stat().st_size,
                    'modified': datetime.fromtimestamp(path.stat().st_mtime).isoformat(),
                    'readable': os.access(path, os.R_OK)
                }
        
        return fs_check
    
    async def _check_environment(self) -> Dict[str, Any]:
        """Check environment configuration."""
        env_check = {
            'python_version': None,
            'virtual_env': None,
            'required_packages': {},
            'environment_vars': {}
        }
        
        # Python version
        import sys
        env_check['python_version'] = sys.version
        env_check['virtual_env'] = sys.prefix != sys.base_prefix
        
        # Check required packages
        required_packages = [
            'fastapi', 'aiogram', 'anthropic', 'openai', 'qdrant-client', 
            'asyncpg', 'sqlalchemy', 'alembic', 'structlog'
        ]
        
        for package in required_packages:
            try:
                __import__(package)
                env_check['required_packages'][package] = 'installed'
            except ImportError:
                env_check['required_packages'][package] = 'missing'
        
        # Check critical environment variables
        critical_env_vars = [
            'TELEGRAM_BOT_TOKEN', 'ANTHROPIC_API_KEY', 'OPENAI_API_KEY'
        ]
        
        import os
        for var in critical_env_vars:
            env_check['environment_vars'][var] = {
                'set': var in os.environ,
                'length': len(os.environ.get(var, '')) if var in os.environ else 0
            }
        
        return env_check
    
    async def _check_processes(self) -> Dict[str, Any]:
        """Check running processes related to Selfology."""
        processes = {
            'selfology_processes': [],
            'python_processes': [],
            'docker_processes': []
        }
        
        for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'cpu_percent', 'memory_percent']):
            try:
                cmdline = ' '.join(proc.info['cmdline'] or [])
                
                if 'selfology' in cmdline.lower() or 'monitored_bot.py' in cmdline:
                    processes['selfology_processes'].append({
                        'pid': proc.info['pid'],
                        'name': proc.info['name'],
                        'cmdline': cmdline,
                        'cpu_percent': proc.info['cpu_percent'],
                        'memory_percent': proc.info['memory_percent']
                    })
                
                if proc.info['name'] == 'python' or proc.info['name'] == 'python3':
                    processes['python_processes'].append({
                        'pid': proc.info['pid'],
                        'cmdline': cmdline[:100] + '...' if len(cmdline) > 100 else cmdline
                    })
                
                if proc.info['name'] == 'docker' or 'docker' in cmdline:
                    processes['docker_processes'].append({
                        'pid': proc.info['pid'],
                        'cmdline': cmdline[:100] + '...' if len(cmdline) > 100 else cmdline
                    })
                    
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        
        return processes
    
    async def _check_network(self) -> Dict[str, Any]:
        """Check network connectivity and ports."""
        network = {
            'listening_ports': [],
            'connections': [],
            'connectivity': {}
        }
        
        # Check listening ports
        for conn in psutil.net_connections(kind='inet'):
            if conn.status == psutil.CONN_LISTEN:
                network['listening_ports'].append({
                    'port': conn.laddr.port,
                    'address': conn.laddr.ip,
                    'pid': conn.pid
                })
        
        # Test key connectivity
        test_hosts = [
            ('api.telegram.org', 443),
            ('api.anthropic.com', 443),
            ('api.openai.com', 443),
            ('localhost', 5432),  # PostgreSQL
            ('localhost', 6333),  # Qdrant
        ]
        
        for host, port in test_hosts:
            try:
                import socket
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(5)
                result = sock.connect_ex((host, port))
                sock.close()
                
                network['connectivity'][f"{host}:{port}"] = 'reachable' if result == 0 else 'unreachable'
            except Exception as e:
                network['connectivity'][f"{host}:{port}"] = f'error: {str(e)}'
        
        return network
    
    async def _run_deep_analysis(self) -> Dict[str, Any]:
        """Run deep system analysis (slower but comprehensive)."""
        deep_analysis = {
            'performance_history': await self._analyze_performance_history(),
            'log_analysis': await self._analyze_recent_logs(),
            'dependency_check': await self._check_dependencies(),
            'security_check': await self._basic_security_check()
        }
        
        return deep_analysis
    
    async def _analyze_performance_history(self) -> Dict[str, Any]:
        """Analyze system performance over time."""
        # This would analyze metrics logs for trends
        return {'status': 'not_implemented', 'note': 'Performance history analysis pending'}
    
    async def _analyze_recent_logs(self) -> Dict[str, Any]:
        """Analyze recent logs for patterns and issues."""
        log_analysis = {
            'error_patterns': [],
            'warning_patterns': [],
            'performance_issues': []
        }
        
        try:
            error_log_path = Path('logs/errors/errors.log')
            if error_log_path.exists():
                with open(error_log_path, 'r') as f:
                    lines = f.readlines()[-100:]  # Last 100 lines
                
                # Simple pattern detection
                error_count = len([l for l in lines if 'ERROR' in l])
                warning_count = len([l for l in lines if 'WARNING' in l])
                
                log_analysis['recent_errors'] = error_count
                log_analysis['recent_warnings'] = warning_count
        
        except Exception as e:
            log_analysis['error'] = str(e)
        
        return log_analysis
    
    async def _check_dependencies(self) -> Dict[str, Any]:
        """Check Python package dependencies and versions."""
        dependencies = {
            'outdated_packages': [],
            'security_vulnerabilities': [],
            'compatibility_issues': []
        }
        
        try:
            # Check for outdated packages
            result = subprocess.run(['pip', 'list', '--outdated', '--format=json'], 
                                  capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                outdated = json.loads(result.stdout)
                dependencies['outdated_packages'] = outdated
        
        except Exception as e:
            dependencies['check_error'] = str(e)
        
        return dependencies
    
    async def _basic_security_check(self) -> Dict[str, Any]:
        """Basic security checks."""
        security = {
            'file_permissions': {},
            'env_file_security': {},
            'exposed_secrets': []
        }
        
        # Check .env file permissions
        env_file = Path('.env')
        if env_file.exists():
            import stat
            file_mode = oct(env_file.stat().st_mode)
            security['env_file_security'] = {
                'exists': True,
                'permissions': file_mode,
                'world_readable': bool(env_file.stat().st_mode & stat.S_IROTH)
            }
        
        return security
    
    def _calculate_health_score(self, health_report: Dict[str, Any]) -> float:
        """Calculate overall system health score (0-100)."""
        score = 100.0
        
        # Infrastructure checks
        if health_report['infrastructure']['docker']['status'] != 'running':
            score -= 20
        
        # Database checks
        for db_name, db_info in health_report['databases'].items():
            if db_info['status'] != 'connected':
                score -= 15
        
        # System resource checks
        system_info = health_report['system_info']
        if system_info['memory']['percent'] > 90:
            score -= 10
        if system_info['disk']['percent'] > 90:
            score -= 10
        if system_info['cpu_percent'] > 90:
            score -= 10
        
        # External service checks
        for service, info in health_report['external_services'].items():
            if info['status'] != 'connected' and service != 'n8n_webhook':
                score -= 5
        
        return max(0.0, score)
    
    def _extract_issues(self, health_report: Dict[str, Any]) -> List[Dict[str, str]]:
        """Extract issues from health report."""
        issues = []
        
        # System resource issues
        system_info = health_report['system_info']
        if system_info['memory']['percent'] > 85:
            issues.append({
                'severity': 'high' if system_info['memory']['percent'] > 95 else 'medium',
                'component': 'system',
                'issue': f"High memory usage: {system_info['memory']['percent']:.1f}%",
                'recommendation': 'Consider restarting services or investigating memory leaks'
            })
        
        if system_info['disk']['percent'] > 85:
            issues.append({
                'severity': 'high' if system_info['disk']['percent'] > 95 else 'medium',
                'component': 'system',
                'issue': f"Low disk space: {system_info['disk']['percent']:.1f}% used",
                'recommendation': 'Clean up logs or expand disk space'
            })
        
        # Infrastructure issues
        if health_report['infrastructure']['docker']['status'] != 'running':
            issues.append({
                'severity': 'critical',
                'component': 'infrastructure',
                'issue': 'Docker is not running',
                'recommendation': 'Start Docker service'
            })
        
        # Database issues
        for db_name, db_info in health_report['databases'].items():
            if db_info['status'] != 'connected':
                issues.append({
                    'severity': 'critical',
                    'component': 'database',
                    'issue': f"{db_name} database not accessible",
                    'recommendation': f'Check {db_name} service status and configuration'
                })
        
        return issues
    
    def _generate_system_recommendations(self, health_report: Dict[str, Any]) -> List[Dict[str, str]]:
        """Generate system-level recommendations."""
        recommendations = []
        
        # Performance recommendations
        system_info = health_report['system_info']
        if system_info['cpu_percent'] > 70:
            recommendations.append({
                'priority': 'medium',
                'action': 'Optimize CPU usage',
                'description': f'CPU usage at {system_info["cpu_percent"]:.1f}%',
                'effort': '2-4 hours'
            })
        
        if system_info['memory']['percent'] > 80:
            recommendations.append({
                'priority': 'high',
                'action': 'Investigate memory usage',
                'description': f'Memory usage at {system_info["memory"]["percent"]:.1f}%',
                'effort': '1-2 hours'
            })
        
        # Missing services
        n8n_services = health_report['infrastructure']['n8n_services']
        for service, info in n8n_services.items():
            if not info['running']:
                recommendations.append({
                    'priority': 'high',
                    'action': f'Start {service} service',
                    'description': f'Required service {service} is not running',
                    'effort': '15 minutes'
                })
        
        return recommendations
    
    async def debug_general_issue(self, issue_type: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Debug general system issues."""
        debug_result = {
            'issue_type': issue_type,
            'timestamp': datetime.now().isoformat(),
            'analysis': {},
            'recommendations': []
        }
        
        if issue_type == 'high_cpu':
            # Analyze high CPU usage
            processes = []
            for proc in psutil.process_iter(['pid', 'name', 'cpu_percent']):
                try:
                    processes.append({
                        'pid': proc.info['pid'],
                        'name': proc.info['name'],
                        'cpu_percent': proc.info['cpu_percent']
                    })
                except:
                    continue
            
            # Sort by CPU usage
            processes.sort(key=lambda x: x['cpu_percent'], reverse=True)
            
            debug_result['analysis'] = {
                'top_cpu_processes': processes[:10],
                'total_processes': len(processes),
                'system_cpu': psutil.cpu_percent(interval=1)
            }
            
            debug_result['recommendations'] = [
                {
                    'action': 'Identify resource-intensive processes',
                    'description': 'Review top CPU consuming processes and optimize',
                    'priority': 'high'
                }
            ]
        
        elif issue_type == 'disk_space':
            # Analyze disk usage
            disk_usage = {}
            for root, dirs, files in os.walk('.'):
                total_size = sum(os.path.getsize(os.path.join(root, file)) for file in files)
                disk_usage[root] = total_size
            
            # Sort by size
            sorted_usage = sorted(disk_usage.items(), key=lambda x: x[1], reverse=True)
            
            debug_result['analysis'] = {
                'largest_directories': sorted_usage[:20],
                'disk_stats': psutil.disk_usage('/')._asdict()
            }
            
            debug_result['recommendations'] = [
                {
                    'action': 'Clean up large directories',
                    'description': 'Remove unnecessary files from largest directories',
                    'priority': 'medium'
                }
            ]
        
        return debug_result


import os