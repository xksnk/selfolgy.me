#!/usr/bin/env python3
"""
Валидация полноты метаданных в enhanced_questions.json

Проверяет что у всех 693 вопросов заполнены все необходимые поля.
"""

import json
import sys
from pathlib import Path
from typing import Dict, List, Any, Set
from collections import defaultdict

# Ожидаемая структура вопроса
EXPECTED_STRUCTURE = {
    "root": ["id", "text", "source_system", "classification", "psychology", "processing_hints"],
    "classification": ["journey_stage", "depth_level", "domain", "energy_dynamic"],
    "psychology": ["complexity", "emotional_weight", "insight_potential", "safety_level", "trust_requirement"],
    "processing_hints": ["recommended_model", "batch_compatible", "requires_context"]
}

# Допустимые значения для enum полей
VALID_VALUES = {
    "journey_stage": ["ENTRY", "EXPLORING", "DEEPENING", "INTEGRATING", "TRANSFORMING"],
    "depth_level": ["SURFACE", "CONSCIOUS", "EDGE", "SHADOW", "CORE"],
    "domain": [
        "IDENTITY", "EMOTIONS", "RELATIONSHIPS", "VALUES", "GOALS",
        "FEARS", "GROWTH", "PAST", "FUTURE", "WORK",
        "CREATIVITY", "BODY", "SPIRITUALITY"
    ],
    "energy_dynamic": ["OPENING", "NEUTRAL", "PROCESSING", "HEAVY", "HEALING"],
    "recommended_model": ["claude-3.5-sonnet", "gpt-4o", "gpt-4o-mini"]
}

# Диапазоны для числовых полей
NUMERIC_RANGES = {
    "complexity": (1, 5),
    "emotional_weight": (1, 5),
    "insight_potential": (1, 5),
    "safety_level": (1, 5),
    "trust_requirement": (1, 5)
}


class QuestionValidator:
    """Валидатор полноты данных вопросов"""

    def __init__(self, questions_file: Path):
        self.questions_file = questions_file
        self.issues: List[Dict[str, Any]] = []
        self.stats = defaultdict(int)
        self.questions = []

    def load_questions(self) -> bool:
        """Загрузить JSON файл"""
        try:
            with open(self.questions_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.questions = data.get("questions", [])
                self.stats["total_questions"] = len(self.questions)
                return True
        except Exception as e:
            print(f"❌ Ошибка загрузки файла: {e}")
            return False

    def validate_question(self, question: Dict[str, Any], index: int) -> List[str]:
        """Валидировать один вопрос, вернуть список проблем"""
        problems = []
        q_id = question.get("id", f"question_{index}")

        # 1. Проверка наличия обязательных полей root level
        for field in EXPECTED_STRUCTURE["root"]:
            if field not in question:
                problems.append(f"Missing root field: {field}")
            elif question[field] is None:
                problems.append(f"Null value in: {field}")
            elif isinstance(question[field], str) and not question[field].strip():
                problems.append(f"Empty string in: {field}")

        # 2. Проверка classification
        if "classification" in question:
            cls = question["classification"]
            for field in EXPECTED_STRUCTURE["classification"]:
                if field not in cls:
                    problems.append(f"Missing classification.{field}")
                elif cls[field] is None:
                    problems.append(f"Null value in classification.{field}")
                elif field in VALID_VALUES:
                    # Проверка enum значений
                    if cls[field] not in VALID_VALUES[field]:
                        problems.append(
                            f"Invalid classification.{field}: '{cls[field]}' "
                            f"(valid: {VALID_VALUES[field]})"
                        )
        else:
            problems.append("Missing classification object")

        # 3. Проверка psychology
        if "psychology" in question:
            psy = question["psychology"]
            for field in EXPECTED_STRUCTURE["psychology"]:
                if field not in psy:
                    problems.append(f"Missing psychology.{field}")
                elif psy[field] is None:
                    problems.append(f"Null value in psychology.{field}")
                elif field in NUMERIC_RANGES:
                    # Проверка числового диапазона
                    min_val, max_val = NUMERIC_RANGES[field]
                    try:
                        val = int(psy[field])
                        if not (min_val <= val <= max_val):
                            problems.append(
                                f"psychology.{field} out of range: {val} "
                                f"(expected {min_val}-{max_val})"
                            )
                    except (ValueError, TypeError):
                        problems.append(f"psychology.{field} is not a number: {psy[field]}")
        else:
            problems.append("Missing psychology object")

        # 4. Проверка processing_hints
        if "processing_hints" in question:
            hints = question["processing_hints"]
            for field in EXPECTED_STRUCTURE["processing_hints"]:
                if field not in hints:
                    problems.append(f"Missing processing_hints.{field}")
                elif hints[field] is None:
                    problems.append(f"Null value in processing_hints.{field}")

            # Проверка recommended_model
            if "recommended_model" in hints:
                model = hints["recommended_model"]
                if model not in VALID_VALUES["recommended_model"]:
                    problems.append(
                        f"Invalid processing_hints.recommended_model: '{model}' "
                        f"(valid: {VALID_VALUES['recommended_model']})"
                    )

            # Проверка boolean полей
            for bool_field in ["batch_compatible", "requires_context"]:
                if bool_field in hints:
                    if not isinstance(hints[bool_field], bool):
                        problems.append(
                            f"processing_hints.{bool_field} is not boolean: {hints[bool_field]}"
                        )
        else:
            problems.append("Missing processing_hints object")

        # 5. Проверка text (не должен быть пустым)
        if "text" in question:
            text = question["text"].strip() if question["text"] else ""
            if len(text) < 5:
                problems.append(f"Question text too short: '{text}'")

        return problems

    def validate_all(self):
        """Валидировать все вопросы"""
        print(f"🔍 Валидация {self.stats['total_questions']} вопросов...\n")

        questions_with_issues = 0

        for idx, question in enumerate(self.questions):
            q_id = question.get("id", f"question_{idx}")
            problems = self.validate_question(question, idx)

            if problems:
                questions_with_issues += 1
                self.issues.append({
                    "question_id": q_id,
                    "index": idx,
                    "text": question.get("text", "")[:50] + "...",
                    "problems": problems
                })
                self.stats["total_issues"] += len(problems)

        self.stats["questions_with_issues"] = questions_with_issues
        self.stats["questions_valid"] = self.stats["total_questions"] - questions_with_issues

    def analyze_patterns(self):
        """Анализ паттернов проблем"""
        problem_types = defaultdict(int)

        for issue in self.issues:
            for problem in issue["problems"]:
                # Извлекаем тип проблемы (первая часть до :)
                problem_type = problem.split(":")[0].strip()
                problem_types[problem_type] += 1

        self.stats["problem_types"] = dict(problem_types)

    def print_report(self):
        """Вывести отчет"""
        print("=" * 80)
        print("📊 РЕЗУЛЬТАТЫ ВАЛИДАЦИИ")
        print("=" * 80)
        print()

        # Общая статистика
        print("🔢 ОБЩАЯ СТАТИСТИКА:")
        print(f"  Всего вопросов:           {self.stats['total_questions']}")
        print(f"  ✅ Вопросов без проблем:  {self.stats['questions_valid']} "
              f"({self.stats['questions_valid'] / self.stats['total_questions'] * 100:.1f}%)")
        print(f"  ❌ Вопросов с проблемами: {self.stats['questions_with_issues']} "
              f"({self.stats['questions_with_issues'] / self.stats['total_questions'] * 100:.1f}%)")
        print(f"  Всего проблем:            {self.stats['total_issues']}")
        print()

        # Типы проблем
        if self.stats.get("problem_types"):
            print("📋 ТИПЫ ПРОБЛЕМ:")
            sorted_types = sorted(
                self.stats["problem_types"].items(),
                key=lambda x: x[1],
                reverse=True
            )
            for problem_type, count in sorted_types:
                print(f"  • {problem_type}: {count}")
            print()

        # Детальные проблемы (первые 10)
        if self.issues:
            print("🔍 ДЕТАЛИ ПРОБЛЕМ (первые 10):")
            print()
            for issue in self.issues[:10]:
                print(f"  ID: {issue['question_id']}")
                print(f"  Текст: {issue['text']}")
                print(f"  Проблемы:")
                for problem in issue["problems"]:
                    print(f"    - {problem}")
                print()

            if len(self.issues) > 10:
                print(f"  ... и еще {len(self.issues) - 10} вопросов с проблемами")
                print()

        # Итог
        print("=" * 80)
        if self.stats["questions_with_issues"] == 0:
            print("✅ ВСЕ ВОПРОСЫ ВАЛИДНЫ! Метаданные заполнены полностью.")
        else:
            print(f"⚠️ НАЙДЕНО ПРОБЛЕМ: {self.stats['questions_with_issues']} вопросов требуют внимания")
        print("=" * 80)

    def save_detailed_report(self, output_file: Path):
        """Сохранить детальный отчет в JSON"""
        report = {
            "validation_date": "2025-10-06",
            "questions_file": str(self.questions_file),
            "statistics": dict(self.stats),
            "issues": self.issues
        }

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        print(f"\n💾 Детальный отчет сохранен: {output_file}")


def main():
    # Путь к файлу с вопросами
    project_root = Path(__file__).parent.parent
    questions_file = project_root / "intelligent_question_core" / "data" / "enhanced_questions.json"

    if not questions_file.exists():
        print(f"❌ Файл не найден: {questions_file}")
        sys.exit(1)

    print(f"📁 Файл: {questions_file}")
    print()

    # Валидация
    validator = QuestionValidator(questions_file)

    if not validator.load_questions():
        sys.exit(1)

    validator.validate_all()
    validator.analyze_patterns()
    validator.print_report()

    # Сохранить детальный отчет
    report_file = project_root / "logs" / "questions_validation_report.json"
    report_file.parent.mkdir(exist_ok=True)
    validator.save_detailed_report(report_file)

    # Exit code
    if validator.stats["questions_with_issues"] > 0:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
