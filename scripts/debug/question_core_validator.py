"""
🧠 Question Core Validator Component
Comprehensive validation and debugging for the 693 intelligent psychological questions system.
"""

import asyncio
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Set
from collections import defaultdict, Counter
import networkx as nx


class QuestionCoreValidator:
    """
    Advanced validator for the intelligent question core system.
    Handles validation of 693 questions, navigation graph, energy dynamics, and domain coverage.
    """
    
    def __init__(self):
        self.core_data_path = Path('intelligent_question_core/data/selfology_intelligent_core.json')
        self.api_path = Path('intelligent_question_core/api/core_api.py')
        self.validation_start = datetime.now()
        
        # Expected system constants
        self.EXPECTED_QUESTIONS = 693
        self.EXPECTED_DOMAINS = 13
        self.EXPECTED_DEPTH_LEVELS = 5
        self.EXPECTED_CONNECTIONS = 344
        
        # Domain definitions
        self.EXPECTED_DOMAIN_NAMES = {
            'IDENTITY', 'EMOTIONS', 'RELATIONSHIPS', 'CAREER', 'VALUES',
            'GOALS', 'MINDSET', 'HEALTH', 'CREATIVITY', 'SPIRITUALITY',
            'LEARNING', 'COMMUNICATION', 'LEADERSHIP'
        }
        
        # Depth level definitions
        self.EXPECTED_DEPTH_LEVELS_NAMES = {
            'SURFACE', 'CONSCIOUS', 'EDGE', 'SHADOW', 'CORE'
        }
        
        # Energy types
        self.EXPECTED_ENERGY_TYPES = {
            'OPENING', 'NEUTRAL', 'PROCESSING', 'HEAVY', 'HEALING'
        }
    
    async def validate_question_system(self) -> Dict[str, Any]:
        """
        Comprehensive validation of the intelligent question core system.
        """
        print("    🔍 Validating intelligent question core (693 questions)...")
        
        validation = {
            'timestamp': datetime.now().isoformat(),
            'core_structure': await self._validate_core_structure(),
            'question_integrity': await self._validate_question_integrity(),
            'navigation_graph': await self._validate_navigation_graph(),
            'domain_coverage': await self._validate_domain_coverage(),
            'energy_dynamics': await self._validate_energy_dynamics(),
            'api_integration': await self._validate_api_integration(),
            'metadata_consistency': await self._validate_metadata_consistency(),
            'safety_rules': await self._validate_safety_rules(),
            'issues': [],
            'recommendations': [],
            'health_score': 0.0
        }
        
        # Calculate overall question system health
        validation['health_score'] = self._calculate_question_health_score(validation)
        validation['issues'] = self._extract_question_issues(validation)
        validation['recommendations'] = self._generate_question_recommendations(validation)
        
        return validation
    
    async def _validate_core_structure(self) -> Dict[str, Any]:
        """Validate the core JSON structure and basic counts."""
        structure = {
            'file_exists': False,
            'file_size': 0,
            'is_valid_json': False,
            'question_count': 0,
            'connection_count': 0,
            'structure_valid': False
        }
        
        try:
            if not self.core_data_path.exists():
                structure['error'] = 'Core data file not found'
                return structure
            
            structure['file_exists'] = True
            structure['file_size'] = self.core_data_path.stat().st_size
            
            # Load and parse JSON
            with open(self.core_data_path, 'r', encoding='utf-8') as f:
                core_data = json.load(f)
            
            structure['is_valid_json'] = True
            
            # Validate basic structure
            required_keys = ['questions', 'connections', 'domains', 'metadata']
            missing_keys = [key for key in required_keys if key not in core_data]
            
            if missing_keys:
                structure['missing_keys'] = missing_keys
                structure['structure_valid'] = False
            else:
                structure['structure_valid'] = True
                
                # Count elements
                structure['question_count'] = len(core_data.get('questions', []))
                structure['connection_count'] = len(core_data.get('connections', []))
                structure['domain_count'] = len(core_data.get('domains', []))
                
                # Validate counts against expected
                structure['count_validation'] = {
                    'questions_expected': self.EXPECTED_QUESTIONS,
                    'questions_actual': structure['question_count'],
                    'questions_match': structure['question_count'] == self.EXPECTED_QUESTIONS,
                    
                    'connections_expected': self.EXPECTED_CONNECTIONS,
                    'connections_actual': structure['connection_count'],
                    'connections_match': structure['connection_count'] == self.EXPECTED_CONNECTIONS,
                    
                    'domains_expected': self.EXPECTED_DOMAINS,
                    'domains_actual': structure['domain_count'],
                    'domains_match': structure['domain_count'] == self.EXPECTED_DOMAINS
                }
        
        except json.JSONDecodeError as e:
            structure['json_error'] = str(e)
        except Exception as e:
            structure['error'] = str(e)
        
        return structure
    
    async def _validate_question_integrity(self) -> Dict[str, Any]:
        """Validate individual question integrity and completeness."""
        integrity = {
            'questions_analyzed': 0,
            'valid_questions': 0,
            'invalid_questions': [],
            'missing_fields': defaultdict(int),
            'field_consistency': {},
            'duplicate_checks': {}
        }
        
        try:
            with open(self.core_data_path, 'r', encoding='utf-8') as f:
                core_data = json.load(f)
            
            questions = core_data.get('questions', [])
            integrity['questions_analyzed'] = len(questions)
            
            # Required fields for each question
            required_fields = [
                'id', 'question', 'domain', 'depth_level', 'energy_type',
                'recommended_model', 'metadata'
            ]
            
            question_ids = set()
            question_texts = set()
            
            for i, question in enumerate(questions):
                question_valid = True
                
                # Check required fields
                for field in required_fields:
                    if field not in question:
                        integrity['missing_fields'][field] += 1
                        question_valid = False
                
                # Check for duplicates
                q_id = question.get('id')
                q_text = question.get('question', '').strip().lower()
                
                if q_id in question_ids:
                    integrity['invalid_questions'].append({
                        'index': i,
                        'id': q_id,
                        'issue': 'Duplicate ID'
                    })
                    question_valid = False
                else:
                    question_ids.add(q_id)
                
                if q_text in question_texts:
                    integrity['invalid_questions'].append({
                        'index': i,
                        'id': q_id,
                        'issue': 'Duplicate question text'
                    })
                    question_valid = False
                else:
                    question_texts.add(q_text)
                
                # Validate field values
                domain = question.get('domain')
                if domain and domain not in self.EXPECTED_DOMAIN_NAMES:
                    integrity['invalid_questions'].append({
                        'index': i,
                        'id': q_id,
                        'issue': f'Invalid domain: {domain}'
                    })
                    question_valid = False
                
                depth_level = question.get('depth_level')
                if depth_level and depth_level not in self.EXPECTED_DEPTH_LEVELS_NAMES:
                    integrity['invalid_questions'].append({
                        'index': i,
                        'id': q_id,
                        'issue': f'Invalid depth level: {depth_level}'
                    })
                    question_valid = False
                
                energy_type = question.get('energy_type')
                if energy_type and energy_type not in self.EXPECTED_ENERGY_TYPES:
                    integrity['invalid_questions'].append({
                        'index': i,
                        'id': q_id,
                        'issue': f'Invalid energy type: {energy_type}'
                    })
                    question_valid = False
                
                if question_valid:
                    integrity['valid_questions'] += 1
            
            # Calculate integrity statistics
            integrity['integrity_percentage'] = (
                integrity['valid_questions'] / integrity['questions_analyzed'] * 100
            ) if integrity['questions_analyzed'] > 0 else 0
            
            integrity['duplicate_checks'] = {
                'unique_ids': len(question_ids),
                'unique_texts': len(question_texts),
                'expected_unique': len(questions)
            }
        
        except Exception as e:
            integrity['error'] = str(e)
        
        return integrity
    
    async def _validate_navigation_graph(self) -> Dict[str, Any]:
        """Validate the question navigation graph structure."""
        graph_validation = {
            'graph_valid': False,
            'connection_analysis': {},
            'connectivity_stats': {},
            'path_analysis': {},
            'graph_properties': {}
        }
        
        try:
            with open(self.core_data_path, 'r', encoding='utf-8') as f:
                core_data = json.load(f)
            
            questions = core_data.get('questions', [])
            connections = core_data.get('connections', [])
            
            # Build NetworkX graph
            G = nx.DiGraph()
            
            # Add question nodes
            for question in questions:
                q_id = question.get('id')
                if q_id:
                    G.add_node(q_id, **question)
            
            # Add connections
            valid_connections = 0
            invalid_connections = 0
            
            for connection in connections:
                from_q = connection.get('from_question')
                to_q = connection.get('to_question')
                
                if from_q in G.nodes and to_q in G.nodes:
                    G.add_edge(from_q, to_q, **connection)
                    valid_connections += 1
                else:
                    invalid_connections += 1
            
            graph_validation['connection_analysis'] = {
                'total_connections': len(connections),
                'valid_connections': valid_connections,
                'invalid_connections': invalid_connections
            }
            
            # Graph connectivity analysis
            if G.number_of_nodes() > 0:
                graph_validation['connectivity_stats'] = {
                    'nodes': G.number_of_nodes(),
                    'edges': G.number_of_edges(),
                    'is_connected': nx.is_weakly_connected(G),
                    'number_of_components': nx.number_weakly_connected_components(G),
                    'average_degree': sum(dict(G.degree()).values()) / G.number_of_nodes()
                }
                
                # Path analysis
                try:
                    # Sample path lengths between random nodes
                    nodes = list(G.nodes())
                    if len(nodes) > 10:
                        sample_paths = []
                        for i in range(min(100, len(nodes) // 10)):
                            source = nodes[i * 7 % len(nodes)]
                            target = nodes[(i * 11 + 5) % len(nodes)]
                            if source != target:
                                try:
                                    path_length = nx.shortest_path_length(G, source, target)
                                    sample_paths.append(path_length)
                                except nx.NetworkXNoPath:
                                    pass
                        
                        if sample_paths:
                            graph_validation['path_analysis'] = {
                                'sample_paths_analyzed': len(sample_paths),
                                'average_path_length': sum(sample_paths) / len(sample_paths),
                                'max_path_length': max(sample_paths),
                                'min_path_length': min(sample_paths)
                            }
                
                except Exception as e:
                    graph_validation['path_analysis_error'] = str(e)
                
                # Graph properties
                graph_validation['graph_properties'] = {
                    'density': nx.density(G),
                    'is_dag': nx.is_directed_acyclic_graph(G),
                    'number_of_selfloops': nx.number_of_selfloops(G)
                }
                
                graph_validation['graph_valid'] = True
        
        except Exception as e:
            graph_validation['error'] = str(e)
        
        return graph_validation
    
    async def _validate_domain_coverage(self) -> Dict[str, Any]:
        """Validate domain coverage and distribution."""
        domain_validation = {
            'domain_distribution': {},
            'coverage_analysis': {},
            'depth_distribution': {},
            'domain_completeness': {}
        }
        
        try:
            with open(self.core_data_path, 'r', encoding='utf-8') as f:
                core_data = json.load(f)
            
            questions = core_data.get('questions', [])
            
            # Domain distribution
            domain_counts = Counter([q.get('domain') for q in questions if q.get('domain')])
            domain_validation['domain_distribution'] = dict(domain_counts)
            
            # Coverage analysis
            covered_domains = set(domain_counts.keys())
            missing_domains = self.EXPECTED_DOMAIN_NAMES - covered_domains
            extra_domains = covered_domains - self.EXPECTED_DOMAIN_NAMES
            
            domain_validation['coverage_analysis'] = {
                'expected_domains': len(self.EXPECTED_DOMAIN_NAMES),
                'covered_domains': len(covered_domains),
                'missing_domains': list(missing_domains),
                'extra_domains': list(extra_domains),
                'coverage_percentage': (len(covered_domains) / len(self.EXPECTED_DOMAIN_NAMES)) * 100
            }
            
            # Depth distribution by domain
            depth_by_domain = defaultdict(lambda: defaultdict(int))
            for question in questions:
                domain = question.get('domain')
                depth = question.get('depth_level')
                if domain and depth:
                    depth_by_domain[domain][depth] += 1
            
            domain_validation['depth_distribution'] = {
                domain: dict(depths) for domain, depths in depth_by_domain.items()
            }
            
            # Domain completeness (each domain should have questions at all depth levels)
            completeness = {}
            for domain in self.EXPECTED_DOMAIN_NAMES:
                if domain in depth_by_domain:
                    domain_depths = set(depth_by_domain[domain].keys())
                    missing_depths = self.EXPECTED_DEPTH_LEVELS_NAMES - domain_depths
                    completeness[domain] = {
                        'total_questions': sum(depth_by_domain[domain].values()),
                        'depth_levels_covered': len(domain_depths),
                        'missing_depth_levels': list(missing_depths),
                        'is_complete': len(missing_depths) == 0
                    }
                else:
                    completeness[domain] = {
                        'total_questions': 0,
                        'depth_levels_covered': 0,
                        'missing_depth_levels': list(self.EXPECTED_DEPTH_LEVELS_NAMES),
                        'is_complete': False
                    }
            
            domain_validation['domain_completeness'] = completeness
        
        except Exception as e:
            domain_validation['error'] = str(e)
        
        return domain_validation
    
    async def _validate_energy_dynamics(self) -> Dict[str, Any]:
        """Validate energy type distribution and safety rules."""
        energy_validation = {
            'energy_distribution': {},
            'safety_violations': [],
            'transition_analysis': {},
            'balance_assessment': {}
        }
        
        try:
            with open(self.core_data_path, 'r', encoding='utf-8') as f:
                core_data = json.load(f)
            
            questions = core_data.get('questions', [])
            connections = core_data.get('connections', [])
            
            # Energy type distribution
            energy_counts = Counter([q.get('energy_type') for q in questions if q.get('energy_type')])
            energy_validation['energy_distribution'] = dict(energy_counts)
            
            # Build energy transition map
            energy_transitions = defaultdict(lambda: defaultdict(int))
            question_energy_map = {
                q.get('id'): q.get('energy_type') 
                for q in questions if q.get('id') and q.get('energy_type')
            }
            
            for connection in connections:
                from_q = connection.get('from_question')
                to_q = connection.get('to_question')
                
                if from_q in question_energy_map and to_q in question_energy_map:
                    from_energy = question_energy_map[from_q]
                    to_energy = question_energy_map[to_q]
                    energy_transitions[from_energy][to_energy] += 1
            
            energy_validation['transition_analysis'] = {
                energy: dict(transitions) for energy, transitions in energy_transitions.items()
            }
            
            # Safety rule violations (HEAVY → HEAVY should be avoided)
            safety_violations = []
            heavy_to_heavy = energy_transitions.get('HEAVY', {}).get('HEAVY', 0)
            if heavy_to_heavy > 0:
                safety_violations.append({
                    'rule': 'No HEAVY to HEAVY transitions',
                    'violations': heavy_to_heavy,
                    'severity': 'critical'
                })
            
            # Check for adequate HEALING questions after HEAVY
            heavy_questions = [q for q in questions if q.get('energy_type') == 'HEAVY']
            healing_available = 0
            
            for heavy_q in heavy_questions:
                heavy_id = heavy_q.get('id')
                # Check if there are connections to HEALING questions
                healing_connections = [
                    conn for conn in connections
                    if (conn.get('from_question') == heavy_id and 
                        question_energy_map.get(conn.get('to_question')) == 'HEALING')
                ]
                if healing_connections:
                    healing_available += 1
            
            healing_coverage = (healing_available / len(heavy_questions)) * 100 if heavy_questions else 100
            
            if healing_coverage < 80:
                safety_violations.append({
                    'rule': 'HEAVY questions should have HEALING paths',
                    'coverage_percentage': healing_coverage,
                    'severity': 'high'
                })
            
            energy_validation['safety_violations'] = safety_violations
            
            # Balance assessment
            total_questions = len(questions)
            energy_percentages = {
                energy: (count / total_questions) * 100
                for energy, count in energy_counts.items()
            }
            
            # Ideal distribution (rough guidelines)
            ideal_distribution = {
                'OPENING': 15,      # 15%
                'NEUTRAL': 40,      # 40%
                'PROCESSING': 25,   # 25%
                'HEAVY': 10,        # 10%
                'HEALING': 10       # 10%
            }
            
            balance_score = 100
            for energy_type, ideal_pct in ideal_distribution.items():
                actual_pct = energy_percentages.get(energy_type, 0)
                deviation = abs(actual_pct - ideal_pct)
                balance_score -= min(deviation, 20)  # Max 20 point deduction per energy type
            
            energy_validation['balance_assessment'] = {
                'actual_distribution': energy_percentages,
                'ideal_distribution': ideal_distribution,
                'balance_score': max(0, balance_score),
                'recommendations': self._generate_energy_balance_recommendations(
                    energy_percentages, ideal_distribution
                )
            }
        
        except Exception as e:
            energy_validation['error'] = str(e)
        
        return energy_validation
    
    async def _validate_api_integration(self) -> Dict[str, Any]:
        """Validate API integration and accessibility."""
        api_validation = {
            'api_file_exists': False,
            'api_structure': {},
            'import_test': {},
            'method_availability': {}
        }
        
        try:
            # Check API file exists
            api_validation['api_file_exists'] = self.api_path.exists()
            
            if self.api_path.exists():
                # Try to import the API
                try:
                    import sys
                    sys.path.insert(0, str(self.api_path.parent))
                    
                    import core_api
                    
                    api_validation['import_test'] = {'success': True}
                    
                    # Check for expected methods
                    expected_methods = [
                        'get_question_by_id',
                        'get_questions_by_domain',
                        'get_questions_by_depth',
                        'get_connected_questions',
                        'search_questions'
                    ]
                    
                    available_methods = {}
                    for method in expected_methods:
                        available_methods[method] = hasattr(core_api, method)
                    
                    api_validation['method_availability'] = available_methods
                    
                except Exception as e:
                    api_validation['import_test'] = {
                        'success': False,
                        'error': str(e)
                    }
        
        except Exception as e:
            api_validation['error'] = str(e)
        
        return api_validation
    
    async def _validate_metadata_consistency(self) -> Dict[str, Any]:
        """Validate metadata consistency across questions."""
        metadata_validation = {
            'metadata_fields': set(),
            'field_coverage': {},
            'consistency_issues': []
        }
        
        try:
            with open(self.core_data_path, 'r', encoding='utf-8') as f:
                core_data = json.load(f)
            
            questions = core_data.get('questions', [])
            
            # Collect all metadata fields
            all_metadata_fields = set()
            field_counts = defaultdict(int)
            
            for question in questions:
                metadata = question.get('metadata', {})
                if isinstance(metadata, dict):
                    for field in metadata.keys():
                        all_metadata_fields.add(field)
                        field_counts[field] += 1
            
            metadata_validation['metadata_fields'] = list(all_metadata_fields)
            
            # Calculate field coverage
            total_questions = len(questions)
            field_coverage = {
                field: {
                    'count': count,
                    'percentage': (count / total_questions) * 100,
                    'missing_count': total_questions - count
                }
                for field, count in field_counts.items()
            }
            
            metadata_validation['field_coverage'] = field_coverage
            
            # Identify consistency issues
            consistency_issues = []
            
            # Fields that should be in all questions
            critical_fields = ['difficulty', 'estimated_time', 'prerequisites']
            for field in critical_fields:
                if field in field_coverage:
                    coverage_pct = field_coverage[field]['percentage']
                    if coverage_pct < 90:
                        consistency_issues.append({
                            'field': field,
                            'issue': f'Low coverage: {coverage_pct:.1f}%',
                            'severity': 'medium' if coverage_pct > 50 else 'high'
                        })
                else:
                    consistency_issues.append({
                        'field': field,
                        'issue': 'Field missing completely',
                        'severity': 'high'
                    })
            
            metadata_validation['consistency_issues'] = consistency_issues
        
        except Exception as e:
            metadata_validation['error'] = str(e)
        
        return metadata_validation
    
    async def _validate_safety_rules(self) -> Dict[str, Any]:
        """Validate psychological safety rules and guidelines."""
        safety_validation = {
            'energy_safety': {},
            'depth_progression': {},
            'trust_level_controls': {},
            'safety_score': 0.0
        }
        
        try:
            with open(self.core_data_path, 'r', encoding='utf-8') as f:
                core_data = json.load(f)
            
            questions = core_data.get('questions', [])
            connections = core_data.get('connections', [])
            
            # Energy safety analysis (already covered in energy validation)
            # Focus on depth progression safety
            
            # Build question maps
            question_depth_map = {
                q.get('id'): q.get('depth_level') 
                for q in questions if q.get('id') and q.get('depth_level')
            }
            
            # Analyze depth progressions
            unsafe_progressions = 0
            safe_progressions = 0
            
            depth_order = {'SURFACE': 1, 'CONSCIOUS': 2, 'EDGE': 3, 'SHADOW': 4, 'CORE': 5}
            
            for connection in connections:
                from_q = connection.get('from_question')
                to_q = connection.get('to_question')
                
                if from_q in question_depth_map and to_q in question_depth_map:
                    from_depth = question_depth_map[from_q]
                    to_depth = question_depth_map[to_q]
                    
                    from_level = depth_order.get(from_depth, 0)
                    to_level = depth_order.get(to_depth, 0)
                    
                    # Check for unsafe jumps (more than 2 levels)
                    level_jump = abs(to_level - from_level)
                    if level_jump > 2:
                        unsafe_progressions += 1
                    else:
                        safe_progressions += 1
            
            total_progressions = unsafe_progressions + safe_progressions
            safety_percentage = (safe_progressions / total_progressions) * 100 if total_progressions > 0 else 100
            
            safety_validation['depth_progression'] = {
                'total_connections': total_progressions,
                'safe_progressions': safe_progressions,
                'unsafe_progressions': unsafe_progressions,
                'safety_percentage': safety_percentage
            }
            
            # Trust level controls (check if sensitive questions have proper prerequisites)
            shadow_core_questions = [
                q for q in questions 
                if q.get('depth_level') in ['SHADOW', 'CORE']
            ]
            
            protected_questions = 0
            for question in shadow_core_questions:
                metadata = question.get('metadata', {})
                if isinstance(metadata, dict):
                    # Check for trust level requirements or prerequisites
                    if ('trust_level' in metadata or 
                        'prerequisites' in metadata or
                        'min_sessions' in metadata):
                        protected_questions += 1
            
            protection_percentage = (protected_questions / len(shadow_core_questions)) * 100 if shadow_core_questions else 100
            
            safety_validation['trust_level_controls'] = {
                'sensitive_questions': len(shadow_core_questions),
                'protected_questions': protected_questions,
                'protection_percentage': protection_percentage
            }
            
            # Overall safety score
            safety_score = (safety_percentage + protection_percentage) / 2
            safety_validation['safety_score'] = safety_score
        
        except Exception as e:
            safety_validation['error'] = str(e)
        
        return safety_validation
    
    def _generate_energy_balance_recommendations(self, actual: Dict[str, float], ideal: Dict[str, float]) -> List[str]:
        """Generate recommendations for energy balance."""
        recommendations = []
        
        for energy_type, ideal_pct in ideal.items():
            actual_pct = actual.get(energy_type, 0)
            deviation = actual_pct - ideal_pct
            
            if deviation > 10:
                recommendations.append(
                    f"Reduce {energy_type} questions by {deviation:.1f}% (currently {actual_pct:.1f}%, target {ideal_pct:.1f}%)"
                )
            elif deviation < -10:
                recommendations.append(
                    f"Add more {energy_type} questions by {abs(deviation):.1f}% (currently {actual_pct:.1f}%, target {ideal_pct:.1f}%)"
                )
        
        return recommendations
    
    def _calculate_question_health_score(self, validation: Dict[str, Any]) -> float:
        """Calculate overall question system health score."""
        score = 100.0
        
        # Core structure validation
        core_structure = validation.get('core_structure', {})
        if not core_structure.get('structure_valid', False):
            score -= 30
        
        count_validation = core_structure.get('count_validation', {})
        if not count_validation.get('questions_match', True):
            score -= 15
        if not count_validation.get('connections_match', True):
            score -= 10
        
        # Question integrity
        integrity = validation.get('question_integrity', {})
        integrity_pct = integrity.get('integrity_percentage', 100)
        if integrity_pct < 95:
            score -= (100 - integrity_pct) * 0.5  # Scale down the penalty
        
        # Navigation graph
        graph_validation = validation.get('navigation_graph', {})
        if not graph_validation.get('graph_valid', False):
            score -= 20
        
        connectivity = graph_validation.get('connectivity_stats', {})
        if not connectivity.get('is_connected', True):
            score -= 15
        
        # Domain coverage
        domain_validation = validation.get('domain_coverage', {})
        coverage = domain_validation.get('coverage_analysis', {})
        coverage_pct = coverage.get('coverage_percentage', 100)
        if coverage_pct < 100:
            score -= (100 - coverage_pct) * 0.3
        
        # Energy safety
        energy_validation = validation.get('energy_dynamics', {})
        safety_violations = len(energy_validation.get('safety_violations', []))
        score -= safety_violations * 10  # 10 points per violation
        
        # Safety rules
        safety_validation = validation.get('safety_rules', {})
        safety_score = safety_validation.get('safety_score', 100)
        score = (score + safety_score) / 2  # Average with safety score
        
        return max(0.0, score)
    
    def _extract_question_issues(self, validation: Dict[str, Any]) -> List[Dict[str, str]]:
        """Extract issues from question validation."""
        issues = []
        
        # Structure issues
        core_structure = validation.get('core_structure', {})
        if not core_structure.get('structure_valid', False):
            issues.append({
                'severity': 'critical',
                'component': 'question_core',
                'issue': 'Core structure invalid',
                'recommendation': 'Fix JSON structure and required fields'
            })
        
        # Count mismatches
        count_validation = core_structure.get('count_validation', {})
        if not count_validation.get('questions_match', True):
            expected = count_validation.get('questions_expected', 0)
            actual = count_validation.get('questions_actual', 0)
            issues.append({
                'severity': 'high',
                'component': 'question_count',
                'issue': f'Question count mismatch: expected {expected}, got {actual}',
                'recommendation': 'Review and correct question count'
            })
        
        # Integrity issues
        integrity = validation.get('question_integrity', {})
        invalid_count = len(integrity.get('invalid_questions', []))
        if invalid_count > 0:
            issues.append({
                'severity': 'high',
                'component': 'question_integrity',
                'issue': f'{invalid_count} invalid questions found',
                'recommendation': 'Fix question validation errors'
            })
        
        # Safety violations
        energy_validation = validation.get('energy_dynamics', {})
        safety_violations = energy_validation.get('safety_violations', [])
        for violation in safety_violations:
            issues.append({
                'severity': violation.get('severity', 'medium'),
                'component': 'energy_safety',
                'issue': violation.get('rule', 'Safety rule violation'),
                'recommendation': 'Review and fix energy transition safety'
            })
        
        return issues
    
    def _generate_question_recommendations(self, validation: Dict[str, Any]) -> List[Dict[str, str]]:
        """Generate question system recommendations."""
        recommendations = []
        
        # Integrity improvements
        integrity = validation.get('question_integrity', {})
        if integrity.get('integrity_percentage', 100) < 95:
            recommendations.append({
                'priority': 'high',
                'action': 'Fix question integrity issues',
                'description': f'Only {integrity.get("integrity_percentage", 0):.1f}% questions are valid',
                'effort': '4-8 hours'
            })
        
        # Domain coverage
        domain_validation = validation.get('domain_coverage', {})
        coverage = domain_validation.get('coverage_analysis', {})
        missing_domains = coverage.get('missing_domains', [])
        if missing_domains:
            recommendations.append({
                'priority': 'medium',
                'action': f'Add questions for missing domains: {", ".join(missing_domains)}',
                'description': 'Improve domain coverage',
                'effort': '8-16 hours'
            })
        
        # Energy balance
        energy_validation = validation.get('energy_dynamics', {})
        balance = energy_validation.get('balance_assessment', {})
        if balance.get('balance_score', 100) < 80:
            recommendations.append({
                'priority': 'medium',
                'action': 'Rebalance energy type distribution',
                'description': f'Energy balance score: {balance.get("balance_score", 0):.1f}%',
                'effort': '6-12 hours'
            })
        
        # API integration
        api_validation = validation.get('api_integration', {})
        if not api_validation.get('api_file_exists', False):
            recommendations.append({
                'priority': 'high',
                'action': 'Create question core API',
                'description': 'API file missing for integration',
                'effort': '2-4 hours'
            })
        
        return recommendations
    
    async def debug_specific_issue(self, issue_type: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Debug specific question-related issues."""
        debug_result = {
            'issue_type': issue_type,
            'timestamp': datetime.now().isoformat(),
            'analysis': {},
            'recommendations': []
        }
        
        if issue_type == 'question_navigation_broken':
            # Analyze navigation issues
            try:
                with open(self.core_data_path, 'r', encoding='utf-8') as f:
                    core_data = json.load(f)
                
                connections = core_data.get('connections', [])
                questions = core_data.get('questions', [])
                question_ids = {q.get('id') for q in questions if q.get('id')}
                
                broken_connections = [
                    conn for conn in connections
                    if (conn.get('from_question') not in question_ids or
                        conn.get('to_question') not in question_ids)
                ]
                
                debug_result['analysis'] = {
                    'total_connections': len(connections),
                    'broken_connections': len(broken_connections),
                    'broken_connection_details': broken_connections[:10]  # First 10
                }
                
                if broken_connections:
                    debug_result['recommendations'] = [
                        {
                            'action': 'Fix broken question connections',
                            'description': f'{len(broken_connections)} connections reference missing questions',
                            'priority': 'high'
                        }
                    ]
            
            except Exception as e:
                debug_result['analysis']['error'] = str(e)
        
        elif issue_type == 'question_energy_imbalance':
            # Analyze energy distribution issues
            energy_validation = await self._validate_energy_dynamics()
            debug_result['analysis'] = energy_validation
            debug_result['recommendations'] = energy_validation.get('balance_assessment', {}).get('recommendations', [])
        
        elif issue_type == 'question_domain_gaps':
            # Analyze domain coverage gaps
            domain_validation = await self._validate_domain_coverage()
            debug_result['analysis'] = domain_validation
            
            missing_domains = domain_validation.get('coverage_analysis', {}).get('missing_domains', [])
            incomplete_domains = [
                domain for domain, completeness in domain_validation.get('domain_completeness', {}).items()
                if not completeness.get('is_complete', True)
            ]
            
            recommendations = []
            if missing_domains:
                recommendations.append({
                    'action': f'Add questions for domains: {", ".join(missing_domains)}',
                    'priority': 'high'
                })
            
            if incomplete_domains:
                recommendations.append({
                    'action': f'Complete depth coverage for: {", ".join(incomplete_domains)}',
                    'priority': 'medium'
                })
            
            debug_result['recommendations'] = recommendations
        
        return debug_result