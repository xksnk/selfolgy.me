#!/usr/bin/env python3
"""
Скрипт для валидации тестового покрытия Selfology

Проверяет:
- Текущий coverage по компонентам
- Прогресс по фазам рефакторинга
- Quality gates
- Генерирует отчет
"""

import subprocess
import json
import sys
from pathlib import Path
from typing import Dict, List, Tuple
from datetime import datetime


# Coverage targets по компонентам
COVERAGE_TARGETS = {
    "core/event_bus.py": 95,
    "systems/onboarding/": 85,
    "systems/analysis/": 90,
    "systems/profile/": 85,
    "systems/telegram/": 80,
    "systems/coach/": 90,
    "overall": 85,
}

# P0 тесты (критичные, должны проходить всегда)
P0_TESTS = [
    "tests/event_bus/unit/test_event_publisher.py::TestEventPublisher::test_publish_simple_event",
    "tests/event_bus/unit/test_event_subscriber.py::TestEventSubscriber::test_subscribe_receives_events",
    "tests/systems/onboarding/unit/test_question_router.py::TestQuestionRouter::test_router_respects_energy_safety",
    "tests/systems/analysis/unit/test_answer_analyzer.py::TestAnswerAnalyzer::test_instant_analysis_is_fast",
]


class Colors:
    """ANSI color codes"""
    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    BOLD = "\033[1m"
    END = "\033[0m"


def run_command(cmd: List[str]) -> Tuple[int, str]:
    """Run shell command and return exit code and output"""
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300
        )
        return result.returncode, result.stdout + result.stderr
    except subprocess.TimeoutExpired:
        return 1, "Command timeout"
    except Exception as e:
        return 1, str(e)


def check_p0_tests() -> bool:
    """Check that all P0 tests pass"""
    print(f"\n{Colors.BOLD}🎯 Checking P0 (Critical) Tests...{Colors.END}")

    all_pass = True

    for test in P0_TESTS:
        if not Path("tests/").exists():
            print(f"{Colors.YELLOW}⚠️  Tests directory not found yet{Colors.END}")
            return False

        # Check if test file exists
        test_file = test.split("::")[0]
        if not Path(test_file).exists():
            print(f"{Colors.YELLOW}⏳ {test_file} - Not implemented yet{Colors.END}")
            continue

        # Run specific test
        exit_code, output = run_command([
            "pytest",
            test,
            "-v",
            "--tb=short"
        ])

        if exit_code == 0:
            print(f"{Colors.GREEN}✅ {test.split('::')[-1]}{Colors.END}")
        else:
            print(f"{Colors.RED}❌ {test.split('::')[-1]}{Colors.END}")
            all_pass = False

    return all_pass


def get_coverage_report() -> Dict[str, float]:
    """Get coverage report for all components"""
    print(f"\n{Colors.BOLD}📊 Generating Coverage Report...{Colors.END}")

    if not Path("tests/").exists():
        print(f"{Colors.YELLOW}⚠️  Tests not implemented yet{Colors.END}")
        return {}

    # Run pytest with coverage
    exit_code, output = run_command([
        "pytest",
        "--cov=.",
        "--cov-report=json",
        "--cov-report=term-missing",
        "-q"
    ])

    if exit_code != 0 and not Path("coverage.json").exists():
        print(f"{Colors.YELLOW}⚠️  Coverage report not available yet{Colors.END}")
        return {}

    # Parse coverage.json
    coverage_data = {}

    try:
        with open("coverage.json", "r") as f:
            data = json.load(f)

        # Overall coverage
        coverage_data["overall"] = data["totals"]["percent_covered"]

        # Per-file coverage
        for filepath, stats in data["files"].items():
            coverage_data[filepath] = stats["summary"]["percent_covered"]

    except Exception as e:
        print(f"{Colors.RED}Error parsing coverage: {e}{Colors.END}")

    return coverage_data


def check_coverage_targets(coverage_data: Dict[str, float]) -> bool:
    """Check if coverage meets targets"""
    print(f"\n{Colors.BOLD}🎯 Coverage vs Targets:{Colors.END}\n")

    all_met = True

    for component, target in COVERAGE_TARGETS.items():
        if component == "overall":
            current = coverage_data.get("overall", 0)
        else:
            # Aggregate coverage for component
            matching_files = [
                cov for path, cov in coverage_data.items()
                if component in path
            ]
            current = sum(matching_files) / len(matching_files) if matching_files else 0

        gap = target - current

        # Format output
        status = ""
        if current >= target:
            status = f"{Colors.GREEN}✅"
            color = Colors.GREEN
        elif current >= target * 0.9:
            status = f"{Colors.YELLOW}⚠️ "
            color = Colors.YELLOW
        else:
            status = f"{Colors.RED}❌"
            color = Colors.RED
            all_met = False

        print(
            f"{status} {component:40} | "
            f"{color}{current:5.1f}%{Colors.END} / {target}% "
            f"({gap:+.1f}%)"
        )

    return all_met


def get_phase_progress() -> Dict[str, int]:
    """Get progress for each refactoring phase"""
    print(f"\n{Colors.BOLD}📅 Refactoring Phase Progress:{Colors.END}\n")

    phases = {
        "Phase 0: Event Bus": "tests/event_bus/",
        "Phase 1: Onboarding": "tests/systems/onboarding/",
        "Phase 2: Analysis": "tests/systems/analysis/",
        "Phase 3: Profile": "tests/systems/profile/",
        "Phase 4: Telegram": "tests/systems/telegram/",
        "Phase 5: Coach": "tests/systems/coach/",
        "Phase 6: Integration": "tests/e2e/",
        "Phase 7: Performance": "tests/load/",
        "Phase 8: Production": "tests/production/",
    }

    progress = {}

    for phase_name, test_dir in phases.items():
        test_path = Path(test_dir)

        if not test_path.exists():
            progress[phase_name] = 0
            print(f"{Colors.RED}⏳ {phase_name:30} | Not started{Colors.END}")
        else:
            # Count test files
            test_files = list(test_path.rglob("test_*.py"))
            test_count = len(test_files)

            if test_count == 0:
                progress[phase_name] = 0
                print(f"{Colors.YELLOW}🚧 {phase_name:30} | In progress (0 tests){Colors.END}")
            else:
                # Run tests to check if passing
                exit_code, output = run_command([
                    "pytest",
                    str(test_path),
                    "-q"
                ])

                if exit_code == 0:
                    progress[phase_name] = 100
                    print(f"{Colors.GREEN}✅ {phase_name:30} | Complete ({test_count} tests){Colors.END}")
                else:
                    progress[phase_name] = 50
                    print(f"{Colors.YELLOW}⚠️  {phase_name:30} | In progress ({test_count} tests, some failing){Colors.END}")

    return progress


def check_quality_gates() -> bool:
    """Check quality gates (блокируют merge)"""
    print(f"\n{Colors.BOLD}🚨 Quality Gates:{Colors.END}\n")

    gates_passed = True

    # Gate 1: P0 tests must pass
    p0_pass = check_p0_tests()
    if p0_pass:
        print(f"{Colors.GREEN}✅ P0 Tests: All passing{Colors.END}")
    else:
        print(f"{Colors.RED}❌ P0 Tests: Some failing (BLOCKS MERGE){Colors.END}")
        gates_passed = False

    # Gate 2: Coverage must not drop >2%
    # (Would need baseline comparison - skip for now)

    # Gate 3: No lint errors
    print(f"\n{Colors.BOLD}Checking lint errors...{Colors.END}")
    exit_code, output = run_command([
        "ruff",
        "check",
        "selfology_bot/",
        "systems/",
        "core/"
    ])

    if exit_code == 0:
        print(f"{Colors.GREEN}✅ Lint: No errors{Colors.END}")
    else:
        print(f"{Colors.RED}❌ Lint: Errors found (BLOCKS MERGE){Colors.END}")
        print(output[:500])
        gates_passed = False

    return gates_passed


def generate_summary_report():
    """Generate summary report"""
    print(f"\n{Colors.BOLD}{'='*70}{Colors.END}")
    print(f"{Colors.BOLD}📋 TESTING SUMMARY REPORT{Colors.END}")
    print(f"{Colors.BOLD}{'='*70}{Colors.END}\n")

    print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Project: Selfology - Microservices Refactoring\n")

    # Overall status
    coverage_data = get_coverage_report()
    overall_coverage = coverage_data.get("overall", 0)

    if overall_coverage >= COVERAGE_TARGETS["overall"]:
        status = f"{Colors.GREEN}🎉 TARGET ACHIEVED{Colors.END}"
    elif overall_coverage >= COVERAGE_TARGETS["overall"] * 0.8:
        status = f"{Colors.YELLOW}🚧 IN PROGRESS{Colors.END}"
    else:
        status = f"{Colors.RED}⚠️  NEEDS WORK{Colors.END}"

    print(f"Overall Coverage: {overall_coverage:.1f}% / {COVERAGE_TARGETS['overall']}%")
    print(f"Status: {status}\n")

    # Phase progress
    progress = get_phase_progress()
    completed_phases = sum(1 for p in progress.values() if p == 100)
    total_phases = len(progress)

    print(f"Phases Completed: {completed_phases}/{total_phases}")

    # Coverage targets
    coverage_met = check_coverage_targets(coverage_data)

    # Quality gates
    gates_passed = check_quality_gates()

    print(f"\n{Colors.BOLD}{'='*70}{Colors.END}")

    if gates_passed and coverage_met:
        print(f"\n{Colors.GREEN}{Colors.BOLD}✅ ALL CHECKS PASSED - Ready to merge!{Colors.END}")
        return 0
    elif gates_passed:
        print(f"\n{Colors.YELLOW}{Colors.BOLD}⚠️  SOME CHECKS FAILED - Continue working on coverage{Colors.END}")
        return 0  # Don't block on coverage (warning only)
    else:
        print(f"\n{Colors.RED}{Colors.BOLD}❌ QUALITY GATES FAILED - Cannot merge{Colors.END}")
        return 1


def main():
    """Main entry point"""
    project_root = Path(__file__).parent.parent

    # Change to project root
    import os
    os.chdir(project_root)

    print(f"{Colors.BOLD}{Colors.BLUE}")
    print("╔═══════════════════════════════════════════════════════════════════╗")
    print("║          SELFOLOGY TEST COVERAGE VALIDATION                       ║")
    print("║          Microservices Refactoring Test Strategy                 ║")
    print("╚═══════════════════════════════════════════════════════════════════╝")
    print(f"{Colors.END}\n")

    exit_code = generate_summary_report()

    print(f"\n{Colors.BOLD}📖 Documentation:{Colors.END}")
    print("  - Testing Strategy: TESTING_STRATEGY.md")
    print("  - Code Examples: TESTING_CODE_EXAMPLES.md")
    print("  - Implementation Plan: TESTING_IMPLEMENTATION_PLAN.md")

    print(f"\n{Colors.BOLD}🚀 Next Steps:{Colors.END}")
    if exit_code == 0:
        print("  1. Review coverage gaps")
        print("  2. Implement missing tests")
        print("  3. Run: pytest --cov=. --cov-report=html")
        print("  4. Re-run this script")
    else:
        print("  1. Fix failing P0 tests")
        print("  2. Fix lint errors")
        print("  3. Re-run this script")

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
