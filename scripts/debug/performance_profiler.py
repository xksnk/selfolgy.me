"""
⚡ Performance Profiler Component
Advanced performance analysis and optimization recommendations for Selfology systems.
"""

import asyncio
import psutil
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional
from collections import defaultdict
import json
import statistics


class PerformanceProfiler:
    """
    Comprehensive performance profiler for Selfology AI Psychology Coach.
    Analyzes system performance, identifies bottlenecks, and provides optimization recommendations.
    """
    
    def __init__(self):
        self.profiling_start = datetime.now()
        self.metrics_history = []
        self.performance_baselines = {
            'response_time_ms': 2000,    # 2 seconds max
            'memory_usage_mb': 512,      # 512 MB baseline
            'cpu_usage_percent': 70,     # 70% CPU max
            'disk_io_mbps': 50,         # 50 MB/s disk I/O
            'network_latency_ms': 100    # 100ms network latency
        }
    
    async def profile_system(self) -> Dict[str, Any]:
        """
        Comprehensive system performance profiling and analysis.
        """
        print("    🔍 Profiling system performance...")
        
        performance_profile = {
            'timestamp': datetime.now().isoformat(),
            'system_resources': await self._profile_system_resources(),
            'application_performance': await self._profile_application_performance(),
            'database_performance': await self._profile_database_performance(),
            'ai_performance': await self._profile_ai_performance(),
            'network_performance': await self._profile_network_performance(),
            'memory_analysis': await self._profile_memory_usage(),
            'process_analysis': await self._profile_process_performance(),
            'bottleneck_analysis': await self._identify_bottlenecks(),
            'optimization_recommendations': [],
            'performance_score': 0.0,
            'issues': []
        }
        
        # Calculate overall performance score
        performance_profile['performance_score'] = self._calculate_performance_score(performance_profile)
        performance_profile['issues'] = self._extract_performance_issues(performance_profile)
        performance_profile['optimization_recommendations'] = self._generate_optimization_recommendations(performance_profile)
        
        return performance_profile
    
    async def _profile_system_resources(self) -> Dict[str, Any]:
        """Profile system resource utilization."""
        system_resources = {
            'cpu': await self._profile_cpu_usage(),
            'memory': await self._profile_memory_resources(),
            'disk': await self._profile_disk_resources(),
            'network': await self._profile_network_resources()
        }
        
        return system_resources
    
    async def _profile_cpu_usage(self) -> Dict[str, Any]:
        """Profile CPU usage patterns."""
        cpu_profile = {
            'current_usage': 0.0,
            'usage_over_time': [],
            'per_core_usage': [],
            'load_average': [],
            'context_switches': 0,
            'interrupts': 0
        }
        
        try:
            # Current CPU usage
            cpu_profile['current_usage'] = psutil.cpu_percent(interval=1)
            
            # Per-core usage
            cpu_profile['per_core_usage'] = psutil.cpu_percent(interval=1, percpu=True)
            
            # Load average (Unix systems)
            try:
                cpu_profile['load_average'] = list(psutil.getloadavg())
            except AttributeError:
                cpu_profile['load_average'] = [0, 0, 0]  # Windows doesn't have load average
            
            # CPU statistics
            cpu_stats = psutil.cpu_stats()
            cpu_profile['context_switches'] = cpu_stats.ctx_switches
            cpu_profile['interrupts'] = cpu_stats.interrupts
            
            # Collect CPU usage over short period
            usage_samples = []
            for _ in range(5):
                usage_samples.append(psutil.cpu_percent(interval=0.5))
            
            cpu_profile['usage_over_time'] = usage_samples
            cpu_profile['average_usage'] = statistics.mean(usage_samples)
            cpu_profile['peak_usage'] = max(usage_samples)
            
        except Exception as e:
            cpu_profile['error'] = str(e)
        
        return cpu_profile
    
    async def _profile_memory_resources(self) -> Dict[str, Any]:
        """Profile memory resource utilization."""
        memory_profile = {
            'virtual_memory': {},
            'swap_memory': {},
            'memory_pressure': 'unknown'
        }
        
        try:
            # Virtual memory
            vmem = psutil.virtual_memory()
            memory_profile['virtual_memory'] = {
                'total_gb': vmem.total / (1024**3),
                'available_gb': vmem.available / (1024**3),
                'used_gb': vmem.used / (1024**3),
                'percentage': vmem.percent,
                'free_gb': vmem.free / (1024**3),
                'cached_gb': getattr(vmem, 'cached', 0) / (1024**3),
                'buffers_gb': getattr(vmem, 'buffers', 0) / (1024**3)
            }
            
            # Swap memory
            swap = psutil.swap_memory()
            memory_profile['swap_memory'] = {
                'total_gb': swap.total / (1024**3),
                'used_gb': swap.used / (1024**3),
                'free_gb': swap.free / (1024**3),
                'percentage': swap.percent,
                'swap_in_mb': getattr(swap, 'sin', 0) / (1024**2),
                'swap_out_mb': getattr(swap, 'sout', 0) / (1024**2)
            }
            
            # Memory pressure analysis
            if vmem.percent > 90:
                memory_profile['memory_pressure'] = 'critical'
            elif vmem.percent > 80:
                memory_profile['memory_pressure'] = 'high'
            elif vmem.percent > 70:
                memory_profile['memory_pressure'] = 'moderate'
            else:
                memory_profile['memory_pressure'] = 'low'
        
        except Exception as e:
            memory_profile['error'] = str(e)
        
        return memory_profile
    
    async def _profile_disk_resources(self) -> Dict[str, Any]:
        """Profile disk I/O and storage utilization."""
        disk_profile = {
            'disk_usage': {},
            'disk_io': {},
            'io_performance': {}
        }
        
        try:
            # Disk usage for root partition
            disk_usage = psutil.disk_usage('/')
            disk_profile['disk_usage'] = {
                'total_gb': disk_usage.total / (1024**3),
                'used_gb': disk_usage.used / (1024**3),
                'free_gb': disk_usage.free / (1024**3),
                'percentage': (disk_usage.used / disk_usage.total) * 100
            }
            
            # Disk I/O statistics
            disk_io_before = psutil.disk_io_counters()
            if disk_io_before:
                # Wait a moment and measure again
                await asyncio.sleep(1)
                disk_io_after = psutil.disk_io_counters()
                
                read_bytes_per_sec = disk_io_after.read_bytes - disk_io_before.read_bytes
                write_bytes_per_sec = disk_io_after.write_bytes - disk_io_before.write_bytes
                
                disk_profile['disk_io'] = {
                    'read_mb_per_sec': read_bytes_per_sec / (1024**2),
                    'write_mb_per_sec': write_bytes_per_sec / (1024**2),
                    'read_count_per_sec': disk_io_after.read_count - disk_io_before.read_count,
                    'write_count_per_sec': disk_io_after.write_count - disk_io_before.write_count,
                    'total_read_gb': disk_io_after.read_bytes / (1024**3),
                    'total_write_gb': disk_io_after.write_bytes / (1024**3)
                }
                
                # I/O performance assessment
                total_io_mbps = (read_bytes_per_sec + write_bytes_per_sec) / (1024**2)
                if total_io_mbps > 100:
                    io_performance = 'high'
                elif total_io_mbps > 50:
                    io_performance = 'moderate'
                else:
                    io_performance = 'low'
                
                disk_profile['io_performance'] = {
                    'assessment': io_performance,
                    'total_io_mbps': total_io_mbps
                }
        
        except Exception as e:
            disk_profile['error'] = str(e)
        
        return disk_profile
    
    async def _profile_network_resources(self) -> Dict[str, Any]:
        """Profile network I/O and connectivity."""
        network_profile = {
            'network_io': {},
            'connections': {},
            'latency_tests': {}
        }
        
        try:
            # Network I/O statistics
            net_io_before = psutil.net_io_counters()
            if net_io_before:
                await asyncio.sleep(1)
                net_io_after = psutil.net_io_counters()
                
                bytes_sent_per_sec = net_io_after.bytes_sent - net_io_before.bytes_sent
                bytes_recv_per_sec = net_io_after.bytes_recv - net_io_before.bytes_recv
                
                network_profile['network_io'] = {
                    'bytes_sent_per_sec': bytes_sent_per_sec,
                    'bytes_recv_per_sec': bytes_recv_per_sec,
                    'packets_sent_per_sec': net_io_after.packets_sent - net_io_before.packets_sent,
                    'packets_recv_per_sec': net_io_after.packets_recv - net_io_before.packets_recv,
                    'total_sent_gb': net_io_after.bytes_sent / (1024**3),
                    'total_recv_gb': net_io_after.bytes_recv / (1024**3)
                }
            
            # Active connections
            connections = psutil.net_connections(kind='inet')
            connection_stats = defaultdict(int)
            
            for conn in connections:
                connection_stats[conn.status] += 1
            
            network_profile['connections'] = {
                'total_connections': len(connections),
                'by_status': dict(connection_stats),
                'listening_ports': len([c for c in connections if c.status == 'LISTEN'])
            }
            
        except Exception as e:
            network_profile['error'] = str(e)
        
        return network_profile
    
    async def _profile_application_performance(self) -> Dict[str, Any]:
        """Profile application-specific performance metrics."""
        app_performance = {
            'response_times': await self._analyze_response_times(),
            'throughput': await self._analyze_throughput(),
            'error_rates': await self._analyze_error_rates(),
            'resource_efficiency': await self._analyze_resource_efficiency()
        }
        
        return app_performance
    
    async def _analyze_response_times(self) -> Dict[str, Any]:
        """Analyze application response times."""
        response_analysis = {
            'api_response_times': {},
            'database_query_times': {},
            'ai_processing_times': {},
            'overall_performance': 'unknown'
        }
        
        try:
            # Parse metrics logs for response time data
            metrics_log_path = Path('logs/metrics/metrics.log')
            if metrics_log_path.exists():
                response_times = await self._parse_response_time_metrics(hours=24)
                
                # Categorize response times
                api_times = [r['value'] for r in response_times if 'api' in r.get('metric_name', '')]
                db_times = [r['value'] for r in response_times if 'db' in r.get('metric_name', '') or 'database' in r.get('metric_name', '')]
                ai_times = [r['value'] for r in response_times if 'ai' in r.get('metric_name', '') or 'model' in r.get('metric_name', '')]
                
                if api_times:
                    response_analysis['api_response_times'] = {
                        'average_ms': statistics.mean(api_times),
                        'median_ms': statistics.median(api_times),
                        'p95_ms': sorted(api_times)[int(len(api_times) * 0.95)] if api_times else 0,
                        'p99_ms': sorted(api_times)[int(len(api_times) * 0.99)] if api_times else 0,
                        'max_ms': max(api_times),
                        'count': len(api_times)
                    }
                
                if db_times:
                    response_analysis['database_query_times'] = {
                        'average_ms': statistics.mean(db_times),
                        'median_ms': statistics.median(db_times),
                        'p95_ms': sorted(db_times)[int(len(db_times) * 0.95)] if db_times else 0,
                        'max_ms': max(db_times),
                        'count': len(db_times)
                    }
                
                if ai_times:
                    response_analysis['ai_processing_times'] = {
                        'average_ms': statistics.mean(ai_times),
                        'median_ms': statistics.median(ai_times),
                        'p95_ms': sorted(ai_times)[int(len(ai_times) * 0.95)] if ai_times else 0,
                        'max_ms': max(ai_times),
                        'count': len(ai_times)
                    }
                
                # Overall performance assessment
                all_times = api_times + db_times + ai_times
                if all_times:
                    avg_response = statistics.mean(all_times)
                    if avg_response < 1000:  # < 1 second
                        response_analysis['overall_performance'] = 'excellent'
                    elif avg_response < 3000:  # < 3 seconds
                        response_analysis['overall_performance'] = 'good'
                    elif avg_response < 5000:  # < 5 seconds
                        response_analysis['overall_performance'] = 'acceptable'
                    else:
                        response_analysis['overall_performance'] = 'poor'
        
        except Exception as e:
            response_analysis['error'] = str(e)
        
        return response_analysis
    
    async def _analyze_throughput(self) -> Dict[str, Any]:
        """Analyze system throughput metrics."""
        throughput_analysis = {
            'requests_per_second': 0,
            'messages_per_hour': 0,
            'database_operations_per_minute': 0,
            'ai_requests_per_hour': 0
        }
        
        try:
            # Parse metrics for throughput data
            metrics_data = await self._parse_throughput_metrics(hours=1)  # Last hour
            
            # Calculate throughput metrics
            total_requests = len([m for m in metrics_data if 'request' in m.get('metric_name', '')])
            total_messages = len([m for m in metrics_data if 'message' in m.get('metric_name', '')])
            total_db_ops = len([m for m in metrics_data if 'db' in m.get('metric_name', '') or 'database' in m.get('metric_name', '')])
            total_ai_requests = len([m for m in metrics_data if 'ai' in m.get('metric_name', '')])
            
            throughput_analysis['requests_per_second'] = total_requests / 3600  # Rough calculation
            throughput_analysis['messages_per_hour'] = total_messages
            throughput_analysis['database_operations_per_minute'] = total_db_ops / 60
            throughput_analysis['ai_requests_per_hour'] = total_ai_requests
        
        except Exception as e:
            throughput_analysis['error'] = str(e)
        
        return throughput_analysis
    
    async def _analyze_error_rates(self) -> Dict[str, Any]:
        """Analyze system error rates."""
        error_analysis = {
            'overall_error_rate': 0.0,
            'error_rate_by_component': {},
            'error_trends': {}
        }
        
        try:
            # Parse error logs
            error_log_path = Path('logs/errors/errors.log')
            if error_log_path.exists():
                with open(error_log_path, 'r') as f:
                    recent_errors = f.readlines()[-100:]  # Last 100 errors
                
                # Categorize errors by component
                error_counts = defaultdict(int)
                for error in recent_errors:
                    if 'BOT_' in error:
                        error_counts['bot'] += 1
                    elif 'USER_' in error:
                        error_counts['user'] += 1
                    elif 'AI_' in error:
                        error_counts['ai'] += 1
                    elif 'DB_' in error:
                        error_counts['database'] += 1
                    else:
                        error_counts['other'] += 1
                
                total_errors = sum(error_counts.values())
                error_analysis['overall_error_rate'] = total_errors  # Simplified - would need total operations for actual rate
                error_analysis['error_rate_by_component'] = dict(error_counts)
        
        except Exception as e:
            error_analysis['error'] = str(e)
        
        return error_analysis
    
    async def _analyze_resource_efficiency(self) -> Dict[str, Any]:
        """Analyze resource usage efficiency."""
        efficiency_analysis = {
            'cpu_efficiency': 'unknown',
            'memory_efficiency': 'unknown',
            'io_efficiency': 'unknown',
            'overall_efficiency': 'unknown'
        }
        
        try:
            # Get system resource usage
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            
            # Assess CPU efficiency
            if cpu_percent < 30:
                efficiency_analysis['cpu_efficiency'] = 'underutilized'
            elif cpu_percent < 70:
                efficiency_analysis['cpu_efficiency'] = 'optimal'
            elif cpu_percent < 90:
                efficiency_analysis['cpu_efficiency'] = 'high_load'
            else:
                efficiency_analysis['cpu_efficiency'] = 'overloaded'
            
            # Assess memory efficiency
            if memory.percent < 50:
                efficiency_analysis['memory_efficiency'] = 'underutilized'
            elif memory.percent < 80:
                efficiency_analysis['memory_efficiency'] = 'optimal'
            elif memory.percent < 95:
                efficiency_analysis['memory_efficiency'] = 'high_usage'
            else:
                efficiency_analysis['memory_efficiency'] = 'critical'
            
            # Overall efficiency assessment
            efficiency_scores = {
                'underutilized': 60,
                'optimal': 100,
                'high_load': 70,
                'high_usage': 70,
                'overloaded': 40,
                'critical': 20
            }
            
            cpu_score = efficiency_scores.get(efficiency_analysis['cpu_efficiency'], 50)
            memory_score = efficiency_scores.get(efficiency_analysis['memory_efficiency'], 50)
            
            overall_score = (cpu_score + memory_score) / 2
            if overall_score > 90:
                efficiency_analysis['overall_efficiency'] = 'excellent'
            elif overall_score > 75:
                efficiency_analysis['overall_efficiency'] = 'good'
            elif overall_score > 60:
                efficiency_analysis['overall_efficiency'] = 'acceptable'
            else:
                efficiency_analysis['overall_efficiency'] = 'poor'
        
        except Exception as e:
            efficiency_analysis['error'] = str(e)
        
        return efficiency_analysis
    
    async def _profile_database_performance(self) -> Dict[str, Any]:
        """Profile database performance metrics."""
        db_performance = {
            'postgresql_performance': await self._profile_postgresql_performance(),
            'qdrant_performance': await self._profile_qdrant_performance(),
            'redis_performance': await self._profile_redis_performance()
        }
        
        return db_performance
    
    async def _profile_postgresql_performance(self) -> Dict[str, Any]:
        """Profile PostgreSQL database performance."""
        postgres_perf = {
            'connection_performance': {'status': 'unknown'},
            'query_performance': {'status': 'unknown'},
            'connection_pool': {'status': 'unknown'}
        }
        
        try:
            import asyncpg
            
            # Test connection performance
            start_time = time.time()
            conn = await asyncpg.connect(
                host='localhost',
                port=5432,
                user='postgres',
                password='sS67wM+1zMBRFHAW4kj9HwFl5J6+veo7Nirx0/I+oiU=',
                database='postgres',
                timeout=10
            )
            connection_time_ms = (time.time() - start_time) * 1000
            
            postgres_perf['connection_performance'] = {
                'status': 'success',
                'connection_time_ms': connection_time_ms,
                'performance': 'good' if connection_time_ms < 100 else 'slow'
            }
            
            # Test simple query performance
            start_time = time.time()
            await conn.fetchrow("SELECT NOW()")
            query_time_ms = (time.time() - start_time) * 1000
            
            postgres_perf['query_performance'] = {
                'status': 'success',
                'simple_query_time_ms': query_time_ms,
                'performance': 'good' if query_time_ms < 10 else 'slow'
            }
            
            await conn.close()
        
        except Exception as e:
            postgres_perf['connection_performance'] = {
                'status': 'error',
                'error': str(e)
            }
        
        return postgres_perf
    
    async def _profile_qdrant_performance(self) -> Dict[str, Any]:
        """Profile Qdrant vector database performance."""
        qdrant_perf = {
            'connection_performance': {'status': 'unknown'},
            'search_performance': {'status': 'unknown'}
        }
        
        try:
            from qdrant_client import QdrantClient
            
            # Test connection performance
            start_time = time.time()
            client = QdrantClient(host='localhost', port=6333, timeout=10)
            collections = client.get_collections()
            connection_time_ms = (time.time() - start_time) * 1000
            
            qdrant_perf['connection_performance'] = {
                'status': 'success',
                'connection_time_ms': connection_time_ms,
                'collections_count': len(collections.collections)
            }
            
            # Test search performance if collections exist
            if collections.collections:
                collection_name = collections.collections[0].name
                test_vector = [0.1] * 384  # Standard embedding size
                
                start_time = time.time()
                results = client.search(
                    collection_name=collection_name,
                    query_vector=test_vector,
                    limit=5
                )
                search_time_ms = (time.time() - start_time) * 1000
                
                qdrant_perf['search_performance'] = {
                    'status': 'success',
                    'search_time_ms': search_time_ms,
                    'results_count': len(results),
                    'performance': 'good' if search_time_ms < 100 else 'slow'
                }
        
        except Exception as e:
            qdrant_perf['connection_performance'] = {
                'status': 'error',
                'error': str(e)
            }
        
        return qdrant_perf
    
    async def _profile_redis_performance(self) -> Dict[str, Any]:
        """Profile Redis performance."""
        redis_perf = {
            'connection_performance': {'status': 'unknown'},
            'operation_performance': {'status': 'unknown'}
        }
        
        try:
            import redis.asyncio as redis
            
            # Test connection and operation performance
            start_time = time.time()
            r = redis.Redis(host='localhost', port=6379, decode_responses=True)
            await r.ping()
            connection_time_ms = (time.time() - start_time) * 1000
            
            redis_perf['connection_performance'] = {
                'status': 'success',
                'connection_time_ms': connection_time_ms
            }
            
            # Test basic operations performance
            start_time = time.time()
            await r.set('perf_test_key', 'test_value', ex=60)
            await r.get('perf_test_key')
            await r.delete('perf_test_key')
            operation_time_ms = (time.time() - start_time) * 1000
            
            redis_perf['operation_performance'] = {
                'status': 'success',
                'operation_time_ms': operation_time_ms,
                'performance': 'good' if operation_time_ms < 10 else 'slow'
            }
            
            await r.close()
        
        except Exception as e:
            redis_perf['connection_performance'] = {
                'status': 'error',
                'error': str(e)
            }
        
        return redis_perf
    
    async def _profile_ai_performance(self) -> Dict[str, Any]:
        """Profile AI service performance."""
        ai_performance = {
            'model_response_times': {},
            'routing_performance': {},
            'cost_efficiency': {}
        }
        
        # This would integrate with AI system analyzer
        ai_performance['status'] = 'delegated_to_ai_analyzer'
        
        return ai_performance
    
    async def _profile_network_performance(self) -> Dict[str, Any]:
        """Profile network performance and latency."""
        network_perf = {
            'external_latency': await self._test_external_latency(),
            'internal_latency': await self._test_internal_latency(),
            'bandwidth_utilization': await self._test_bandwidth_utilization()
        }
        
        return network_perf
    
    async def _test_external_latency(self) -> Dict[str, Any]:
        """Test latency to external services."""
        latency_tests = {
            'telegram_api': {'latency_ms': 0, 'status': 'unknown'},
            'anthropic_api': {'latency_ms': 0, 'status': 'unknown'},
            'openai_api': {'latency_ms': 0, 'status': 'unknown'}
        }
        
        import aiohttp
        
        test_endpoints = [
            ('telegram_api', 'https://api.telegram.org'),
            ('anthropic_api', 'https://api.anthropic.com'),
            ('openai_api', 'https://api.openai.com')
        ]
        
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
            for service_name, endpoint in test_endpoints:
                try:
                    start_time = time.time()
                    async with session.head(endpoint) as resp:
                        latency_ms = (time.time() - start_time) * 1000
                        latency_tests[service_name] = {
                            'latency_ms': latency_ms,
                            'status': 'success',
                            'http_status': resp.status
                        }
                except Exception as e:
                    latency_tests[service_name] = {
                        'latency_ms': 0,
                        'status': 'error',
                        'error': str(e)
                    }
        
        return latency_tests
    
    async def _test_internal_latency(self) -> Dict[str, Any]:
        """Test latency to internal services."""
        internal_latency = {
            'localhost_postgresql': {'latency_ms': 0, 'status': 'unknown'},
            'localhost_qdrant': {'latency_ms': 0, 'status': 'unknown'},
            'localhost_redis': {'latency_ms': 0, 'status': 'unknown'}
        }
        
        # Test database connections for latency
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
            await conn.close()
            latency_ms = (time.time() - start_time) * 1000
            
            internal_latency['localhost_postgresql'] = {
                'latency_ms': latency_ms,
                'status': 'success'
            }
        except Exception as e:
            internal_latency['localhost_postgresql'] = {
                'status': 'error',
                'error': str(e)
            }
        
        return internal_latency
    
    async def _test_bandwidth_utilization(self) -> Dict[str, Any]:
        """Test network bandwidth utilization."""
        bandwidth = {
            'current_utilization': 'unknown',
            'peak_utilization': 'unknown'
        }
        
        # This would require more sophisticated network monitoring
        bandwidth['status'] = 'not_implemented'
        
        return bandwidth
    
    async def _profile_memory_usage(self) -> Dict[str, Any]:
        """Detailed memory usage profiling."""
        memory_profile = {
            'process_memory': await self._profile_process_memory(),
            'memory_leaks': await self._detect_memory_leaks(),
            'garbage_collection': await self._analyze_garbage_collection()
        }
        
        return memory_profile
    
    async def _profile_process_memory(self) -> Dict[str, Any]:
        """Profile memory usage by process."""
        process_memory = {
            'selfology_processes': [],
            'python_processes': [],
            'system_memory_distribution': {}
        }
        
        try:
            for proc in psutil.process_iter(['pid', 'name', 'memory_info', 'cmdline']):
                try:
                    cmdline = ' '.join(proc.info['cmdline'] or [])
                    memory_mb = proc.info['memory_info'].rss / (1024 * 1024)
                    
                    if 'selfology' in cmdline.lower() or 'monitored_bot' in cmdline:
                        process_memory['selfology_processes'].append({
                            'pid': proc.info['pid'],
                            'name': proc.info['name'],
                            'memory_mb': memory_mb,
                            'cmdline': cmdline[:100] + '...' if len(cmdline) > 100 else cmdline
                        })
                    
                    if proc.info['name'] in ['python', 'python3']:
                        process_memory['python_processes'].append({
                            'pid': proc.info['pid'],
                            'memory_mb': memory_mb,
                            'cmdline': cmdline[:100] + '...' if len(cmdline) > 100 else cmdline
                        })
                
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
        
        except Exception as e:
            process_memory['error'] = str(e)
        
        return process_memory
    
    async def _detect_memory_leaks(self) -> Dict[str, Any]:
        """Detect potential memory leaks."""
        leak_detection = {
            'status': 'not_implemented',
            'note': 'Memory leak detection requires long-term monitoring'
        }
        
        return leak_detection
    
    async def _analyze_garbage_collection(self) -> Dict[str, Any]:
        """Analyze Python garbage collection performance."""
        gc_analysis = {
            'status': 'not_implemented',
            'note': 'GC analysis requires Python-specific profiling'
        }
        
        return gc_analysis
    
    async def _profile_process_performance(self) -> Dict[str, Any]:
        """Profile individual process performance."""
        process_perf = {
            'high_cpu_processes': [],
            'high_memory_processes': [],
            'io_intensive_processes': []
        }
        
        try:
            for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent', 'cmdline']):
                try:
                    # Get CPU percent over short interval
                    cpu_percent = proc.cpu_percent(interval=0.1)
                    memory_percent = proc.memory_percent()
                    
                    if cpu_percent > 50:
                        process_perf['high_cpu_processes'].append({
                            'pid': proc.info['pid'],
                            'name': proc.info['name'],
                            'cpu_percent': cpu_percent,
                            'cmdline': ' '.join(proc.info['cmdline'] or [])[:100]
                        })
                    
                    if memory_percent > 5:  # >5% of total system memory
                        process_perf['high_memory_processes'].append({
                            'pid': proc.info['pid'],
                            'name': proc.info['name'],
                            'memory_percent': memory_percent,
                            'cmdline': ' '.join(proc.info['cmdline'] or [])[:100]
                        })
                
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
        
        except Exception as e:
            process_perf['error'] = str(e)
        
        return process_perf
    
    async def _identify_bottlenecks(self) -> Dict[str, Any]:
        """Identify system performance bottlenecks."""
        bottlenecks = {
            'cpu_bottlenecks': [],
            'memory_bottlenecks': [],
            'io_bottlenecks': [],
            'network_bottlenecks': []
        }
        
        try:
            # CPU bottlenecks
            cpu_percent = psutil.cpu_percent(interval=1)
            if cpu_percent > 80:
                bottlenecks['cpu_bottlenecks'].append({
                    'type': 'high_cpu_usage',
                    'value': cpu_percent,
                    'threshold': 80,
                    'severity': 'high' if cpu_percent > 90 else 'medium'
                })
            
            # Memory bottlenecks
            memory = psutil.virtual_memory()
            if memory.percent > 85:
                bottlenecks['memory_bottlenecks'].append({
                    'type': 'high_memory_usage',
                    'value': memory.percent,
                    'threshold': 85,
                    'severity': 'critical' if memory.percent > 95 else 'high'
                })
            
            # Disk I/O bottlenecks
            disk_usage = psutil.disk_usage('/')
            if disk_usage.percent > 90:
                bottlenecks['io_bottlenecks'].append({
                    'type': 'low_disk_space',
                    'value': disk_usage.percent,
                    'threshold': 90,
                    'severity': 'critical' if disk_usage.percent > 95 else 'high'
                })
        
        except Exception as e:
            bottlenecks['error'] = str(e)
        
        return bottlenecks
    
    async def _parse_response_time_metrics(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Parse response time metrics from logs."""
        metrics = []
        
        metrics_path = Path('logs/metrics/metrics.log')
        if not metrics_path.exists():
            return metrics
        
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        try:
            with open(metrics_path, 'r') as f:
                for line in f:
                    try:
                        log_entry = json.loads(line.strip())
                        
                        # Check if it's a response time metric
                        metric_name = log_entry.get('metric_name', '')
                        if 'response_time' in metric_name or 'processing_time' in metric_name:
                            # Parse timestamp
                            timestamp_str = log_entry.get('timestamp', '')
                            if timestamp_str:
                                log_time = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                                if log_time.replace(tzinfo=None) > cutoff_time:
                                    metrics.append(log_entry)
                    
                    except (json.JSONDecodeError, ValueError):
                        continue
        
        except Exception:
            pass
        
        return metrics
    
    async def _parse_throughput_metrics(self, hours: int = 1) -> List[Dict[str, Any]]:
        """Parse throughput metrics from logs."""
        metrics = []
        
        # This would parse various log files for throughput data
        # Implementation would depend on specific log formats
        
        return metrics
    
    def _calculate_performance_score(self, performance_profile: Dict[str, Any]) -> float:
        """Calculate overall performance score."""
        score = 100.0
        
        # System resources impact
        system_resources = performance_profile.get('system_resources', {})
        
        # CPU performance
        cpu_profile = system_resources.get('cpu', {})
        avg_cpu = cpu_profile.get('average_usage', 0)
        if avg_cpu > 80:
            score -= min((avg_cpu - 80) * 2, 30)  # Max 30 point deduction
        
        # Memory performance
        memory_profile = system_resources.get('memory', {})
        memory_pressure = memory_profile.get('memory_pressure', 'low')
        if memory_pressure == 'critical':
            score -= 30
        elif memory_pressure == 'high':
            score -= 20
        elif memory_pressure == 'moderate':
            score -= 10
        
        # Application performance impact
        app_performance = performance_profile.get('application_performance', {})
        
        # Response times
        response_times = app_performance.get('response_times', {})
        overall_performance = response_times.get('overall_performance', 'unknown')
        if overall_performance == 'poor':
            score -= 25
        elif overall_performance == 'acceptable':
            score -= 15
        elif overall_performance == 'good':
            score -= 5
        
        # Error rates
        error_rates = app_performance.get('error_rates', {})
        overall_error_rate = error_rates.get('overall_error_rate', 0)
        if overall_error_rate > 50:  # More than 50 errors
            score -= min(overall_error_rate - 50, 20)
        
        # Bottlenecks impact
        bottlenecks = performance_profile.get('bottleneck_analysis', {})
        total_bottlenecks = sum(len(bottlenecks.get(bt, [])) for bt in ['cpu_bottlenecks', 'memory_bottlenecks', 'io_bottlenecks'])
        score -= min(total_bottlenecks * 5, 25)  # 5 points per bottleneck, max 25
        
        return max(0.0, score)
    
    def _extract_performance_issues(self, performance_profile: Dict[str, Any]) -> List[Dict[str, str]]:
        """Extract performance issues from profile."""
        issues = []
        
        # System resource issues
        system_resources = performance_profile.get('system_resources', {})
        
        # High CPU usage
        cpu_profile = system_resources.get('cpu', {})
        avg_cpu = cpu_profile.get('average_usage', 0)
        if avg_cpu > 80:
            issues.append({
                'severity': 'high' if avg_cpu > 90 else 'medium',
                'component': 'cpu',
                'issue': f'High CPU usage: {avg_cpu:.1f}%',
                'recommendation': 'Investigate CPU-intensive processes'
            })
        
        # Memory pressure
        memory_profile = system_resources.get('memory', {})
        memory_pressure = memory_profile.get('memory_pressure', 'low')
        if memory_pressure in ['critical', 'high']:
            issues.append({
                'severity': 'critical' if memory_pressure == 'critical' else 'high',
                'component': 'memory',
                'issue': f'{memory_pressure} memory pressure',
                'recommendation': 'Free up memory or investigate memory leaks'
            })
        
        # Application performance issues
        app_performance = performance_profile.get('application_performance', {})
        
        # Slow response times
        response_times = app_performance.get('response_times', {})
        overall_performance = response_times.get('overall_performance', 'unknown')
        if overall_performance in ['poor', 'acceptable']:
            issues.append({
                'severity': 'high' if overall_performance == 'poor' else 'medium',
                'component': 'response_time',
                'issue': f'{overall_performance} response time performance',
                'recommendation': 'Optimize slow endpoints and queries'
            })
        
        # Database performance issues
        db_performance = performance_profile.get('database_performance', {})
        
        for db_name, db_perf in db_performance.items():
            if isinstance(db_perf, dict):
                # Check connection performance
                conn_perf = db_perf.get('connection_performance', {})
                if conn_perf.get('performance') == 'slow':
                    issues.append({
                        'severity': 'medium',
                        'component': f'database_{db_name}',
                        'issue': f'Slow {db_name} connections',
                        'recommendation': f'Optimize {db_name} connection configuration'
                    })
        
        # Bottleneck issues
        bottlenecks = performance_profile.get('bottleneck_analysis', {})
        
        for bottleneck_type, bottleneck_list in bottlenecks.items():
            if isinstance(bottleneck_list, list):
                for bottleneck in bottleneck_list:
                    if isinstance(bottleneck, dict):
                        issues.append({
                            'severity': bottleneck.get('severity', 'medium'),
                            'component': 'bottleneck',
                            'issue': f"{bottleneck_type}: {bottleneck.get('type', 'unknown')}",
                            'recommendation': f"Address {bottleneck.get('type', 'bottleneck')}"
                        })
        
        return issues
    
    def _generate_optimization_recommendations(self, performance_profile: Dict[str, Any]) -> List[Dict[str, str]]:
        """Generate performance optimization recommendations."""
        recommendations = []
        
        # System resource optimizations
        system_resources = performance_profile.get('system_resources', {})
        
        # CPU optimization
        cpu_profile = system_resources.get('cpu', {})
        avg_cpu = cpu_profile.get('average_usage', 0)
        if avg_cpu > 70:
            recommendations.append({
                'priority': 'high' if avg_cpu > 85 else 'medium',
                'action': 'Optimize CPU usage',
                'description': f'CPU usage at {avg_cpu:.1f}%, identify and optimize high-CPU processes',
                'effort': '4-8 hours'
            })
        
        # Memory optimization
        memory_profile = system_resources.get('memory', {})
        memory_pressure = memory_profile.get('memory_pressure', 'low')
        if memory_pressure in ['critical', 'high', 'moderate']:
            recommendations.append({
                'priority': 'critical' if memory_pressure == 'critical' else 'high',
                'action': 'Optimize memory usage',
                'description': f'{memory_pressure} memory pressure detected',
                'effort': '3-6 hours'
            })
        
        # Application performance optimizations
        app_performance = performance_profile.get('application_performance', {})
        
        # Response time optimization
        response_times = app_performance.get('response_times', {})
        api_times = response_times.get('api_response_times', {})
        if api_times.get('average_ms', 0) > 2000:  # >2 seconds
            recommendations.append({
                'priority': 'high',
                'action': 'Optimize API response times',
                'description': f"Average API response time {api_times['average_ms']:.0f}ms",
                'effort': '6-12 hours'
            })
        
        # Database optimization
        db_performance = performance_profile.get('database_performance', {})
        
        postgres_perf = db_performance.get('postgresql_performance', {})
        query_perf = postgres_perf.get('query_performance', {})
        if query_perf.get('performance') == 'slow':
            recommendations.append({
                'priority': 'medium',
                'action': 'Optimize database queries',
                'description': 'Slow PostgreSQL query performance detected',
                'effort': '4-8 hours'
            })
        
        # AI performance optimization
        ai_response_times = response_times.get('ai_processing_times', {})
        if ai_response_times.get('average_ms', 0) > 5000:  # >5 seconds
            recommendations.append({
                'priority': 'high',
                'action': 'Optimize AI processing pipeline',
                'description': f"AI processing time {ai_response_times['average_ms']:.0f}ms",
                'effort': '8-16 hours'
            })
        
        # Network optimization
        network_perf = performance_profile.get('network_performance', {})
        external_latency = network_perf.get('external_latency', {})
        
        high_latency_services = [
            service for service, data in external_latency.items()
            if isinstance(data, dict) and data.get('latency_ms', 0) > 500
        ]
        
        if high_latency_services:
            recommendations.append({
                'priority': 'medium',
                'action': 'Optimize network connectivity',
                'description': f'High latency to: {", ".join(high_latency_services)}',
                'effort': '2-4 hours'
            })
        
        # Resource efficiency optimization
        resource_efficiency = app_performance.get('resource_efficiency', {})
        if resource_efficiency.get('overall_efficiency') == 'poor':
            recommendations.append({
                'priority': 'medium',
                'action': 'Improve resource efficiency',
                'description': 'Overall resource utilization is inefficient',
                'effort': '6-12 hours'
            })
        
        return recommendations
    
    async def debug_specific_issue(self, issue_type: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Debug specific performance issues."""
        debug_result = {
            'issue_type': issue_type,
            'timestamp': datetime.now().isoformat(),
            'analysis': {},
            'recommendations': []
        }
        
        if issue_type == 'performance_slow_response':
            # Analyze slow response times
            response_analysis = await self._analyze_response_times()
            debug_result['analysis'] = response_analysis
            
            # Get component-specific analysis
            component = context.get('component', 'api')
            if component in response_analysis:
                component_data = response_analysis[component]
                avg_time = component_data.get('average_ms', 0)
                
                debug_result['recommendations'] = [
                    {
                        'action': f'Optimize {component} response time',
                        'description': f'Average response time {avg_time:.0f}ms is too high',
                        'priority': 'high' if avg_time > 5000 else 'medium'
                    }
                ]
        
        elif issue_type == 'performance_high_cpu':
            # Analyze high CPU usage
            process_analysis = await self._profile_process_performance()
            debug_result['analysis'] = process_analysis
            
            high_cpu_processes = process_analysis.get('high_cpu_processes', [])
            if high_cpu_processes:
                debug_result['recommendations'] = [
                    {
                        'action': 'Optimize high CPU processes',
                        'description': f'{len(high_cpu_processes)} processes using high CPU',
                        'priority': 'high'
                    }
                ]
        
        elif issue_type == 'performance_memory_leak':
            # Analyze memory usage patterns
            memory_analysis = await self._profile_memory_usage()
            debug_result['analysis'] = memory_analysis
            
            debug_result['recommendations'] = [
                {
                    'action': 'Investigate memory usage patterns',
                    'description': 'Potential memory leak detected',
                    'priority': 'high'
                }
            ]
        
        elif issue_type == 'performance_database_slow':
            # Analyze database performance
            db_analysis = await self._profile_database_performance()
            debug_result['analysis'] = db_analysis
            
            slow_dbs = []
            for db_name, db_data in db_analysis.items():
                if isinstance(db_data, dict):
                    query_perf = db_data.get('query_performance', {})
                    if query_perf.get('performance') == 'slow':
                        slow_dbs.append(db_name)
            
            if slow_dbs:
                debug_result['recommendations'] = [
                    {
                        'action': f'Optimize {", ".join(slow_dbs)} performance',
                        'description': 'Slow database performance detected',
                        'priority': 'high'
                    }
                ]
        
        return debug_result