"""
🔧 Workflow Optimizer Component
Development workflow analysis and optimization recommendations.
"""

import asyncio
import subprocess
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional
import os


class WorkflowOptimizer:
    """
    Analyzes and optimizes development workflows for the Selfology project.
    Focuses on development efficiency, CI/CD optimization, and process improvements.
    """
    
    def __init__(self):
        self.analysis_start = datetime.now()
        self.project_root = Path.cwd()
    
    async def analyze_workflow(self) -> Dict[str, Any]:
        """
        Comprehensive development workflow analysis.
        """
        print("    🔍 Analyzing development workflow...")
        
        workflow_analysis = {
            'timestamp': datetime.now().isoformat(),
            'development_environment': await self._analyze_dev_environment(),
            'code_quality_tools': await self._analyze_code_quality(),
            'testing_workflow': await self._analyze_testing_workflow(),
            'deployment_process': await self._analyze_deployment_process(),
            'monitoring_integration': await self._analyze_monitoring_integration(),
            'documentation_status': await self._analyze_documentation(),
            'automation_opportunities': await self._identify_automation_opportunities(),
            'efficiency_metrics': await self._calculate_efficiency_metrics(),
            'recommendations': [],
            'workflow_score': 0.0,
            'issues': []
        }
        
        # Calculate overall workflow efficiency score
        workflow_analysis['workflow_score'] = self._calculate_workflow_score(workflow_analysis)
        workflow_analysis['issues'] = self._extract_workflow_issues(workflow_analysis)
        workflow_analysis['recommendations'] = self._generate_workflow_recommendations(workflow_analysis)
        
        return workflow_analysis
    
    async def _analyze_dev_environment(self) -> Dict[str, Any]:
        """Analyze development environment setup."""
        dev_env = {
            'python_environment': await self._check_python_environment(),
            'dependency_management': await self._check_dependency_management(),
            'environment_configuration': await self._check_environment_config(),
            'ide_integration': await self._check_ide_integration()
        }
        
        return dev_env
    
    async def _check_python_environment(self) -> Dict[str, Any]:
        """Check Python environment setup."""
        python_env = {
            'virtual_environment': {'status': 'unknown'},
            'python_version': {'status': 'unknown'},
            'package_management': {'status': 'unknown'}
        }
        
        try:
            # Check if virtual environment is active
            virtual_env = os.environ.get('VIRTUAL_ENV')
            if virtual_env:
                python_env['virtual_environment'] = {
                    'status': 'active',
                    'path': virtual_env,
                    'name': Path(virtual_env).name
                }
            else:
                # Check if venv directory exists
                if Path('venv').exists():
                    python_env['virtual_environment'] = {
                        'status': 'available_not_active',
                        'path': str(Path('venv').absolute())
                    }
                else:
                    python_env['virtual_environment'] = {
                        'status': 'not_found'
                    }
            
            # Check Python version
            result = subprocess.run(['python', '--version'], capture_output=True, text=True)
            if result.returncode == 0:
                version = result.stdout.strip()
                python_env['python_version'] = {
                    'status': 'detected',
                    'version': version,
                    'compatible': '3.11' in version or '3.12' in version  # Expected versions
                }
            
            # Check package management
            package_files = {
                'requirements.txt': Path('requirements.txt').exists(),
                'pyproject.toml': Path('pyproject.toml').exists(),
                'setup.py': Path('setup.py').exists(),
                'Pipfile': Path('Pipfile').exists()
            }
            
            python_env['package_management'] = {
                'status': 'configured' if any(package_files.values()) else 'missing',
                'files_found': {k: v for k, v in package_files.items() if v}
            }
        
        except Exception as e:
            python_env['error'] = str(e)
        
        return python_env
    
    async def _check_dependency_management(self) -> Dict[str, Any]:
        """Check dependency management setup."""
        dep_management = {
            'dependency_files': {'status': 'unknown'},
            'dependency_sync': {'status': 'unknown'},
            'security_scanning': {'status': 'unknown'}
        }
        
        try:
            # Check for dependency files
            dep_files = [
                'requirements.txt',
                'requirements-monitoring.txt',
                'pyproject.toml'
            ]
            
            found_files = []
            for dep_file in dep_files:
                if Path(dep_file).exists():
                    found_files.append(dep_file)
            
            dep_management['dependency_files'] = {
                'status': 'complete' if len(found_files) >= 2 else 'partial',
                'found_files': found_files,
                'missing_files': [f for f in dep_files if f not in found_files]
            }
            
            # Check if dependencies are in sync
            if Path('requirements.txt').exists() and Path('pyproject.toml').exists():
                # Would need to parse both files to check sync
                dep_management['dependency_sync'] = {
                    'status': 'needs_verification',
                    'note': 'Manual verification required'
                }
            
            # Check for security scanning tools
            security_tools = ['safety', 'pip-audit', 'bandit']
            available_tools = []
            
            for tool in security_tools:
                result = subprocess.run(['which', tool], capture_output=True)
                if result.returncode == 0:
                    available_tools.append(tool)
            
            dep_management['security_scanning'] = {
                'status': 'configured' if available_tools else 'missing',
                'available_tools': available_tools
            }
        
        except Exception as e:
            dep_management['error'] = str(e)
        
        return dep_management
    
    async def _check_environment_config(self) -> Dict[str, Any]:
        """Check environment configuration."""
        env_config = {
            'env_files': {'status': 'unknown'},
            'env_security': {'status': 'unknown'},
            'config_management': {'status': 'unknown'}
        }
        
        try:
            # Check for environment files
            env_files = ['.env', '.env.example', '.env.tokens']
            found_env_files = []
            
            for env_file in env_files:
                if Path(env_file).exists():
                    found_env_files.append(env_file)
            
            env_config['env_files'] = {
                'status': 'complete' if '.env' in found_env_files and '.env.example' in found_env_files else 'incomplete',
                'found_files': found_env_files
            }
            
            # Check .env security
            if Path('.env').exists():
                import stat
                env_stat = Path('.env').stat()
                is_world_readable = bool(env_stat.st_mode & stat.S_IROTH)
                
                env_config['env_security'] = {
                    'status': 'secure' if not is_world_readable else 'insecure',
                    'world_readable': is_world_readable,
                    'permissions': oct(env_stat.st_mode)
                }
            
            # Check config management
            config_files = [
                'selfology_bot/core/config.py',
                'scripts/setup.py'
            ]
            
            config_structure = []
            for config_file in config_files:
                if Path(config_file).exists():
                    config_structure.append(config_file)
            
            env_config['config_management'] = {
                'status': 'structured' if config_structure else 'basic',
                'config_files': config_structure
            }
        
        except Exception as e:
            env_config['error'] = str(e)
        
        return env_config
    
    async def _check_ide_integration(self) -> Dict[str, Any]:
        """Check IDE integration and development tools."""
        ide_integration = {
            'vscode_config': {'status': 'unknown'},
            'git_integration': {'status': 'unknown'},
            'debugging_setup': {'status': 'unknown'}
        }
        
        try:
            # Check VS Code configuration
            vscode_dir = Path('.vscode')
            if vscode_dir.exists():
                vscode_files = list(vscode_dir.glob('*.json'))
                ide_integration['vscode_config'] = {
                    'status': 'configured',
                    'config_files': [f.name for f in vscode_files]
                }
            else:
                ide_integration['vscode_config'] = {'status': 'not_configured'}
            
            # Check Git integration
            git_dir = Path('.git')
            if git_dir.exists():
                # Check for Git hooks, .gitignore, etc.
                gitignore = Path('.gitignore').exists()
                git_hooks = list((git_dir / 'hooks').glob('*')) if (git_dir / 'hooks').exists() else []
                
                ide_integration['git_integration'] = {
                    'status': 'configured',
                    'gitignore': gitignore,
                    'hooks': len(git_hooks),
                    'hook_files': [h.name for h in git_hooks if not h.name.endswith('.sample')]
                }
            else:
                ide_integration['git_integration'] = {'status': 'not_git_repo'}
            
            # Check debugging configuration
            debug_configs = [
                '.vscode/launch.json',
                'pyproject.toml',  # May contain debug configs
                'pytest.ini'
            ]
            
            debug_files = [f for f in debug_configs if Path(f).exists()]
            ide_integration['debugging_setup'] = {
                'status': 'configured' if debug_files else 'basic',
                'config_files': debug_files
            }
        
        except Exception as e:
            ide_integration['error'] = str(e)
        
        return ide_integration
    
    async def _analyze_code_quality(self) -> Dict[str, Any]:
        """Analyze code quality tools and processes."""
        code_quality = {
            'linting_tools': await self._check_linting_tools(),
            'formatting_tools': await self._check_formatting_tools(),
            'type_checking': await self._check_type_checking(),
            'code_analysis': await self._check_static_analysis()
        }
        
        return code_quality
    
    async def _check_linting_tools(self) -> Dict[str, Any]:
        """Check linting tools configuration."""
        linting = {
            'available_linters': [],
            'configuration': {'status': 'unknown'},
            'integration': {'status': 'unknown'}
        }
        
        try:
            # Check for common Python linters
            linters = ['ruff', 'flake8', 'pylint', 'pycodestyle']
            available_linters = []
            
            for linter in linters:
                try:
                    result = subprocess.run([linter, '--version'], capture_output=True, timeout=5)
                    if result.returncode == 0:
                        available_linters.append({
                            'name': linter,
                            'version': result.stdout.decode().strip()
                        })
                except (FileNotFoundError, subprocess.TimeoutExpired):
                    pass
            
            linting['available_linters'] = available_linters
            
            # Check for linter configuration files
            config_files = [
                '.ruff.toml',
                'ruff.toml',
                'setup.cfg',
                '.flake8',
                'pylintrc',
                'pyproject.toml'
            ]
            
            found_configs = [f for f in config_files if Path(f).exists()]
            linting['configuration'] = {
                'status': 'configured' if found_configs else 'default',
                'config_files': found_configs
            }
            
            # Check pyproject.toml for linter configuration
            if Path('pyproject.toml').exists():
                try:
                    import tomli
                    with open('pyproject.toml', 'rb') as f:
                        toml_data = tomli.load(f)
                    
                    has_ruff = 'tool' in toml_data and 'ruff' in toml_data['tool']
                    has_pylint = 'tool' in toml_data and 'pylint' in toml_data['tool']
                    
                    linting['integration'] = {
                        'status': 'integrated' if has_ruff or has_pylint else 'basic',
                        'pyproject_integration': {
                            'ruff': has_ruff,
                            'pylint': has_pylint
                        }
                    }
                except ImportError:
                    linting['integration'] = {
                        'status': 'unknown',
                        'error': 'tomli not available for parsing'
                    }
        
        except Exception as e:
            linting['error'] = str(e)
        
        return linting
    
    async def _check_formatting_tools(self) -> Dict[str, Any]:
        """Check code formatting tools."""
        formatting = {
            'available_formatters': [],
            'configuration': {'status': 'unknown'},
            'auto_formatting': {'status': 'unknown'}
        }
        
        try:
            # Check for Python formatters
            formatters = ['black', 'autopep8', 'isort']
            available_formatters = []
            
            for formatter in formatters:
                try:
                    result = subprocess.run([formatter, '--version'], capture_output=True, timeout=5)
                    if result.returncode == 0:
                        available_formatters.append({
                            'name': formatter,
                            'version': result.stdout.decode().strip()
                        })
                except (FileNotFoundError, subprocess.TimeoutExpired):
                    pass
            
            formatting['available_formatters'] = available_formatters
            
            # Check for formatter configuration in pyproject.toml
            if Path('pyproject.toml').exists():
                try:
                    import tomli
                    with open('pyproject.toml', 'rb') as f:
                        toml_data = tomli.load(f)
                    
                    tool_config = toml_data.get('tool', {})
                    has_black = 'black' in tool_config
                    has_isort = 'isort' in tool_config
                    
                    formatting['configuration'] = {
                        'status': 'configured' if has_black or has_isort else 'default',
                        'black': has_black,
                        'isort': has_isort
                    }
                except ImportError:
                    pass
            
            # Check for auto-formatting setup (pre-commit, IDE config)
            precommit_file = Path('.pre-commit-config.yaml')
            vscode_settings = Path('.vscode/settings.json')
            
            auto_format_indicators = []
            if precommit_file.exists():
                auto_format_indicators.append('pre-commit')
            if vscode_settings.exists():
                auto_format_indicators.append('vscode')
            
            formatting['auto_formatting'] = {
                'status': 'configured' if auto_format_indicators else 'manual',
                'methods': auto_format_indicators
            }
        
        except Exception as e:
            formatting['error'] = str(e)
        
        return formatting
    
    async def _check_type_checking(self) -> Dict[str, Any]:
        """Check type checking setup."""
        type_checking = {
            'type_checkers': [],
            'type_annotations': {'status': 'unknown'},
            'configuration': {'status': 'unknown'}
        }
        
        try:
            # Check for type checkers
            checkers = ['mypy', 'pyright', 'pyre']
            available_checkers = []
            
            for checker in checkers:
                try:
                    result = subprocess.run([checker, '--version'], capture_output=True, timeout=5)
                    if result.returncode == 0:
                        available_checkers.append({
                            'name': checker,
                            'version': result.stdout.decode().strip()
                        })
                except (FileNotFoundError, subprocess.TimeoutExpired):
                    pass
            
            type_checking['type_checkers'] = available_checkers
            
            # Check for type checking configuration
            config_files = ['mypy.ini', 'pyproject.toml', 'setup.cfg']
            type_config_found = False
            
            for config_file in config_files:
                if Path(config_file).exists():
                    if config_file == 'pyproject.toml':
                        try:
                            import tomli
                            with open(config_file, 'rb') as f:
                                toml_data = tomli.load(f)
                            if 'mypy' in toml_data.get('tool', {}):
                                type_config_found = True
                        except ImportError:
                            pass
                    else:
                        type_config_found = True
            
            type_checking['configuration'] = {
                'status': 'configured' if type_config_found else 'default'
            }
            
            # Analyze type annotation usage (simplified check)
            python_files = list(Path('.').rglob('*.py'))
            if python_files:
                # Sample a few files to check for type annotations
                sample_files = python_files[:5]
                annotated_files = 0
                
                for py_file in sample_files:
                    try:
                        with open(py_file, 'r', encoding='utf-8') as f:
                            content = f.read()
                        
                        # Simple check for type annotations
                        if (': ' in content and ('str' in content or 'int' in content or 'Dict' in content or 'List' in content or 'Optional' in content)):
                            annotated_files += 1
                    except:
                        pass
                
                annotation_percentage = (annotated_files / len(sample_files)) * 100
                type_checking['type_annotations'] = {
                    'status': 'extensive' if annotation_percentage > 80 else 'partial' if annotation_percentage > 20 else 'minimal',
                    'estimated_coverage': annotation_percentage,
                    'sample_size': len(sample_files)
                }
        
        except Exception as e:
            type_checking['error'] = str(e)
        
        return type_checking
    
    async def _check_static_analysis(self) -> Dict[str, Any]:
        """Check static analysis tools."""
        static_analysis = {
            'security_scanners': [],
            'complexity_analyzers': [],
            'dependency_scanners': []
        }
        
        try:
            # Check for security scanners
            security_tools = ['bandit', 'safety', 'pip-audit']
            for tool in security_tools:
                try:
                    result = subprocess.run([tool, '--version'], capture_output=True, timeout=5)
                    if result.returncode == 0:
                        static_analysis['security_scanners'].append({
                            'name': tool,
                            'version': result.stdout.decode().strip()
                        })
                except (FileNotFoundError, subprocess.TimeoutExpired):
                    pass
            
            # Check for complexity analyzers
            complexity_tools = ['radon', 'xenon']
            for tool in complexity_tools:
                try:
                    result = subprocess.run([tool, '--version'], capture_output=True, timeout=5)
                    if result.returncode == 0:
                        static_analysis['complexity_analyzers'].append({
                            'name': tool,
                            'version': result.stdout.decode().strip()
                        })
                except (FileNotFoundError, subprocess.TimeoutExpired):
                    pass
        
        except Exception as e:
            static_analysis['error'] = str(e)
        
        return static_analysis
    
    async def _analyze_testing_workflow(self) -> Dict[str, Any]:
        """Analyze testing workflow and setup."""
        testing = {
            'test_framework': await self._check_test_framework(),
            'test_coverage': await self._check_test_coverage(),
            'test_automation': await self._check_test_automation(),
            'test_organization': await self._check_test_organization()
        }
        
        return testing
    
    async def _check_test_framework(self) -> Dict[str, Any]:
        """Check testing framework setup."""
        test_framework = {
            'frameworks': [],
            'configuration': {'status': 'unknown'},
            'test_discovery': {'status': 'unknown'}
        }
        
        try:
            # Check for testing frameworks
            frameworks = ['pytest', 'unittest', 'nose2']
            available_frameworks = []
            
            for framework in frameworks:
                try:
                    result = subprocess.run([framework, '--version'], capture_output=True, timeout=5)
                    if result.returncode == 0:
                        available_frameworks.append({
                            'name': framework,
                            'version': result.stdout.decode().strip()
                        })
                except (FileNotFoundError, subprocess.TimeoutExpired):
                    pass
            
            test_framework['frameworks'] = available_frameworks
            
            # Check for test configuration
            config_files = ['pytest.ini', 'pyproject.toml', 'setup.cfg', 'tox.ini']
            test_configs = []
            
            for config_file in config_files:
                if Path(config_file).exists():
                    test_configs.append(config_file)
            
            test_framework['configuration'] = {
                'status': 'configured' if test_configs else 'default',
                'config_files': test_configs
            }
            
            # Check test discovery
            test_directories = ['tests', 'test', 'testing']
            test_dirs_found = [d for d in test_directories if Path(d).exists()]
            
            test_framework['test_discovery'] = {
                'status': 'structured' if test_dirs_found else 'scattered',
                'test_directories': test_dirs_found
            }
        
        except Exception as e:
            test_framework['error'] = str(e)
        
        return test_framework
    
    async def _check_test_coverage(self) -> Dict[str, Any]:
        """Check test coverage tools and metrics."""
        coverage = {
            'coverage_tools': [],
            'coverage_config': {'status': 'unknown'},
            'coverage_reporting': {'status': 'unknown'}
        }
        
        try:
            # Check for coverage tools
            coverage_tools = ['coverage', 'pytest-cov']
            available_tools = []
            
            for tool in coverage_tools:
                try:
                    if tool == 'pytest-cov':
                        # Check if pytest-cov is installed
                        result = subprocess.run(['python', '-c', 'import pytest_cov'], capture_output=True, timeout=5)
                        if result.returncode == 0:
                            available_tools.append({'name': tool, 'type': 'plugin'})
                    else:
                        result = subprocess.run([tool, '--version'], capture_output=True, timeout=5)
                        if result.returncode == 0:
                            available_tools.append({
                                'name': tool,
                                'version': result.stdout.decode().strip()
                            })
                except (FileNotFoundError, subprocess.TimeoutExpired):
                    pass
            
            coverage['coverage_tools'] = available_tools
            
            # Check for coverage configuration
            coverage_files = ['.coveragerc', 'pyproject.toml', 'setup.cfg']
            coverage_configs = []
            
            for config_file in coverage_files:
                if Path(config_file).exists():
                    coverage_configs.append(config_file)
            
            coverage['coverage_config'] = {
                'status': 'configured' if coverage_configs else 'default',
                'config_files': coverage_configs
            }
            
            # Check for coverage reporting
            coverage_reports = ['htmlcov', 'coverage.xml', '.coverage']
            report_files = [f for f in coverage_reports if Path(f).exists()]
            
            coverage['coverage_reporting'] = {
                'status': 'active' if report_files else 'not_generated',
                'report_files': report_files
            }
        
        except Exception as e:
            coverage['error'] = str(e)
        
        return coverage
    
    async def _check_test_automation(self) -> Dict[str, Any]:
        """Check test automation setup."""
        automation = {
            'ci_integration': {'status': 'unknown'},
            'pre_commit_testing': {'status': 'unknown'},
            'automated_test_runs': {'status': 'unknown'}
        }
        
        try:
            # Check for CI configuration
            ci_files = [
                '.github/workflows',
                '.gitlab-ci.yml',
                'Jenkinsfile',
                '.travis.yml',
                'azure-pipelines.yml'
            ]
            
            ci_configs = []
            for ci_file in ci_files:
                ci_path = Path(ci_file)
                if ci_path.exists():
                    if ci_path.is_dir():
                        workflow_files = list(ci_path.glob('*.yml')) + list(ci_path.glob('*.yaml'))
                        if workflow_files:
                            ci_configs.append({
                                'type': 'github_actions',
                                'files': [f.name for f in workflow_files]
                            })
                    else:
                        ci_configs.append({
                            'type': ci_file.replace('.', '').replace('/', '_'),
                            'file': ci_file
                        })
            
            automation['ci_integration'] = {
                'status': 'configured' if ci_configs else 'not_configured',
                'configurations': ci_configs
            }
            
            # Check for pre-commit hooks
            precommit_file = Path('.pre-commit-config.yaml')
            if precommit_file.exists():
                automation['pre_commit_testing'] = {'status': 'configured'}
            else:
                automation['pre_commit_testing'] = {'status': 'not_configured'}
            
            # Check for test automation scripts
            script_files = [
                'scripts/test.py',
                'scripts/run_tests.py',
                'test.sh',
                'run_tests.sh'
            ]
            
            test_scripts = [s for s in script_files if Path(s).exists()]
            automation['automated_test_runs'] = {
                'status': 'configured' if test_scripts else 'manual',
                'scripts': test_scripts
            }
        
        except Exception as e:
            automation['error'] = str(e)
        
        return automation
    
    async def _check_test_organization(self) -> Dict[str, Any]:
        """Check test organization and structure."""
        organization = {
            'test_structure': {'status': 'unknown'},
            'test_naming': {'status': 'unknown'},
            'test_categories': {'status': 'unknown'}
        }
        
        try:
            # Analyze test directory structure
            test_dirs = ['tests', 'test', 'testing']
            test_structure = {}
            
            for test_dir in test_dirs:
                test_path = Path(test_dir)
                if test_path.exists():
                    # Count test files
                    test_files = list(test_path.rglob('test_*.py')) + list(test_path.rglob('*_test.py'))
                    test_structure[test_dir] = {
                        'test_files': len(test_files),
                        'subdirectories': len([d for d in test_path.iterdir() if d.is_dir()]),
                        'sample_files': [f.name for f in test_files[:5]]  # First 5 as sample
                    }
            
            organization['test_structure'] = {
                'status': 'organized' if test_structure else 'unstructured',
                'structure': test_structure
            }
            
            # Analyze test naming conventions
            all_test_files = []
            for test_dir in test_dirs:
                test_path = Path(test_dir)
                if test_path.exists():
                    all_test_files.extend(test_path.rglob('*.py'))
            
            if all_test_files:
                naming_patterns = {
                    'test_prefix': sum(1 for f in all_test_files if f.name.startswith('test_')),
                    'test_suffix': sum(1 for f in all_test_files if f.name.endswith('_test.py')),
                    'other': sum(1 for f in all_test_files if not (f.name.startswith('test_') or f.name.endswith('_test.py')))
                }
                
                total_files = len(all_test_files)
                consistent_naming = (naming_patterns['test_prefix'] / total_files) > 0.8 or (naming_patterns['test_suffix'] / total_files) > 0.8
                
                organization['test_naming'] = {
                    'status': 'consistent' if consistent_naming else 'inconsistent',
                    'patterns': naming_patterns,
                    'total_files': total_files
                }
        
        except Exception as e:
            organization['error'] = str(e)
        
        return organization
    
    async def _analyze_deployment_process(self) -> Dict[str, Any]:
        """Analyze deployment process and configuration."""
        deployment = {
            'containerization': await self._check_containerization(),
            'deployment_config': await self._check_deployment_config(),
            'environment_management': await self._check_environment_management(),
            'monitoring_integration': await self._check_deployment_monitoring()
        }
        
        return deployment
    
    async def _check_containerization(self) -> Dict[str, Any]:
        """Check containerization setup."""
        containerization = {
            'docker_setup': {'status': 'unknown'},
            'docker_compose': {'status': 'unknown'},
            'optimization': {'status': 'unknown'}
        }
        
        try:
            # Check for Docker files
            docker_files = ['Dockerfile', 'Dockerfile.new', 'Dockerfile.test']
            found_dockerfiles = [f for f in docker_files if Path(f).exists()]
            
            if found_dockerfiles:
                containerization['docker_setup'] = {
                    'status': 'configured',
                    'dockerfiles': found_dockerfiles
                }
                
                # Check Docker Compose files
                compose_files = []
                compose_patterns = ['docker-compose*.yml', 'docker-compose*.yaml']
                
                for pattern in compose_patterns:
                    compose_files.extend(Path('.').glob(pattern))
                
                if compose_files:
                    containerization['docker_compose'] = {
                        'status': 'configured',
                        'compose_files': [f.name for f in compose_files]
                    }
                else:
                    containerization['docker_compose'] = {'status': 'missing'}
                
                # Basic optimization check (multi-stage builds, .dockerignore)
                dockerignore = Path('.dockerignore').exists()
                
                # Check for multi-stage builds in main Dockerfile
                multistage = False
                if Path('Dockerfile').exists():
                    with open('Dockerfile', 'r') as f:
                        dockerfile_content = f.read()
                    multistage = 'FROM' in dockerfile_content and dockerfile_content.count('FROM') > 1
                
                containerization['optimization'] = {
                    'status': 'optimized' if dockerignore and multistage else 'basic',
                    'dockerignore': dockerignore,
                    'multistage_build': multistage
                }
            else:
                containerization['docker_setup'] = {'status': 'not_configured'}
        
        except Exception as e:
            containerization['error'] = str(e)
        
        return containerization
    
    async def _check_deployment_config(self) -> Dict[str, Any]:
        """Check deployment configuration."""
        deployment_config = {
            'deployment_scripts': {'status': 'unknown'},
            'infrastructure_as_code': {'status': 'unknown'},
            'deployment_automation': {'status': 'unknown'}
        }
        
        try:
            # Check for deployment scripts
            deployment_scripts = [
                'scripts/deploy.py',
                'scripts/deploy.sh',
                'deploy.py',
                'deploy.sh'
            ]
            
            found_scripts = [s for s in deployment_scripts if Path(s).exists()]
            deployment_config['deployment_scripts'] = {
                'status': 'configured' if found_scripts else 'missing',
                'scripts': found_scripts
            }
            
            # Check for IaC files
            iac_files = [
                'terraform/',
                'ansible/',
                'kubernetes/',
                'helm/',
                '*.tf',
                '*.yml',
                '*.yaml'
            ]
            
            iac_found = []
            for iac_pattern in iac_files:
                if '/' in iac_pattern:
                    if Path(iac_pattern.rstrip('/')).exists():
                        iac_found.append(iac_pattern)
                else:
                    matches = list(Path('.').glob(iac_pattern))
                    if matches:
                        iac_found.extend([m.name for m in matches[:3]])  # Limit to 3 examples
            
            deployment_config['infrastructure_as_code'] = {
                'status': 'configured' if iac_found else 'missing',
                'files_found': iac_found
            }
        
        except Exception as e:
            deployment_config['error'] = str(e)
        
        return deployment_config
    
    async def _check_environment_management(self) -> Dict[str, Any]:
        """Check environment management for deployments."""
        env_management = {
            'environment_configs': {'status': 'unknown'},
            'secrets_management': {'status': 'unknown'},
            'environment_isolation': {'status': 'unknown'}
        }
        
        try:
            # Check for environment-specific configs
            env_configs = [
                '.env.development',
                '.env.production',
                '.env.staging',
                'config/development.py',
                'config/production.py'
            ]
            
            found_env_configs = [c for c in env_configs if Path(c).exists()]
            env_management['environment_configs'] = {
                'status': 'configured' if found_env_configs else 'basic',
                'config_files': found_env_configs
            }
            
            # Check secrets management
            secrets_indicators = [
                'vault/',
                'secrets/',
                '.env.vault',
                'docker-compose.override.yml'
            ]
            
            secrets_found = [s for s in secrets_indicators if Path(s).exists()]
            env_management['secrets_management'] = {
                'status': 'configured' if secrets_found else 'basic',
                'methods': secrets_found
            }
        
        except Exception as e:
            env_management['error'] = str(e)
        
        return env_management
    
    async def _check_deployment_monitoring(self) -> Dict[str, Any]:
        """Check deployment monitoring integration."""
        monitoring = {
            'health_checks': {'status': 'unknown'},
            'logging_integration': {'status': 'unknown'},
            'metrics_collection': {'status': 'unknown'}
        }
        
        # This would check integration with existing monitoring systems
        monitoring['status'] = 'delegated_to_monitoring_analysis'
        
        return monitoring
    
    async def _analyze_monitoring_integration(self) -> Dict[str, Any]:
        """Analyze monitoring system integration with development workflow."""
        monitoring_integration = {
            'development_monitoring': {'status': 'unknown'},
            'alerting_integration': {'status': 'unknown'},
            'debugging_integration': {'status': 'unknown'}
        }
        
        # This would be implemented based on the existing monitoring system
        monitoring_integration['status'] = 'delegated_to_monitoring_system'
        
        return monitoring_integration
    
    async def _analyze_documentation(self) -> Dict[str, Any]:
        """Analyze documentation status and quality."""
        documentation = {
            'readme_status': await self._check_readme(),
            'code_documentation': await self._check_code_docs(),
            'api_documentation': await self._check_api_docs(),
            'developer_docs': await self._check_developer_docs()
        }
        
        return documentation
    
    async def _check_readme(self) -> Dict[str, Any]:
        """Check README file quality."""
        readme_status = {
            'exists': False,
            'completeness': {'status': 'unknown'},
            'sections': []
        }
        
        try:
            readme_files = ['README.md', 'README.rst', 'README.txt', 'readme.md']
            readme_file = None
            
            for rf in readme_files:
                if Path(rf).exists():
                    readme_file = rf
                    break
            
            if readme_file:
                readme_status['exists'] = True
                
                with open(readme_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Check for common sections
                sections = []
                common_sections = [
                    ('# ', 'Main Title'),
                    ('## Installation', 'Installation'),
                    ('## Usage', 'Usage'),
                    ('## API', 'API Documentation'),
                    ('## Development', 'Development'),
                    ('## Contributing', 'Contributing'),
                    ('## License', 'License')
                ]
                
                for section_marker, section_name in common_sections:
                    if section_marker.lower() in content.lower():
                        sections.append(section_name)
                
                readme_status['sections'] = sections
                readme_status['completeness'] = {
                    'status': 'comprehensive' if len(sections) > 5 else 'basic' if len(sections) > 2 else 'minimal',
                    'section_count': len(sections),
                    'content_length': len(content)
                }
            else:
                readme_status['exists'] = False
        
        except Exception as e:
            readme_status['error'] = str(e)
        
        return readme_status
    
    async def _check_code_docs(self) -> Dict[str, Any]:
        """Check code documentation (docstrings, comments)."""
        code_docs = {
            'docstring_coverage': {'status': 'unknown'},
            'comment_quality': {'status': 'unknown'},
            'documentation_style': {'status': 'unknown'}
        }
        
        try:
            # Sample Python files to check documentation
            python_files = list(Path('.').rglob('*.py'))
            if not python_files:
                code_docs['docstring_coverage'] = {'status': 'no_python_files'}
                return code_docs
            
            # Sample first few files for analysis
            sample_files = python_files[:5]
            
            total_functions = 0
            documented_functions = 0
            
            for py_file in sample_files:
                try:
                    with open(py_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # Simple heuristic for function documentation
                    lines = content.split('\n')
                    in_function = False
                    function_has_docstring = False
                    
                    for i, line in enumerate(lines):
                        stripped = line.strip()
                        
                        # Check for function definition
                        if stripped.startswith('def ') and not stripped.startswith('def _'):  # Ignore private functions
                            total_functions += 1
                            in_function = True
                            function_has_docstring = False
                            
                            # Check next few lines for docstring
                            for j in range(i+1, min(i+4, len(lines))):
                                if '"""' in lines[j] or "'''" in lines[j]:
                                    function_has_docstring = True
                                    break
                            
                            if function_has_docstring:
                                documented_functions += 1
                
                except Exception:
                    continue
            
            if total_functions > 0:
                coverage_pct = (documented_functions / total_functions) * 100
                code_docs['docstring_coverage'] = {
                    'status': 'good' if coverage_pct > 70 else 'partial' if coverage_pct > 30 else 'poor',
                    'coverage_percentage': coverage_pct,
                    'total_functions': total_functions,
                    'documented_functions': documented_functions,
                    'sample_files': len(sample_files)
                }
        
        except Exception as e:
            code_docs['error'] = str(e)
        
        return code_docs
    
    async def _check_api_docs(self) -> Dict[str, Any]:
        """Check API documentation."""
        api_docs = {
            'openapi_schema': {'status': 'unknown'},
            'api_documentation_tools': {'status': 'unknown'}
        }
        
        try:
            # Check for OpenAPI/FastAPI documentation
            # Look for FastAPI usage
            python_files = list(Path('.').rglob('*.py'))
            
            fastapi_usage = False
            for py_file in python_files[:10]:  # Sample files
                try:
                    with open(py_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                    if 'from fastapi' in content or 'import fastapi' in content:
                        fastapi_usage = True
                        break
                except:
                    continue
            
            if fastapi_usage:
                api_docs['openapi_schema'] = {
                    'status': 'auto_generated',
                    'framework': 'FastAPI'
                }
            else:
                api_docs['openapi_schema'] = {'status': 'not_detected'}
            
            # Check for API documentation files
            api_doc_files = [
                'docs/api.md',
                'docs/api/',
                'api_docs/',
                'openapi.json',
                'swagger.json'
            ]
            
            found_api_docs = [f for f in api_doc_files if Path(f).exists()]
            api_docs['api_documentation_tools'] = {
                'status': 'configured' if found_api_docs else 'basic',
                'documentation_files': found_api_docs
            }
        
        except Exception as e:
            api_docs['error'] = str(e)
        
        return api_docs
    
    async def _check_developer_docs(self) -> Dict[str, Any]:
        """Check developer documentation."""
        dev_docs = {
            'setup_instructions': {'status': 'unknown'},
            'architecture_docs': {'status': 'unknown'},
            'contributing_guide': {'status': 'unknown'}
        }
        
        try:
            # Check for developer documentation files
            dev_doc_files = {
                'setup_instructions': ['SETUP.md', 'docs/setup.md', 'INSTALL.md', 'docs/installation.md'],
                'architecture_docs': ['ARCHITECTURE.md', 'docs/architecture.md', 'docs/design.md', 'DESIGN.md'],
                'contributing_guide': ['CONTRIBUTING.md', 'docs/contributing.md', 'DEVELOP.md', 'docs/development.md']
            }
            
            for category, file_list in dev_doc_files.items():
                found_files = [f for f in file_list if Path(f).exists()]
                dev_docs[category] = {
                    'status': 'configured' if found_files else 'missing',
                    'files': found_files
                }
        
        except Exception as e:
            dev_docs['error'] = str(e)
        
        return dev_docs
    
    async def _identify_automation_opportunities(self) -> Dict[str, Any]:
        """Identify opportunities for workflow automation."""
        automation_opportunities = {
            'code_quality_automation': [],
            'testing_automation': [],
            'deployment_automation': [],
            'monitoring_automation': []
        }
        
        # Based on previous analysis, identify what could be automated
        # This would be populated based on findings from other analyses
        
        return automation_opportunities
    
    async def _calculate_efficiency_metrics(self) -> Dict[str, Any]:
        """Calculate development workflow efficiency metrics."""
        efficiency = {
            'setup_time': {'status': 'unknown'},
            'development_friction': {'status': 'unknown'},
            'deployment_time': {'status': 'unknown'},
            'debugging_efficiency': {'status': 'unknown'}
        }
        
        # This would calculate actual metrics based on workflow analysis
        # For now, providing structure for implementation
        
        return efficiency
    
    def _calculate_workflow_score(self, workflow_analysis: Dict[str, Any]) -> float:
        """Calculate overall workflow efficiency score."""
        score = 100.0
        
        # Development environment scoring
        dev_env = workflow_analysis.get('development_environment', {})
        
        # Python environment
        python_env = dev_env.get('python_environment', {})
        if python_env.get('virtual_environment', {}).get('status') != 'active':
            score -= 15
        
        # Dependency management
        dep_mgmt = dev_env.get('dependency_management', {})
        if dep_mgmt.get('dependency_files', {}).get('status') != 'complete':
            score -= 10
        
        # Code quality tools scoring
        code_quality = workflow_analysis.get('code_quality_tools', {})
        
        # Linting
        linting = code_quality.get('linting_tools', {})
        if not linting.get('available_linters'):
            score -= 15
        
        # Formatting
        formatting = code_quality.get('formatting_tools', {})
        if not formatting.get('available_formatters'):
            score -= 10
        
        # Testing workflow scoring
        testing = workflow_analysis.get('testing_workflow', {})
        
        # Test framework
        test_framework = testing.get('test_framework', {})
        if not test_framework.get('frameworks'):
            score -= 20
        
        # Test coverage
        test_coverage = testing.get('test_coverage', {})
        if not test_coverage.get('coverage_tools'):
            score -= 15
        
        # Documentation scoring
        documentation = workflow_analysis.get('documentation_status', {})
        
        # README
        readme = documentation.get('readme_status', {})
        if not readme.get('exists', False):
            score -= 10
        elif readme.get('completeness', {}).get('status') == 'minimal':
            score -= 5
        
        return max(0.0, score)
    
    def _extract_workflow_issues(self, workflow_analysis: Dict[str, Any]) -> List[Dict[str, str]]:
        """Extract workflow issues from analysis."""
        issues = []
        
        # Development environment issues
        dev_env = workflow_analysis.get('development_environment', {})
        
        python_env = dev_env.get('python_environment', {})
        if python_env.get('virtual_environment', {}).get('status') != 'active':
            issues.append({
                'severity': 'medium',
                'component': 'python_environment',
                'issue': 'Virtual environment not active',
                'recommendation': 'Activate virtual environment: source venv/bin/activate'
            })
        
        # Code quality issues
        code_quality = workflow_analysis.get('code_quality_tools', {})
        
        linting = code_quality.get('linting_tools', {})
        if not linting.get('available_linters'):
            issues.append({
                'severity': 'high',
                'component': 'code_quality',
                'issue': 'No linting tools configured',
                'recommendation': 'Install and configure ruff or flake8'
            })
        
        formatting = code_quality.get('formatting_tools', {})
        if not formatting.get('available_formatters'):
            issues.append({
                'severity': 'medium',
                'component': 'code_quality',
                'issue': 'No code formatting tools configured',
                'recommendation': 'Install and configure black'
            })
        
        # Testing issues
        testing = workflow_analysis.get('testing_workflow', {})
        
        test_framework = testing.get('test_framework', {})
        if not test_framework.get('frameworks'):
            issues.append({
                'severity': 'high',
                'component': 'testing',
                'issue': 'No testing framework configured',
                'recommendation': 'Install and configure pytest'
            })
        
        # Documentation issues
        documentation = workflow_analysis.get('documentation_status', {})
        
        readme = documentation.get('readme_status', {})
        if not readme.get('exists', False):
            issues.append({
                'severity': 'medium',
                'component': 'documentation',
                'issue': 'README file missing',
                'recommendation': 'Create comprehensive README.md'
            })
        
        return issues
    
    def _generate_workflow_recommendations(self, workflow_analysis: Dict[str, Any]) -> List[Dict[str, str]]:
        """Generate workflow optimization recommendations."""
        recommendations = []
        
        # Development environment recommendations
        dev_env = workflow_analysis.get('development_environment', {})
        
        python_env = dev_env.get('python_environment', {})
        if python_env.get('virtual_environment', {}).get('status') == 'available_not_active':
            recommendations.append({
                'priority': 'high',
                'action': 'Activate virtual environment',
                'description': 'Virtual environment exists but not active',
                'effort': '5 minutes'
            })
        
        # Code quality recommendations
        code_quality = workflow_analysis.get('code_quality_tools', {})
        
        if not code_quality.get('linting_tools', {}).get('available_linters'):
            recommendations.append({
                'priority': 'high',
                'action': 'Set up code linting',
                'description': 'Install and configure ruff for code linting',
                'effort': '30 minutes'
            })
        
        if not code_quality.get('formatting_tools', {}).get('available_formatters'):
            recommendations.append({
                'priority': 'medium',
                'action': 'Set up code formatting',
                'description': 'Install and configure black for code formatting',
                'effort': '20 minutes'
            })
        
        # Testing recommendations
        testing = workflow_analysis.get('testing_workflow', {})
        
        if not testing.get('test_framework', {}).get('frameworks'):
            recommendations.append({
                'priority': 'high',
                'action': 'Set up testing framework',
                'description': 'Install and configure pytest for testing',
                'effort': '1-2 hours'
            })
        
        if not testing.get('test_coverage', {}).get('coverage_tools'):
            recommendations.append({
                'priority': 'medium',
                'action': 'Set up test coverage',
                'description': 'Install pytest-cov for test coverage reporting',
                'effort': '30 minutes'
            })
        
        # Documentation recommendations
        documentation = workflow_analysis.get('documentation_status', {})
        
        if not documentation.get('readme_status', {}).get('exists', False):
            recommendations.append({
                'priority': 'medium',
                'action': 'Create project README',
                'description': 'Write comprehensive README with setup and usage instructions',
                'effort': '2-3 hours'
            })
        
        # Deployment recommendations
        deployment = workflow_analysis.get('deployment_process', {})
        
        containerization = deployment.get('containerization', {})
        if containerization.get('docker_setup', {}).get('status') != 'configured':
            recommendations.append({
                'priority': 'medium',
                'action': 'Set up containerization',
                'description': 'Create Dockerfile and docker-compose configuration',
                'effort': '2-4 hours'
            })
        
        return recommendations