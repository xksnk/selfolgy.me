"""
💬 Chat Manager Debugger Component
Advanced debugging for chat management systems, user flows, and conversation states.
"""

import asyncio
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from collections import defaultdict, Counter
import re


class ChatManagerDebugger:
    """
    Comprehensive debugger for chat management systems in Selfology.
    Handles user flow analysis, state management debugging, and conversation quality assessment.
    """
    
    def __init__(self):
        self.debug_start = datetime.now()
        self.bot_logs_path = Path('logs/bot/bot_activity.log')
        self.user_logs_path = Path('logs/users/user_activity.log')
        self.main_logs_path = Path('logs/selfology.log')
    
    async def debug_chat_systems(self) -> Dict[str, Any]:
        """
        Comprehensive debugging of chat management systems.
        """
        print("    🔍 Debugging chat management systems...")
        
        chat_debug = {
            'timestamp': datetime.now().isoformat(),
            'user_flow_analysis': await self._analyze_user_flows(),
            'state_management': await self._analyze_state_management(),
            'conversation_quality': await self._analyze_conversation_quality(),
            'error_patterns': await self._analyze_chat_errors(),
            'performance_metrics': await self._analyze_chat_performance(),
            'user_engagement': await self._analyze_user_engagement(),
            'bot_responses': await self._analyze_bot_responses(),
            'session_management': await self._analyze_session_management(),
            'issues': [],
            'recommendations': [],
            'health_score': 0.0
        }
        
        # Calculate overall chat system health
        chat_debug['health_score'] = self._calculate_chat_health_score(chat_debug)
        chat_debug['issues'] = self._extract_chat_issues(chat_debug)
        chat_debug['recommendations'] = self._generate_chat_recommendations(chat_debug)
        
        return chat_debug
    
    async def _analyze_user_flows(self) -> Dict[str, Any]:
        """Analyze user flow patterns and completion rates."""
        flow_analysis = {
            'total_sessions': 0,
            'flow_stages': {},
            'completion_rates': {},
            'drop_off_points': {},
            'user_journey_patterns': {}
        }
        
        try:
            # Parse user activity logs
            user_activities = await self._parse_user_logs(hours=24)
            
            if not user_activities:
                flow_analysis['error'] = 'No user activity found'
                return flow_analysis
            
            # Group by user sessions
            user_sessions = defaultdict(list)
            for activity in user_activities:
                user_id = activity.get('user_id')
                if user_id:
                    user_sessions[user_id].append(activity)
            
            flow_analysis['total_sessions'] = len(user_sessions)
            
            # Analyze flow stages
            stage_transitions = defaultdict(lambda: defaultdict(int))
            stage_counts = defaultdict(int)
            
            # Expected flow stages
            expected_stages = [
                'start_command',
                'gdpr_consent',
                'assessment_start',
                'assessment_progress',
                'assessment_complete',
                'chat_session',
                'ai_interaction'
            ]
            
            for user_id, activities in user_sessions.items():
                # Sort activities by timestamp
                activities.sort(key=lambda x: x.get('timestamp', ''))
                
                previous_stage = None
                for activity in activities:
                    current_stage = activity.get('stage') or activity.get('action', 'unknown')
                    stage_counts[current_stage] += 1
                    
                    if previous_stage:
                        stage_transitions[previous_stage][current_stage] += 1
                    
                    previous_stage = current_stage
            
            flow_analysis['flow_stages'] = dict(stage_counts)
            flow_analysis['stage_transitions'] = {
                stage: dict(transitions) for stage, transitions in stage_transitions.items()
            }
            
            # Calculate completion rates for expected flow
            total_starts = stage_counts.get('start_command', 0)
            completion_rates = {}
            
            for stage in expected_stages:
                stage_count = stage_counts.get(stage, 0)
                completion_rate = (stage_count / total_starts) * 100 if total_starts > 0 else 0
                completion_rates[stage] = {
                    'count': stage_count,
                    'completion_rate': completion_rate
                }
            
            flow_analysis['completion_rates'] = completion_rates
            
            # Identify drop-off points
            drop_offs = {}
            for i, stage in enumerate(expected_stages[:-1]):
                current_count = stage_counts.get(stage, 0)
                next_stage = expected_stages[i + 1]
                next_count = stage_counts.get(next_stage, 0)
                
                if current_count > 0:
                    drop_off_rate = ((current_count - next_count) / current_count) * 100
                    drop_offs[f"{stage}_to_{next_stage}"] = {
                        'drop_off_rate': drop_off_rate,
                        'users_lost': current_count - next_count
                    }
            
            flow_analysis['drop_off_points'] = drop_offs
            
            # Analyze user journey patterns
            journey_patterns = defaultdict(int)
            for user_id, activities in user_sessions.items():
                # Create journey pattern string
                stages = [activity.get('stage', 'unknown') for activity in activities]
                pattern = ' -> '.join(stages[:5])  # First 5 stages
                journey_patterns[pattern] += 1
            
            # Get top 10 patterns
            top_patterns = dict(sorted(journey_patterns.items(), key=lambda x: x[1], reverse=True)[:10])
            flow_analysis['user_journey_patterns'] = top_patterns
        
        except Exception as e:
            flow_analysis['error'] = str(e)
        
        return flow_analysis
    
    async def _analyze_state_management(self) -> Dict[str, Any]:
        """Analyze FSM state management and transitions."""
        state_analysis = {
            'state_distribution': {},
            'transition_patterns': {},
            'state_errors': [],
            'stuck_states': {},
            'invalid_transitions': []
        }
        
        try:
            # Parse bot logs for state information
            bot_activities = await self._parse_bot_logs(hours=24)
            
            if not bot_activities:
                state_analysis['error'] = 'No bot activity logs found'
                return state_analysis
            
            # Extract state information
            states = []
            transitions = []
            state_errors = []
            
            for activity in bot_activities:
                # Look for state-related information
                message = activity.get('message', '')
                
                # Extract current state
                state_match = re.search(r'state[:\s]+(\w+)', message, re.IGNORECASE)
                if state_match:
                    states.append(state_match.group(1))
                
                # Extract state transitions
                transition_match = re.search(r'transition[:\s]+(\w+)\s*->\s*(\w+)', message, re.IGNORECASE)
                if transition_match:
                    transitions.append((transition_match.group(1), transition_match.group(2)))
                
                # Look for state errors
                if 'state' in message.lower() and ('error' in message.lower() or 'failed' in message.lower()):
                    state_errors.append({
                        'timestamp': activity.get('timestamp'),
                        'user_id': activity.get('user_id'),
                        'error': message
                    })
            
            # State distribution
            state_counts = Counter(states)
            state_analysis['state_distribution'] = dict(state_counts)
            
            # Transition patterns
            transition_counts = Counter(transitions)
            state_analysis['transition_patterns'] = {
                f"{from_state} -> {to_state}": count
                for (from_state, to_state), count in transition_counts.items()
            }
            
            state_analysis['state_errors'] = state_errors
            
            # Identify stuck states (states with high count but few transitions out)
            stuck_threshold = 10  # More than 10 occurrences
            transition_out_counts = defaultdict(int)
            
            for (from_state, to_state), count in transition_counts.items():
                transition_out_counts[from_state] += count
            
            stuck_states = {}
            for state, count in state_counts.items():
                transitions_out = transition_out_counts.get(state, 0)
                if count > stuck_threshold and transitions_out < count * 0.5:
                    stuck_states[state] = {
                        'occurrences': count,
                        'transitions_out': transitions_out,
                        'stuck_percentage': ((count - transitions_out) / count) * 100
                    }
            
            state_analysis['stuck_states'] = stuck_states
        
        except Exception as e:
            state_analysis['error'] = str(e)
        
        return state_analysis
    
    async def _analyze_conversation_quality(self) -> Dict[str, Any]:
        """Analyze conversation quality and engagement metrics."""
        quality_analysis = {
            'message_statistics': {},
            'response_completeness': {},
            'conversation_depth': {},
            'user_satisfaction_indicators': {}
        }
        
        try:
            # Parse user activities for conversation data
            user_activities = await self._parse_user_logs(hours=24)
            bot_activities = await self._parse_bot_logs(hours=24)
            
            # Combine and analyze conversations
            all_messages = user_activities + bot_activities
            all_messages.sort(key=lambda x: x.get('timestamp', ''))
            
            # Message statistics
            user_messages = [msg for msg in all_messages if msg.get('type') == 'user_message']
            bot_responses = [msg for msg in all_messages if msg.get('type') == 'bot_response']
            
            quality_analysis['message_statistics'] = {
                'total_messages': len(all_messages),
                'user_messages': len(user_messages),
                'bot_responses': len(bot_responses),
                'response_ratio': len(bot_responses) / len(user_messages) if user_messages else 0
            }
            
            # Analyze response completeness (non-empty, meaningful responses)
            meaningful_responses = 0
            empty_responses = 0
            error_responses = 0
            
            for response in bot_responses:
                content = response.get('content', '')
                if not content or len(content.strip()) < 5:
                    empty_responses += 1
                elif 'error' in content.lower() or 'sorry' in content.lower()[:20]:
                    error_responses += 1
                else:
                    meaningful_responses += 1
            
            total_responses = len(bot_responses)
            quality_analysis['response_completeness'] = {
                'meaningful_responses': meaningful_responses,
                'empty_responses': empty_responses,
                'error_responses': error_responses,
                'completeness_percentage': (meaningful_responses / total_responses) * 100 if total_responses > 0 else 0
            }
            
            # Conversation depth analysis
            conversations = self._group_messages_by_conversation(all_messages)
            depth_metrics = []
            
            for conv_id, messages in conversations.items():
                depth_metrics.append({
                    'conversation_id': conv_id,
                    'total_exchanges': len(messages),
                    'user_messages': len([m for m in messages if m.get('type') == 'user_message']),
                    'bot_responses': len([m for m in messages if m.get('type') == 'bot_response']),
                    'duration_minutes': self._calculate_conversation_duration(messages)
                })
            
            if depth_metrics:
                quality_analysis['conversation_depth'] = {
                    'total_conversations': len(depth_metrics),
                    'avg_exchanges_per_conversation': sum(m['total_exchanges'] for m in depth_metrics) / len(depth_metrics),
                    'avg_duration_minutes': sum(m['duration_minutes'] for m in depth_metrics) / len(depth_metrics),
                    'conversations_by_length': {
                        'short (1-5 exchanges)': len([m for m in depth_metrics if m['total_exchanges'] <= 5]),
                        'medium (6-15 exchanges)': len([m for m in depth_metrics if 6 <= m['total_exchanges'] <= 15]),
                        'long (16+ exchanges)': len([m for m in depth_metrics if m['total_exchanges'] > 15])
                    }
                }
        
        except Exception as e:
            quality_analysis['error'] = str(e)
        
        return quality_analysis
    
    async def _analyze_chat_errors(self) -> Dict[str, Any]:
        """Analyze chat-related error patterns."""
        error_analysis = {
            'total_chat_errors': 0,
            'error_categories': {},
            'error_frequency': {},
            'user_impact': {},
            'recovery_patterns': {}
        }
        
        try:
            # Parse error logs
            error_log_path = Path('logs/errors/errors.log')
            if not error_log_path.exists():
                error_analysis['error'] = 'Error log not found'
                return error_analysis
            
            with open(error_log_path, 'r') as f:
                error_lines = f.readlines()
            
            # Chat-related error patterns
            chat_error_patterns = [
                (r'USER_\d{3}', 'User interaction error'),
                (r'BOT_\d{3}', 'Bot operation error'),
                (r'state.*error', 'State management error'),
                (r'message.*failed', 'Message handling error'),
                (r'conversation.*error', 'Conversation flow error'),
                (r'timeout.*user', 'User timeout error')
            ]
            
            chat_errors = []
            error_categories = defaultdict(int)
            
            for line in error_lines:
                for pattern, category in chat_error_patterns:
                    if re.search(pattern, line, re.IGNORECASE):
                        chat_errors.append(line.strip())
                        error_categories[category] += 1
                        break
            
            error_analysis['total_chat_errors'] = len(chat_errors)
            error_analysis['error_categories'] = dict(error_categories)
            
            # Error frequency analysis (by hour)
            current_time = datetime.now()
            hourly_errors = defaultdict(int)
            
            for error in chat_errors[-100:]:  # Last 100 errors
                # Try to extract timestamp (simplified)
                # In real implementation, would parse actual timestamps
                hourly_errors[current_time.hour] += 1
            
            error_analysis['error_frequency'] = dict(hourly_errors)
            
            # Analyze user impact
            affected_users = set()
            for error in chat_errors:
                # Extract user ID if present
                user_match = re.search(r'user[_\s]*(\d+)', error, re.IGNORECASE)
                if user_match:
                    affected_users.add(user_match.group(1))
            
            error_analysis['user_impact'] = {
                'affected_users': len(affected_users),
                'error_rate_per_user': len(chat_errors) / len(affected_users) if affected_users else 0
            }
        
        except Exception as e:
            error_analysis['error'] = str(e)
        
        return error_analysis
    
    async def _analyze_chat_performance(self) -> Dict[str, Any]:
        """Analyze chat system performance metrics."""
        performance = {
            'response_times': {},
            'throughput': {},
            'resource_usage': {},
            'bottlenecks': []
        }
        
        try:
            # Parse performance metrics from logs
            metrics_log_path = Path('logs/metrics/metrics.log')
            if metrics_log_path.exists():
                metrics_data = await self._parse_metrics_logs(hours=24)
                
                # Extract chat-related performance metrics
                chat_response_times = []
                message_throughput = []
                
                for metric in metrics_data:
                    metric_name = metric.get('metric_name', '')
                    value = metric.get('value', 0)
                    
                    if 'chat_response_time' in metric_name or 'message_processing_time' in metric_name:
                        chat_response_times.append(value)
                    
                    if 'messages_processed' in metric_name:
                        message_throughput.append(value)
                
                if chat_response_times:
                    import statistics
                    performance['response_times'] = {
                        'average': statistics.mean(chat_response_times),
                        'median': statistics.median(chat_response_times),
                        'p95': sorted(chat_response_times)[int(len(chat_response_times) * 0.95)] if chat_response_times else 0,
                        'max': max(chat_response_times),
                        'count': len(chat_response_times)
                    }
                
                if message_throughput:
                    performance['throughput'] = {
                        'average_messages_per_hour': sum(message_throughput) / len(message_throughput),
                        'peak_throughput': max(message_throughput),
                        'total_messages': sum(message_throughput)
                    }
                
                # Identify bottlenecks
                bottlenecks = []
                if chat_response_times:
                    avg_response_time = statistics.mean(chat_response_times)
                    if avg_response_time > 5.0:  # >5 seconds
                        bottlenecks.append({
                            'type': 'slow_responses',
                            'severity': 'high' if avg_response_time > 10 else 'medium',
                            'description': f'Average response time {avg_response_time:.1f}s'
                        })
                
                performance['bottlenecks'] = bottlenecks
        
        except Exception as e:
            performance['error'] = str(e)
        
        return performance
    
    async def _analyze_user_engagement(self) -> Dict[str, Any]:
        """Analyze user engagement patterns and metrics."""
        engagement = {
            'active_users': {},
            'session_patterns': {},
            'retention_indicators': {},
            'engagement_score': 0.0
        }
        
        try:
            user_activities = await self._parse_user_logs(hours=24)
            
            if not user_activities:
                engagement['error'] = 'No user activity data'
                return engagement
            
            # Active users analysis
            unique_users = set(activity.get('user_id') for activity in user_activities if activity.get('user_id'))
            returning_users = set()
            
            # Group activities by user
            user_activity_map = defaultdict(list)
            for activity in user_activities:
                user_id = activity.get('user_id')
                if user_id:
                    user_activity_map[user_id].append(activity)
            
            # Analyze session patterns
            session_lengths = []
            messages_per_session = []
            
            for user_id, activities in user_activity_map.items():
                # Sort by timestamp
                activities.sort(key=lambda x: x.get('timestamp', ''))
                
                # Calculate session metrics
                if len(activities) > 1:
                    session_start = activities[0].get('timestamp')
                    session_end = activities[-1].get('timestamp')
                    
                    # Simple duration calculation (would need proper timestamp parsing)
                    session_lengths.append(len(activities))  # Proxy for duration
                    messages_per_session.append(len([a for a in activities if a.get('type') == 'user_message']))
                
                # Check for returning users (multiple sessions)
                if len(activities) > 5:  # Arbitrary threshold
                    returning_users.add(user_id)
            
            engagement['active_users'] = {
                'total_unique_users': len(unique_users),
                'returning_users': len(returning_users),
                'return_rate': (len(returning_users) / len(unique_users)) * 100 if unique_users else 0
            }
            
            if session_lengths:
                import statistics
                engagement['session_patterns'] = {
                    'average_session_length': statistics.mean(session_lengths),
                    'average_messages_per_session': statistics.mean(messages_per_session) if messages_per_session else 0,
                    'total_sessions': len(session_lengths)
                }
            
            # Calculate engagement score
            engagement_factors = [
                min(len(unique_users) / 10, 1.0),  # User count factor (max 10)
                min(len(returning_users) / len(unique_users) if unique_users else 0, 1.0),  # Return rate
                min(statistics.mean(session_lengths) / 20, 1.0) if session_lengths else 0,  # Session length factor
            ]
            
            engagement['engagement_score'] = sum(engagement_factors) / len(engagement_factors) * 100
        
        except Exception as e:
            engagement['error'] = str(e)
        
        return engagement
    
    async def _analyze_bot_responses(self) -> Dict[str, Any]:
        """Analyze bot response quality and patterns."""
        response_analysis = {
            'response_types': {},
            'response_quality': {},
            'ai_model_usage': {},
            'response_patterns': {}
        }
        
        try:
            bot_activities = await self._parse_bot_logs(hours=24)
            
            # Categorize response types
            response_types = defaultdict(int)
            ai_model_usage = defaultdict(int)
            
            for activity in bot_activities:
                response_type = activity.get('response_type', 'unknown')
                response_types[response_type] += 1
                
                # Extract AI model if mentioned
                message = activity.get('message', '')
                if 'claude' in message.lower():
                    ai_model_usage['claude'] += 1
                elif 'gpt-4' in message.lower():
                    ai_model_usage['gpt4'] += 1
                elif 'gpt-4o-mini' in message.lower():
                    ai_model_usage['gpt4o_mini'] += 1
            
            response_analysis['response_types'] = dict(response_types)
            response_analysis['ai_model_usage'] = dict(ai_model_usage)
            
            # Response quality assessment (basic)
            total_responses = len(bot_activities)
            error_responses = len([a for a in bot_activities if 'error' in a.get('message', '').lower()])
            
            response_analysis['response_quality'] = {
                'total_responses': total_responses,
                'error_responses': error_responses,
                'success_rate': ((total_responses - error_responses) / total_responses) * 100 if total_responses > 0 else 0
            }
        
        except Exception as e:
            response_analysis['error'] = str(e)
        
        return response_analysis
    
    async def _analyze_session_management(self) -> Dict[str, Any]:
        """Analyze session management and persistence."""
        session_analysis = {
            'session_statistics': {},
            'session_persistence': {},
            'timeout_analysis': {},
            'state_persistence': {}
        }
        
        try:
            # This would analyze session data from logs or database
            # For now, provide structure for implementation
            session_analysis['session_statistics'] = {
                'note': 'Session analysis requires database integration'
            }
        
        except Exception as e:
            session_analysis['error'] = str(e)
        
        return session_analysis
    
    async def _parse_user_logs(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Parse user activity logs."""
        activities = []
        
        if not self.user_logs_path.exists():
            return activities
        
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        try:
            with open(self.user_logs_path, 'r') as f:
                for line in f:
                    try:
                        log_entry = json.loads(line.strip())
                        
                        # Parse timestamp
                        timestamp_str = log_entry.get('timestamp', '')
                        if timestamp_str:
                            log_time = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                            if log_time.replace(tzinfo=None) > cutoff_time:
                                activities.append(log_entry)
                    
                    except (json.JSONDecodeError, ValueError):
                        continue
        
        except Exception:
            pass
        
        return activities
    
    async def _parse_bot_logs(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Parse bot activity logs."""
        activities = []
        
        if not self.bot_logs_path.exists():
            return activities
        
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        try:
            with open(self.bot_logs_path, 'r') as f:
                for line in f:
                    try:
                        log_entry = json.loads(line.strip())
                        
                        # Parse timestamp
                        timestamp_str = log_entry.get('timestamp', '')
                        if timestamp_str:
                            log_time = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                            if log_time.replace(tzinfo=None) > cutoff_time:
                                activities.append(log_entry)
                    
                    except (json.JSONDecodeError, ValueError):
                        continue
        
        except Exception:
            pass
        
        return activities
    
    async def _parse_metrics_logs(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Parse metrics logs."""
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
    
    def _group_messages_by_conversation(self, messages: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """Group messages by conversation/user."""
        conversations = defaultdict(list)
        
        for message in messages:
            # Use user_id as conversation identifier (simplified)
            conv_id = message.get('user_id', 'unknown')
            conversations[conv_id].append(message)
        
        return conversations
    
    def _calculate_conversation_duration(self, messages: List[Dict[str, Any]]) -> float:
        """Calculate conversation duration in minutes."""
        if len(messages) < 2:
            return 0.0
        
        try:
            # Sort by timestamp
            messages.sort(key=lambda x: x.get('timestamp', ''))
            
            first_msg = messages[0]
            last_msg = messages[-1]
            
            # Parse timestamps (simplified - would need proper parsing)
            # For now, return message count as proxy for duration
            return len(messages) * 2  # Assume 2 minutes per message exchange
        
        except Exception:
            return 0.0
    
    def _calculate_chat_health_score(self, chat_debug: Dict[str, Any]) -> float:
        """Calculate overall chat system health score."""
        score = 100.0
        
        # User flow completion rates
        flow_analysis = chat_debug.get('user_flow_analysis', {})
        completion_rates = flow_analysis.get('completion_rates', {})
        
        # Check critical completion rates
        gdpr_completion = completion_rates.get('gdpr_consent', {}).get('completion_rate', 100)
        if gdpr_completion < 80:
            score -= (80 - gdpr_completion) * 0.5
        
        assessment_completion = completion_rates.get('assessment_complete', {}).get('completion_rate', 100)
        if assessment_completion < 60:
            score -= (60 - assessment_completion) * 0.5
        
        # State management issues
        state_analysis = chat_debug.get('state_management', {})
        state_errors = len(state_analysis.get('state_errors', []))
        if state_errors > 10:  # >10 state errors in 24h
            score -= min(state_errors, 30)  # Max 30 point deduction
        
        # Conversation quality
        quality_analysis = chat_debug.get('conversation_quality', {})
        response_completeness = quality_analysis.get('response_completeness', {})
        completeness_pct = response_completeness.get('completeness_percentage', 100)
        if completeness_pct < 90:
            score -= (90 - completeness_pct) * 0.8
        
        # Chat errors
        error_analysis = chat_debug.get('error_patterns', {})
        total_errors = error_analysis.get('total_chat_errors', 0)
        if total_errors > 50:  # >50 errors in 24h
            score -= min(total_errors - 50, 25)
        
        # Performance issues
        performance = chat_debug.get('performance_metrics', {})
        bottlenecks = len(performance.get('bottlenecks', []))
        score -= bottlenecks * 10
        
        return max(0.0, score)
    
    def _extract_chat_issues(self, chat_debug: Dict[str, Any]) -> List[Dict[str, str]]:
        """Extract issues from chat analysis."""
        issues = []
        
        # Flow completion issues
        flow_analysis = chat_debug.get('user_flow_analysis', {})
        drop_offs = flow_analysis.get('drop_off_points', {})
        
        for transition, drop_data in drop_offs.items():
            drop_rate = drop_data.get('drop_off_rate', 0)
            if drop_rate > 30:  # >30% drop-off
                issues.append({
                    'severity': 'high' if drop_rate > 50 else 'medium',
                    'component': 'user_flow',
                    'issue': f'High drop-off at {transition}: {drop_rate:.1f}%',
                    'recommendation': f'Investigate and improve {transition.split("_to_")[0]} experience'
                })
        
        # State management issues
        state_analysis = chat_debug.get('state_management', {})
        stuck_states = state_analysis.get('stuck_states', {})
        
        for state, stuck_data in stuck_states.items():
            stuck_pct = stuck_data.get('stuck_percentage', 0)
            issues.append({
                'severity': 'medium',
                'component': 'state_management',
                'issue': f'Users stuck in {state}: {stuck_pct:.1f}%',
                'recommendation': f'Review {state} exit conditions'
            })
        
        # Response quality issues
        quality_analysis = chat_debug.get('conversation_quality', {})
        response_completeness = quality_analysis.get('response_completeness', {})
        completeness_pct = response_completeness.get('completeness_percentage', 100)
        
        if completeness_pct < 85:
            issues.append({
                'severity': 'high',
                'component': 'response_quality',
                'issue': f'Low response completeness: {completeness_pct:.1f}%',
                'recommendation': 'Improve AI response generation and error handling'
            })
        
        # Performance issues
        performance = chat_debug.get('performance_metrics', {})
        for bottleneck in performance.get('bottlenecks', []):
            issues.append({
                'severity': bottleneck.get('severity', 'medium'),
                'component': 'chat_performance',
                'issue': bottleneck.get('description', 'Performance bottleneck'),
                'recommendation': 'Optimize chat response pipeline'
            })
        
        return issues
    
    def _generate_chat_recommendations(self, chat_debug: Dict[str, Any]) -> List[Dict[str, str]]:
        """Generate chat system recommendations."""
        recommendations = []
        
        # User flow optimization
        flow_analysis = chat_debug.get('user_flow_analysis', {})
        completion_rates = flow_analysis.get('completion_rates', {})
        
        assessment_completion = completion_rates.get('assessment_complete', {}).get('completion_rate', 100)
        if assessment_completion < 50:
            recommendations.append({
                'priority': 'high',
                'action': 'Optimize assessment flow',
                'description': f'Only {assessment_completion:.1f}% complete assessments',
                'effort': '6-12 hours'
            })
        
        # State management improvements
        state_analysis = chat_debug.get('state_management', {})
        if state_analysis.get('state_errors'):
            recommendations.append({
                'priority': 'high',
                'action': 'Fix state management errors',
                'description': f'{len(state_analysis["state_errors"])} state errors detected',
                'effort': '4-8 hours'
            })
        
        # Response quality improvements
        quality_analysis = chat_debug.get('conversation_quality', {})
        response_completeness = quality_analysis.get('response_completeness', {})
        empty_responses = response_completeness.get('empty_responses', 0)
        
        if empty_responses > 10:
            recommendations.append({
                'priority': 'medium',
                'action': 'Reduce empty responses',
                'description': f'{empty_responses} empty responses in 24h',
                'effort': '2-4 hours'
            })
        
        # Performance optimization
        performance = chat_debug.get('performance_metrics', {})
        response_times = performance.get('response_times', {})
        avg_response_time = response_times.get('average', 0)
        
        if avg_response_time > 5:
            recommendations.append({
                'priority': 'medium',
                'action': 'Optimize response times',
                'description': f'Average response time {avg_response_time:.1f}s',
                'effort': '3-6 hours'
            })
        
        # Engagement improvements
        engagement = chat_debug.get('user_engagement', {})
        engagement_score = engagement.get('engagement_score', 100)
        
        if engagement_score < 60:
            recommendations.append({
                'priority': 'high',
                'action': 'Improve user engagement',
                'description': f'Low engagement score: {engagement_score:.1f}%',
                'effort': '8-16 hours'
            })
        
        return recommendations
    
    async def debug_specific_issue(self, issue_type: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Debug specific chat-related issues."""
        debug_result = {
            'issue_type': issue_type,
            'timestamp': datetime.now().isoformat(),
            'analysis': {},
            'recommendations': []
        }
        
        if issue_type == 'chat_flow_stuck':
            # Analyze stuck user flows
            user_id = context.get('user_id')
            if user_id:
                # Get specific user's activity
                user_activities = await self._parse_user_logs(hours=72)
                user_specific = [a for a in user_activities if str(a.get('user_id')) == str(user_id)]
                
                debug_result['analysis'] = {
                    'user_id': user_id,
                    'total_activities': len(user_specific),
                    'recent_activities': user_specific[-10:],  # Last 10
                    'stuck_duration': 'Analysis needed'  # Would calculate actual duration
                }
                
                debug_result['recommendations'] = [
                    {
                        'action': 'Reset user state',
                        'description': f'User {user_id} appears stuck in conversation flow',
                        'priority': 'high'
                    }
                ]
        
        elif issue_type == 'chat_responses_empty':
            # Analyze empty response patterns
            bot_activities = await self._parse_bot_logs(hours=6)
            empty_responses = [
                activity for activity in bot_activities
                if not activity.get('content', '').strip()
            ]
            
            debug_result['analysis'] = {
                'empty_response_count': len(empty_responses),
                'recent_empty_responses': empty_responses[-5:],
                'patterns': 'Analysis of empty response triggers needed'
            }
            
            if empty_responses:
                debug_result['recommendations'] = [
                    {
                        'action': 'Investigate AI response generation',
                        'description': f'{len(empty_responses)} empty responses in 6h',
                        'priority': 'high'
                    }
                ]
        
        elif issue_type == 'chat_performance_slow':
            # Analyze performance bottlenecks
            performance_analysis = await self._analyze_chat_performance()
            debug_result['analysis'] = performance_analysis
            
            bottlenecks = performance_analysis.get('bottlenecks', [])
            if bottlenecks:
                debug_result['recommendations'] = [
                    {
                        'action': 'Optimize response pipeline',
                        'description': 'Multiple performance bottlenecks detected',
                        'priority': 'high'
                    }
                ]
        
        return debug_result