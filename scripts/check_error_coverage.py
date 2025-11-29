#!/usr/bin/env python3
"""
Проверка покрытия error_collector в проекте Selfology

Запуск: python scripts/check_error_coverage.py
"""

import os
import re
from pathlib import Path
from typing import Dict, List, Tuple

# Корневая директория проекта
PROJECT_ROOT = Path(__file__).parent.parent

# Критические компоненты которые ДОЛЖНЫ иметь error_collector
CRITICAL_COMPONENTS = [
    "selfology_controller.py",
    "services/chat_coach.py",
    "selfology_bot/services/onboarding/orchestrator.py",
    "selfology_bot/database/service.py",
    "selfology_bot/analysis/answer_analyzer.py",
    "selfology_bot/database/onboarding_dao.py",
    "selfology_bot/database/user_dao.py",
    "selfology_bot/services/onboarding/question_router.py",
    "selfology_bot/services/onboarding/fatigue_detector.py",
    "selfology_bot/services/vector_storage_service.py",
    "selfology_bot/services/embedding_service.py",
]

# Директории для сканирования
SCAN_DIRS = [
    "selfology_bot",
    "services",
    "core",
    "systems",
]

# Исключения (не требуют error_collector)
EXCLUDE_PATTERNS = [
    "__pycache__",
    "test_",
    "__init__.py",
    "config.py",
    "constants.py",
]


def check_file_for_error_collector(filepath: Path) -> Dict:
    """Проверить файл на наличие error_collector"""

    result = {
        "has_import": False,
        "has_collect_calls": 0,
        "has_except_blocks": 0,
        "coverage_ratio": 0.0,
    }

    try:
        content = filepath.read_text(encoding='utf-8')

        # Проверяем импорт
        if "from core.error_collector import" in content or "import error_collector" in content:
            result["has_import"] = True

        # Считаем вызовы error_collector.collect
        collect_calls = len(re.findall(r'error_collector\.collect\s*\(', content))
        result["has_collect_calls"] = collect_calls

        # Считаем except блоки
        except_blocks = len(re.findall(r'except\s+\w*Exception', content))
        except_blocks += len(re.findall(r'except\s+Exception', content))
        except_blocks += len(re.findall(r'except\s*:', content))
        result["has_except_blocks"] = except_blocks

        # Вычисляем покрытие
        if except_blocks > 0:
            result["coverage_ratio"] = min(1.0, collect_calls / except_blocks)
        elif collect_calls > 0:
            result["coverage_ratio"] = 1.0

    except Exception as e:
        result["error"] = str(e)

    return result


def scan_project() -> Tuple[List[Dict], List[Dict], List[Dict]]:
    """Сканировать проект и вернуть результаты"""

    covered = []      # Файлы с error_collector
    not_covered = []  # Файлы без error_collector но с except
    no_errors = []    # Файлы без except блоков

    # Сканируем критические компоненты
    for component in CRITICAL_COMPONENTS:
        filepath = PROJECT_ROOT / component
        if filepath.exists():
            result = check_file_for_error_collector(filepath)
            result["file"] = component
            result["critical"] = True

            if result["has_import"] and result["has_collect_calls"] > 0:
                covered.append(result)
            elif result["has_except_blocks"] > 0:
                not_covered.append(result)
            else:
                no_errors.append(result)

    # Сканируем остальные директории
    for scan_dir in SCAN_DIRS:
        dir_path = PROJECT_ROOT / scan_dir
        if not dir_path.exists():
            continue

        for filepath in dir_path.rglob("*.py"):
            # Пропускаем исключения
            if any(pattern in str(filepath) for pattern in EXCLUDE_PATTERNS):
                continue

            # Пропускаем уже проверенные критические
            rel_path = str(filepath.relative_to(PROJECT_ROOT))
            if rel_path in CRITICAL_COMPONENTS:
                continue

            result = check_file_for_error_collector(filepath)
            result["file"] = rel_path
            result["critical"] = False

            if result["has_import"] and result["has_collect_calls"] > 0:
                covered.append(result)
            elif result["has_except_blocks"] > 0:
                not_covered.append(result)
            else:
                no_errors.append(result)

    return covered, not_covered, no_errors


def print_report(covered: List, not_covered: List, no_errors: List):
    """Вывести отчет о покрытии"""

    print("\n" + "="*60)
    print("📊 ОТЧЕТ О ПОКРЫТИИ ERROR_COLLECTOR")
    print("="*60)

    # Покрытые файлы
    print(f"\n✅ ПОКРЫТО ({len(covered)} файлов):")
    print("-"*60)
    for item in sorted(covered, key=lambda x: (not x['critical'], x['file'])):
        critical_mark = "🔴" if item['critical'] else "  "
        ratio = f"{item['coverage_ratio']*100:.0f}%"
        print(f"{critical_mark} {item['file']}")
        print(f"   └─ {item['has_collect_calls']} вызовов / {item['has_except_blocks']} except ({ratio})")

    # Непокрытые файлы
    if not_covered:
        print(f"\n❌ НЕ ПОКРЫТО ({len(not_covered)} файлов):")
        print("-"*60)
        for item in sorted(not_covered, key=lambda x: (not x['critical'], x['file'])):
            critical_mark = "🔴" if item['critical'] else "  "
            print(f"{critical_mark} {item['file']}")
            print(f"   └─ {item['has_except_blocks']} except блоков без error_collector")

    # Статистика
    total_files = len(covered) + len(not_covered)
    coverage_pct = (len(covered) / total_files * 100) if total_files > 0 else 0

    critical_covered = sum(1 for x in covered if x['critical'])
    critical_total = sum(1 for x in covered + not_covered if x['critical'])

    print("\n" + "="*60)
    print("📈 ИТОГО:")
    print(f"   Общее покрытие: {len(covered)}/{total_files} файлов ({coverage_pct:.0f}%)")
    print(f"   Критические компоненты: {critical_covered}/{critical_total}")
    print(f"   Файлов без except: {len(no_errors)}")
    print("="*60)

    # Рекомендации
    if not_covered:
        print("\n⚠️  РЕКОМЕНДАЦИИ:")
        for item in not_covered:
            if item['critical']:
                print(f"   🔴 КРИТИЧНО: Добавить error_collector в {item['file']}")
            else:
                print(f"   📝 Рассмотреть: {item['file']}")
    else:
        print("\n✨ Все критические компоненты покрыты!")

    print()


def main():
    """Главная функция"""

    print("🔍 Сканирование проекта Selfology...")

    covered, not_covered, no_errors = scan_project()
    print_report(covered, not_covered, no_errors)

    # Код возврата для CI/CD
    critical_not_covered = [x for x in not_covered if x['critical']]
    if critical_not_covered:
        print("❌ Есть непокрытые критические компоненты!")
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
