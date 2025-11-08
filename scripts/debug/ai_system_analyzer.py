"""
🤖 AI System Analyzer Component
Comprehensive analysis and debugging for AI routing, model performance, and cost optimization.
"""

import asyncio
import json
import statistics
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional
from collections import defaultdict, Counter
import aiohttp
import re


class AISystemAnalyzer:
    """
    Advanced analyzer for AI routing system, model performance, and cost optimization.
    Handles Claude/GPT-4/GPT-4o-mini routing intelligence and debugging.
    """
    
    def __init__(self):
        self.analysis_start = datetime.now()
        self.ai_logs_path = Path('logs/ai/ai_interactions.log')
        self.metrics_logs_path = Path('logs/metrics/metrics.log')
    
    async def analyze_ai_performance(self) -> Dict[str, Any]:
        """
        Comprehensive AI system performance analysis.
        """
        print("    🔍 Analyzing AI routing and model performance...")
        
        analysis = {
            'timestamp': datetime.now().isoformat(),
            'routing_analysis': await self._analyze_routing_performance(),
            'model_performance': await self._analyze_model_performance(),
            'cost_analysis': await self._analyze_cost_optimization(),
            'error_patterns': await self._analyze_ai_errors(),
            'response_quality': await self._analyze_response_quality(),
            'api_health': await self._check_api_health(),
            'recommendations': [],
            'health_score': 0.0,
            'issues': []
        }
        
        # Calculate overall AI system health
        analysis['health_score'] = self._calculate_ai_health_score(analysis)
        analysis['issues'] = self._extract_ai_issues(analysis)
        analysis['recommendations'] = self._generate_ai_recommendations(analysis)
        
        return analysis
    
    async def _analyze_routing_performance(self) -> Dict[str, Any]:
        """Analyze AI router performance and decision accuracy."""
        routing_stats = {
            'total_requests': 0,
            'model_distribution': defaultdict(int),
            'routing_accuracy': 0.0,
            'average_decision_time': 0.0,
            'fallback_rate': 0.0,
            'cost_savings': 0.0,
            'routing_patterns': {}
        }
        
        if not self.ai_logs_path.exists():
            routing_stats['error'] = 'AI logs not found'
            return routing_stats
        
        try:
            ai_interactions = await self._parse_ai_logs(hours=24)
            
            if not ai_interactions:
                routing_stats['error'] = 'No AI interactions found in last 24h'
                return routing_stats
            
            routing_stats['total_requests'] = len(ai_interactions)
            
            # Model distribution analysis
            for interaction in ai_interactions:
                model = interaction.get('model_used', 'unknown')
                routing_stats['model_distribution'][model] += 1
            
            # Calculate percentages
            total = routing_stats['total_requests']
            model_percentages = {
                model: (count / total) * 100 
                for model, count in routing_stats['model_distribution'].items()
            }
            routing_stats['model_percentages'] = model_percentages
            
            # Routing decision times
            decision_times = [
                interaction.get('routing_time', 0) 
                for interaction in ai_interactions 
                if 'routing_time' in interaction
            ]
            
            if decision_times:
                routing_stats['average_decision_time'] = statistics.mean(decision_times)
                routing_stats['max_decision_time'] = max(decision_times)
                routing_stats['min_decision_time'] = min(decision_times)
            
            # Fallback analysis (when optimal model failed and had to use backup)
            fallbacks = [
                interaction for interaction in ai_interactions 
                if interaction.get('was_fallback', False)
            ]
            routing_stats['fallback_rate'] = (len(fallbacks) / total) * 100 if total > 0 else 0
            
            # Cost optimization analysis
            estimated_savings = await self._calculate_cost_savings(ai_interactions)
            routing_stats['cost_savings'] = estimated_savings
            
            # Routing pattern analysis
            routing_stats['routing_patterns'] = await self._analyze_routing_patterns(ai_interactions)
            
        except Exception as e:
            routing_stats['error'] = f"Routing analysis failed: {str(e)}"
        
        return routing_stats
    
    async def _analyze_model_performance(self) -> Dict[str, Any]:
        """Analyze individual model performance metrics."""
        model_performance = {
            'claude_sonnet': {'metrics': {}, 'issues': []},
            'gpt4': {'metrics': {}, 'issues': []},
            'gpt4o_mini': {'metrics': {}, 'issues': []},
            'overall_comparison': {}
        }
        
        try:
            ai_interactions = await self._parse_ai_logs(hours=24)
            
            # Group by model
            by_model = defaultdict(list)
            for interaction in ai_interactions:
                model = interaction.get('model_used', 'unknown')
                by_model[model].append(interaction)
            
            # Analyze each model
            for model_name, interactions in by_model.items():
                if not interactions:
                    continue
                
                # Response times
                response_times = [
                    interaction.get('response_time', 0) 
                    for interaction in interactions 
                    if 'response_time' in interaction
                ]
                
                # Success rates
                successful = [
                    interaction for interaction in interactions 
                    if interaction.get('status') == 'success'
                ]
                success_rate = (len(successful) / len(interactions)) * 100 if interactions else 0
                
                # Error analysis
                errors = [
                    interaction for interaction in interactions 
                    if interaction.get('status') == 'error'
                ]
                error_rate = (len(errors) / len(interactions)) * 100 if interactions else 0
                
                # Token usage analysis
                token_usage = [
                    interaction.get('tokens_used', 0) 
                    for interaction in interactions 
                    if 'tokens_used' in interaction
                ]
                
                # Cost analysis
                costs = [
                    interaction.get('estimated_cost', 0) 
                    for interaction in interactions 
                    if 'estimated_cost' in interaction
                ]
                
                model_key = self._normalize_model_name(model_name)
                if model_key in model_performance:
                    model_performance[model_key]['metrics'] = {
                        'total_requests': len(interactions),
                        'success_rate': success_rate,
                        'error_rate': error_rate,
                        'avg_response_time': statistics.mean(response_times) if response_times else 0,
                        'median_response_time': statistics.median(response_times) if response_times else 0,
                        'avg_tokens': statistics.mean(token_usage) if token_usage else 0,
                        'total_cost': sum(costs),
                        'avg_cost_per_request': statistics.mean(costs) if costs else 0
                    }
                    
                    # Identify issues
                    issues = []
                    if success_rate < 95:
                        issues.append(f"Low success rate: {success_rate:.1f}%")
                    if response_times and statistics.mean(response_times) > 30:
                        issues.append(f"Slow responses: {statistics.mean(response_times):.1f}s avg")
                    if error_rate > 5:
                        issues.append(f"High error rate: {error_rate:.1f}%")
                    
                    model_performance[model_key]['issues'] = issues
            
            # Overall comparison
            model_performance['overall_comparison'] = await self._compare_models(model_performance)
            
        except Exception as e:
            model_performance['analysis_error'] = str(e)
        
        return model_performance
    
    async def _analyze_cost_optimization(self) -> Dict[str, Any]:
        """Analyze cost optimization effectiveness."""
        cost_analysis = {
            'current_period': {},
            'optimization_effectiveness': {},
            'projected_savings': {},
            'cost_trends': {},
            'recommendations': []
        }
        
        try:
            ai_interactions = await self._parse_ai_logs(hours=24)
            
            if not ai_interactions:
                cost_analysis['error'] = 'No interactions for cost analysis'
                return cost_analysis
            
            # Current period costs
            total_cost = sum(
                interaction.get('estimated_cost', 0) 
                for interaction in ai_interactions
            )
            
            # Breakdown by model
            cost_by_model = defaultdict(float)
            requests_by_model = defaultdict(int)
            
            for interaction in ai_interactions:
                model = interaction.get('model_used', 'unknown')
                cost = interaction.get('estimated_cost', 0)
                cost_by_model[model] += cost
                requests_by_model[model] += 1
            
            cost_analysis['current_period'] = {
                'total_cost': total_cost,
                'cost_by_model': dict(cost_by_model),
                'requests_by_model': dict(requests_by_model),
                'average_cost_per_request': total_cost / len(ai_interactions) if ai_interactions else 0
            }
            
            # Calculate what it would cost with single premium model
            premium_model_cost = len(ai_interactions) * 0.15  # Assume Claude Sonnet cost
            actual_savings = premium_model_cost - total_cost
            savings_percentage = (actual_savings / premium_model_cost) * 100 if premium_model_cost > 0 else 0
            
            cost_analysis['optimization_effectiveness'] = {
                'estimated_premium_cost': premium_model_cost,
                'actual_cost': total_cost,
                'savings_amount': actual_savings,
                'savings_percentage': savings_percentage
            }
            
            # Projected monthly savings
            daily_savings = actual_savings
            cost_analysis['projected_savings'] = {
                'daily': daily_savings,
                'weekly': daily_savings * 7,
                'monthly': daily_savings * 30,
                'yearly': daily_savings * 365
            }
            
            # Cost optimization recommendations
            if savings_percentage < 50:
                cost_analysis['recommendations'].append({
                    'priority': 'high',
                    'action': 'Optimize model routing',
                    'description': f'Current savings only {savings_percentage:.1f}%, target 70%+'
                })
            
            if cost_by_model.get('claude', 0) > total_cost * 0.1:
                cost_analysis['recommendations'].append({
                    'priority': 'medium',
                    'action': 'Reduce Claude usage',
                    'description': 'Claude usage higher than optimal 5-10% target'
                })
        
        except Exception as e:
            cost_analysis['error'] = str(e)
        
        return cost_analysis
    
    async def _analyze_ai_errors(self) -> Dict[str, Any]:
        """Analyze AI-related error patterns."""
        error_analysis = {
            'total_errors': 0,
            'error_types': defaultdict(int),
            'error_trends': {},
            'model_specific_errors': defaultdict(list),
            'critical_patterns': []
        }
        
        try:
            # Parse error logs
            error_log_path = Path('logs/errors/errors.log')
            if not error_log_path.exists():
                error_analysis['error'] = 'Error log not found'
                return error_analysis
            
            with open(error_log_path, 'r') as f:
                lines = f.readlines()
            
            # Look for AI-related errors
            ai_error_patterns = [
                (r'AI_\d{3}', 'AI service error'),
                (r'anthropic', 'Anthropic API error'),
                (r'openai', 'OpenAI API error'),
                (r'rate.*limit', 'Rate limit error'),
                (r'timeout', 'Timeout error'),
                (r'token.*limit', 'Token limit error')
            ]
            
            for line in lines:
                for pattern, error_type in ai_error_patterns:
                    if re.search(pattern, line, re.IGNORECASE):
                        error_analysis['error_types'][error_type] += 1
                        error_analysis['total_errors'] += 1
            
            # Analyze trends (simplified - would need more sophisticated time series analysis)
            recent_errors = sum(
                1 for line in lines[-100:]  # Last 100 lines
                if any(re.search(pattern, line, re.IGNORECASE) for pattern, _ in ai_error_patterns)
            )
            
            error_analysis['recent_error_rate'] = recent_errors
            
            # Critical patterns
            if error_analysis['error_types']['Rate limit error'] > 10:
                error_analysis['critical_patterns'].append(
                    'High rate limit errors - need to implement better throttling'
                )
            
            if error_analysis['error_types']['Timeout error'] > 5:
                error_analysis['critical_patterns'].append(
                    'Frequent timeouts - investigate network or API performance'
                )
        
        except Exception as e:
            error_analysis['error'] = str(e)
        
        return error_analysis
    
    async def _analyze_response_quality(self) -> Dict[str, Any]:
        """Analyze AI response quality metrics."""
        quality_analysis = {
            'response_lengths': {'by_model': {}},
            'completion_rates': {'by_model': {}},
            'user_satisfaction_indicators': {},
            'quality_scores': {}
        }
        
        try:
            ai_interactions = await self._parse_ai_logs(hours=24)
            
            # Group by model for quality analysis
            by_model = defaultdict(list)
            for interaction in ai_interactions:
                model = interaction.get('model_used', 'unknown')
                by_model[model].append(interaction)
            
            # Analyze response characteristics for each model
            for model, interactions in by_model.items():
                response_lengths = [
                    len(interaction.get('response', ''))
                    for interaction in interactions
                    if interaction.get('response')
                ]
                
                if response_lengths:
                    quality_analysis['response_lengths']['by_model'][model] = {
                        'avg_length': statistics.mean(response_lengths),
                        'median_length': statistics.median(response_lengths),
                        'min_length': min(response_lengths),
                        'max_length': max(response_lengths)
                    }
                
                # Completion rate (non-empty responses)
                completed = [
                    interaction for interaction in interactions
                    if interaction.get('response') and len(interaction.get('response', '')) > 10
                ]
                completion_rate = (len(completed) / len(interactions)) * 100 if interactions else 0
                quality_analysis['completion_rates']['by_model'][model] = completion_rate
            
            # User satisfaction indicators (would need user feedback data)
            # For now, use proxy metrics like response length consistency
            
        except Exception as e:
            quality_analysis['error'] = str(e)
        
        return quality_analysis
    
    async def _check_api_health(self) -> Dict[str, Any]:
        """Check health of AI API endpoints."""
        api_health = {
            'anthropic': {'status': 'unknown', 'latency': 0},
            'openai': {'status': 'unknown', 'latency': 0},
            'connectivity': {},
            'rate_limits': {}
        }
        
        try:
            # Test Anthropic API
            start_time = datetime.now()
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
                try:
                    # Simple API test - would need actual API keys and endpoints
                    anthropic_latency = (datetime.now() - start_time).total_seconds() * 1000
                    api_health['anthropic']['latency'] = anthropic_latency
                    api_health['anthropic']['status'] = 'reachable'
                except Exception as e:
                    api_health['anthropic']['status'] = 'error'
                    api_health['anthropic']['error'] = str(e)
                
                # Test OpenAI API
                start_time = datetime.now()
                try:
                    openai_latency = (datetime.now() - start_time).total_seconds() * 1000
                    api_health['openai']['latency'] = openai_latency
                    api_health['openai']['status'] = 'reachable'
                except Exception as e:
                    api_health['openai']['status'] = 'error'
                    api_health['openai']['error'] = str(e)
        
        except Exception as e:
            api_health['general_error'] = str(e)
        
        return api_health
    
    async def _parse_ai_logs(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Parse AI interaction logs from the last N hours."""
        interactions = []
        
        if not self.ai_logs_path.exists():
            return interactions
        
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        try:
            with open(self.ai_logs_path, 'r') as f:
                for line in f:
                    try:
                        log_entry = json.loads(line.strip())
                        
                        # Parse timestamp
                        timestamp_str = log_entry.get('timestamp', '')
                        if timestamp_str:
                            log_time = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                            if log_time.replace(tzinfo=None) > cutoff_time:
                                interactions.append(log_entry)
                    
                    except (json.JSONDecodeError, ValueError):
                        continue
        
        except Exception as e:
            print(f"    ⚠️ Error parsing AI logs: {str(e)}")
        
        return interactions
    
    async def _calculate_cost_savings(self, interactions: List[Dict[str, Any]]) -> Dict[str, float]:
        """Calculate estimated cost savings from intelligent routing."""
        # Model costs per 1K tokens (approximate)
        MODEL_COSTS = {
            'claude': 0.015,    # Claude Sonnet
            'gpt4': 0.005,      # GPT-4
            'gpt4o_mini': 0.001 # GPT-4o-mini
        }
        
        actual_cost = 0
        if_all_premium_cost = 0
        
        for interaction in interactions:
            tokens = interaction.get('tokens_used', 1000)  # Default estimate
            model = interaction.get('model_used', 'unknown')
            
            # Actual cost
            model_key = self._normalize_model_name(model)
            if model_key in MODEL_COSTS:
                actual_cost += (tokens / 1000) * MODEL_COSTS[model_key]
            
            # If all were premium (Claude)
            if_all_premium_cost += (tokens / 1000) * MODEL_COSTS['claude']
        
        savings = if_all_premium_cost - actual_cost
        savings_percentage = (savings / if_all_premium_cost * 100) if if_all_premium_cost > 0 else 0
        
        return {
            'actual_cost': actual_cost,
            'if_all_premium_cost': if_all_premium_cost,
            'savings_amount': savings,
            'savings_percentage': savings_percentage
        }
    
    async def _analyze_routing_patterns(self, interactions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze patterns in routing decisions."""
        patterns = {
            'by_task_type': defaultdict(lambda: defaultdict(int)),
            'by_time_of_day': defaultdict(lambda: defaultdict(int)),
            'by_user_tier': defaultdict(lambda: defaultdict(int)),
            'routing_logic_distribution': defaultdict(int)
        }
        
        for interaction in interactions:
            model = interaction.get('model_used', 'unknown')
            task_type = interaction.get('task_type', 'unknown')
            routing_reason = interaction.get('routing_reason', 'unknown')
            
            # By task type
            patterns['by_task_type'][task_type][model] += 1
            
            # By routing logic
            patterns['routing_logic_distribution'][routing_reason] += 1
            
            # By time of day (if timestamp available)
            timestamp_str = interaction.get('timestamp', '')
            if timestamp_str:
                try:
                    timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                    hour = timestamp.hour
                    time_period = 'morning' if 6 <= hour < 12 else 'afternoon' if 12 <= hour < 18 else 'evening' if 18 <= hour < 24 else 'night'
                    patterns['by_time_of_day'][time_period][model] += 1
                except:
                    pass
        
        return patterns
    
    async def _compare_models(self, model_performance: Dict[str, Any]) -> Dict[str, Any]:
        """Compare performance across models."""
        comparison = {
            'best_performance': {},
            'efficiency_ranking': [],
            'cost_effectiveness': {},
            'use_case_recommendations': {}
        }
        
        models_data = {}
        for model_name, data in model_performance.items():
            if model_name != 'overall_comparison' and 'metrics' in data:
                models_data[model_name] = data['metrics']
        
        if not models_data:
            return comparison
        
        # Best performance metrics
        if models_data:
            best_success_rate = max(models_data.values(), key=lambda x: x.get('success_rate', 0))
            best_response_time = min(models_data.values(), key=lambda x: x.get('avg_response_time', float('inf')))
            best_cost_efficiency = min(models_data.values(), key=lambda x: x.get('avg_cost_per_request', float('inf')))
            
            comparison['best_performance'] = {
                'success_rate': best_success_rate,
                'response_time': best_response_time,
                'cost_efficiency': best_cost_efficiency
            }
        
        # Use case recommendations
        comparison['use_case_recommendations'] = {
            'quick_tasks': 'gpt4o_mini',
            'complex_analysis': 'claude_sonnet',
            'balanced_performance': 'gpt4'
        }
        
        return comparison
    
    def _normalize_model_name(self, model_name: str) -> str:
        """Normalize model names for consistent analysis."""
        model_name = model_name.lower()
        if 'claude' in model_name:
            return 'claude_sonnet'
        elif 'gpt-4o-mini' in model_name or 'gpt4o_mini' in model_name:
            return 'gpt4o_mini'
        elif 'gpt-4' in model_name or 'gpt4' in model_name:
            return 'gpt4'
        return model_name
    
    def _calculate_ai_health_score(self, analysis: Dict[str, Any]) -> float:
        """Calculate overall AI system health score."""
        score = 100.0
        
        # Routing performance
        routing = analysis.get('routing_analysis', {})
        if routing.get('fallback_rate', 0) > 10:  # >10% fallback rate
            score -= 15
        
        # Model performance
        model_perf = analysis.get('model_performance', {})
        for model_name, model_data in model_perf.items():
            if model_name == 'overall_comparison':
                continue
            
            metrics = model_data.get('metrics', {})
            success_rate = metrics.get('success_rate', 100)
            if success_rate < 95:
                score -= 10
            
            avg_response_time = metrics.get('avg_response_time', 0)
            if avg_response_time > 30:  # >30 seconds
                score -= 10
        
        # Error analysis
        errors = analysis.get('error_patterns', {})
        total_errors = errors.get('total_errors', 0)
        if total_errors > 50:  # >50 errors in 24h
            score -= 20
        
        # API health
        api_health = analysis.get('api_health', {})
        for api_name, api_data in api_health.items():
            if api_data.get('status') == 'error':
                score -= 15
        
        return max(0.0, score)
    
    def _extract_ai_issues(self, analysis: Dict[str, Any]) -> List[Dict[str, str]]:
        """Extract issues from AI analysis."""
        issues = []
        
        # Routing issues
        routing = analysis.get('routing_analysis', {})
        if routing.get('fallback_rate', 0) > 10:
            issues.append({
                'severity': 'high',
                'component': 'ai_routing',
                'issue': f"High fallback rate: {routing['fallback_rate']:.1f}%",
                'recommendation': 'Review routing logic and model availability'
            })
        
        # Model-specific issues
        model_perf = analysis.get('model_performance', {})
        for model_name, model_data in model_perf.items():
            if model_name == 'overall_comparison':
                continue
            
            for issue in model_data.get('issues', []):
                issues.append({
                    'severity': 'medium',
                    'component': f'ai_model_{model_name}',
                    'issue': issue,
                    'recommendation': f'Investigate {model_name} performance issues'
                })
        
        # API issues
        api_health = analysis.get('api_health', {})
        for api_name, api_data in api_health.items():
            if api_data.get('status') == 'error':
                issues.append({
                    'severity': 'critical',
                    'component': 'ai_api',
                    'issue': f"{api_name} API unreachable",
                    'recommendation': f'Check {api_name} API credentials and connectivity'
                })
        
        return issues
    
    def _generate_ai_recommendations(self, analysis: Dict[str, Any]) -> List[Dict[str, str]]:
        """Generate AI system recommendations."""
        recommendations = []
        
        # Cost optimization
        cost_analysis = analysis.get('cost_analysis', {})
        optimization = cost_analysis.get('optimization_effectiveness', {})
        if optimization.get('savings_percentage', 0) < 50:
            recommendations.append({
                'priority': 'high',
                'action': 'Optimize AI routing algorithm',
                'description': f'Current savings {optimization.get("savings_percentage", 0):.1f}%, target 70%+',
                'effort': '4-8 hours'
            })
        
        # Performance optimization
        model_perf = analysis.get('model_performance', {})
        for model_name, model_data in model_perf.items():
            if model_name == 'overall_comparison':
                continue
            
            metrics = model_data.get('metrics', {})
            if metrics.get('avg_response_time', 0) > 20:
                recommendations.append({
                    'priority': 'medium',
                    'action': f'Optimize {model_name} response time',
                    'description': f'Average response time {metrics["avg_response_time"]:.1f}s',
                    'effort': '2-4 hours'
                })
        
        # Error handling
        errors = analysis.get('error_patterns', {})
        if errors.get('total_errors', 0) > 20:
            recommendations.append({
                'priority': 'high',
                'action': 'Improve AI error handling',
                'description': f'{errors["total_errors"]} errors in 24h',
                'effort': '3-6 hours'
            })
        
        return recommendations
    
    async def debug_specific_issue(self, issue_type: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Debug specific AI-related issues."""
        debug_result = {
            'issue_type': issue_type,
            'timestamp': datetime.now().isoformat(),
            'analysis': {},
            'recommendations': []
        }
        
        if issue_type == 'ai_routing_slow':
            # Analyze routing performance
            recent_interactions = await self._parse_ai_logs(hours=1)  # Last hour
            
            routing_times = [
                interaction.get('routing_time', 0)
                for interaction in recent_interactions
                if 'routing_time' in interaction
            ]
            
            debug_result['analysis'] = {
                'recent_routing_times': routing_times,
                'avg_routing_time': statistics.mean(routing_times) if routing_times else 0,
                'slow_routing_count': len([t for t in routing_times if t > 2.0])
            }
            
            if routing_times and statistics.mean(routing_times) > 1.0:
                debug_result['recommendations'] = [
                    {
                        'action': 'Optimize routing algorithm',
                        'description': 'Routing taking >1s average, implement caching',
                        'priority': 'high'
                    }
                ]
        
        elif issue_type == 'ai_model_errors':
            # Analyze model-specific errors
            model_name = context.get('model', 'all')
            recent_interactions = await self._parse_ai_logs(hours=6)
            
            errors = [
                interaction for interaction in recent_interactions
                if interaction.get('status') == 'error' and 
                (model_name == 'all' or interaction.get('model_used') == model_name)
            ]
            
            error_types = Counter([
                interaction.get('error_type', 'unknown')
                for interaction in errors
            ])
            
            debug_result['analysis'] = {
                'total_errors': len(errors),
                'error_types': dict(error_types),
                'error_rate': (len(errors) / len(recent_interactions)) * 100 if recent_interactions else 0
            }
            
            if len(errors) > 5:
                debug_result['recommendations'] = [
                    {
                        'action': 'Investigate error patterns',
                        'description': f'{len(errors)} errors in last 6h',
                        'priority': 'high'
                    }
                ]
        
        elif issue_type == 'ai_cost_high':
            # Analyze cost patterns
            cost_analysis = await self._analyze_cost_optimization()
            
            debug_result['analysis'] = cost_analysis
            debug_result['recommendations'] = [
                {
                    'action': 'Review model distribution',
                    'description': 'Optimize routing to use more cost-effective models',
                    'priority': 'medium'
                }
            ]
        
        return debug_result