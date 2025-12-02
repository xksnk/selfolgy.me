#!/usr/bin/env python3
"""
AI Question Validator — 3-этапный pipeline для проверки качества вопросов.

Этап 1: Индивидуальный анализ каждого вопроса (GPT-4o-mini — дёшево)
Этап 2: Консистентность кластеров (GPT-4o — точность)
Этап 3: Генерация переформулировок для проблемных (Claude — качество)

Использование:
    python validate_questions.py                    # Полный прогон
    python validate_questions.py --stage 1         # Только этап 1
    python validate_questions.py --dry-run         # Без API вызовов
    python validate_questions.py --sample 10       # Только 10 вопросов (тест)
"""

import json
import asyncio
import argparse
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, asdict
from typing import Optional
import os
import sys

# Добавляем корень проекта в path
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

import openai
from openai import AsyncOpenAI

# ═══════════════════════════════════════════════════════════════════════════════
# КОНФИГУРАЦИЯ
# ═══════════════════════════════════════════════════════════════════════════════

DATA_FILE = PROJECT_ROOT / "intelligent_question_core/data/selfology_programs_v2.json"
OUTPUT_DIR = PROJECT_ROOT / "products/book/exports/validation"

# Модели для разных этапов
MODELS = {
    "stage1": "gpt-4o-mini",      # Быстрый скрининг ~$0.50 за 674 вопроса
    "stage2": "gpt-4o",           # Кластерный анализ ~$2 за 190 кластеров
    "stage3": "gpt-4o",           # Переформулировки ~$1 за ~50 проблемных
}

# ═══════════════════════════════════════════════════════════════════════════════
# ПРОМПТЫ
# ═══════════════════════════════════════════════════════════════════════════════

STAGE1_SYSTEM = """Ты психотерапевт-редактор, проверяющий вопросы для книги самопознания.

Твоя задача — оценить ОДИН вопрос по критериям безопасности и качества.

КРИТЕРИИ ОЦЕНКИ:

1. **safety_score** (1-10): Насколько вопрос безопасен для читателя
   - 10: Полностью безопасен, мягкий
   - 7-9: Безопасен, но затрагивает чувствительные темы
   - 4-6: Может вызвать дискомфорт у уязвимых людей
   - 1-3: Потенциально травмирующий

2. **tone**: Тон вопроса
   - "soft" — мягкий, поддерживающий
   - "neutral" — нейтральный, исследовательский
   - "direct" — прямой, но уважительный
   - "harsh" — жёсткий, может восприниматься как критика

3. **has_labels**: Есть ли навешивание ярлыков на читателя
   - true — вопрос называет читателя чем-то ("ты неудачник", "ты слабый")
   - false — вопрос исследует опыт без ярлыков

4. **depth_level**: Глубина вопроса
   - "surface" — простой, о фактах
   - "conscious" — о мыслях и мнениях
   - "edge" — о чувствах и уязвимости
   - "shadow" — о скрытом, болезненном

5. **issues**: Список проблем (массив строк). Возможные проблемы:
   - "toxic_label" — называет читателя негативным словом
   - "too_harsh" — слишком жёсткая формулировка
   - "double_bind" — противоречивое послание
   - "presumes_negative" — предполагает негатив у читателя
   - "grammatical" — грамматическая ошибка
   - "unclear" — неясная формулировка
   - [] — проблем нет

6. **needs_review**: Нужна ли ручная проверка (true/false)

ВАЖНО:
- Слово "неадекватность" в контексте "страх профессиональной неадекватности" — это психологический термин, НЕ оскорбление
- Слово "слабость" в контексте "с кем ты можешь быть слабым" — это про уязвимость, НЕ ярлык
- Оценивай КОНТЕКСТ, не только отдельные слова

Отвечай ТОЛЬКО валидным JSON без комментариев."""

STAGE1_USER = """Оцени этот вопрос из книги самопознания:

Программа: {program}
Кластер: {cluster} ({cluster_type})
Позиция в кластере: {position}/{total}

ВОПРОС: "{question}"

Верни JSON:
{{
  "safety_score": <1-10>,
  "tone": "<soft|neutral|direct|harsh>",
  "has_labels": <true|false>,
  "depth_level": "<surface|conscious|edge|shadow>",
  "issues": ["issue1", "issue2"] или [],
  "needs_review": <true|false>,
  "comment": "<краткий комментарий если есть проблемы>"
}}"""

STAGE2_SYSTEM = """Ты психотерапевт, проверяющий ПОСЛЕДОВАТЕЛЬНОСТЬ вопросов в кластере.

Кластер — это группа из 3-7 вопросов, которые читатель проходит подряд.
Важна ПЛАВНОСТЬ перехода и отсутствие резких скачков.

КРИТЕРИИ:

1. **flow_score** (1-10): Плавность переходов между вопросами
   - 10: Идеальный поток, каждый вопрос естественно следует из предыдущего
   - 7-9: Хороший поток с небольшими скачками
   - 4-6: Заметные скачки, но терпимо
   - 1-3: Резкие переходы, дезориентирует читателя

2. **depth_progression**: Как меняется глубина
   - "gradual_increase" — плавное погружение (идеал)
   - "stable" — примерно одинаковая глубина
   - "gradual_decrease" — от глубокого к поверхностному
   - "chaotic" — хаотичные скачки (проблема!)

3. **tone_consistency**: Консистентность тона
   - "consistent" — тон одинаковый
   - "gradual_shift" — плавная смена тона
   - "inconsistent" — резкие смены (проблема!)

4. **issues**: Список проблем кластера
   - "depth_jump" — резкий скачок глубины
   - "tone_shift" — резкая смена тона
   - "missing_warmup" — нет разогрева перед глубоким вопросом
   - "no_closure" — нет завершения/выхода из глубины
   - "duplicate_angle" — повторяющийся ракурс вопросов

5. **problem_transitions**: Массив проблемных переходов
   - Каждый элемент: {"from": 1, "to": 2, "issue": "описание"}

Отвечай ТОЛЬКО валидным JSON."""

STAGE2_USER = """Проанализируй последовательность вопросов в кластере:

Программа: {program}
Кластер: {cluster}
Тип кластера: {cluster_type} (Foundation=входной, Exploration=исследование, Integration=глубокий)

ВОПРОСЫ:
{questions}

Верни JSON:
{{
  "flow_score": <1-10>,
  "depth_progression": "<gradual_increase|stable|gradual_decrease|chaotic>",
  "tone_consistency": "<consistent|gradual_shift|inconsistent>",
  "issues": ["issue1"] или [],
  "problem_transitions": [
    {{"from": 1, "to": 2, "issue": "описание проблемы"}}
  ] или [],
  "recommendation": "<краткая рекомендация если есть проблемы>"
}}"""

STAGE3_SYSTEM = """Ты опытный психотерапевт и редактор. Твоя задача — предложить БЕЗОПАСНЫЕ переформулировки проблемных вопросов.

ПРИНЦИПЫ ПЕРЕФОРМУЛИРОВКИ:

1. **Сохрани глубину и смысл** — вопрос должен исследовать ту же тему
2. **Убери токсичность** — никаких ярлыков и оценок читателя
3. **Добавь выбор** — вместо "ты X" используй "бывает ли, что ты чувствуешь X"
4. **Смягчи тон** — используй "возможно", "иногда", "бывает"
5. **Уважай автономию** — читатель сам решает, подходит ли ему вопрос

ПРИМЕРЫ ТРАНСФОРМАЦИЙ:
- "Чьи результаты заставляют тебя чувствовать себя неудачником?"
  → "Чьи успехи иногда вызывают у тебя сложные чувства? Что именно ты чувствуешь?"

- "Почему ты такой неуверенный?"
  → "В каких ситуациях ты замечаешь неуверенность в себе?"

Отвечай ТОЛЬКО валидным JSON."""

STAGE3_USER = """Предложи безопасные переформулировки для этого вопроса:

Программа: {program}
Кластер: {cluster}
Оригинальный вопрос: "{question}"
Выявленные проблемы: {issues}

Верни JSON:
{{
  "original": "<оригинал>",
  "issues_summary": "<краткое описание проблем>",
  "alternatives": [
    {{
      "text": "<вариант 1>",
      "approach": "<какой принцип применён>"
    }},
    {{
      "text": "<вариант 2>",
      "approach": "<какой принцип применён>"
    }}
  ],
  "recommended": 1 или 2,
  "recommendation_reason": "<почему этот вариант лучше>"
}}"""


# ═══════════════════════════════════════════════════════════════════════════════
# СТРУКТУРЫ ДАННЫХ
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class QuestionAnalysis:
    """Результат анализа одного вопроса (Этап 1)"""
    question_id: str
    program: str
    cluster: str
    cluster_type: str
    position: int
    text: str
    safety_score: int
    tone: str
    has_labels: bool
    depth_level: str
    issues: list
    needs_review: bool
    comment: str = ""


@dataclass
class ClusterAnalysis:
    """Результат анализа кластера (Этап 2)"""
    cluster_id: str
    program: str
    cluster_name: str
    cluster_type: str
    question_count: int
    flow_score: int
    depth_progression: str
    tone_consistency: str
    issues: list
    problem_transitions: list
    recommendation: str = ""


@dataclass
class Reformulation:
    """Предложенная переформулировка (Этап 3)"""
    question_id: str
    original: str
    issues_summary: str
    alternatives: list
    recommended: int
    recommendation_reason: str


# ═══════════════════════════════════════════════════════════════════════════════
# ОСНОВНОЙ КЛАСС ВАЛИДАТОРА
# ═══════════════════════════════════════════════════════════════════════════════

class QuestionValidator:
    def __init__(self, dry_run: bool = False):
        self.client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.dry_run = dry_run
        self.data = None
        self.results = {
            "stage1": [],
            "stage2": [],
            "stage3": [],
            "summary": {}
        }

    def load_data(self):
        """Загрузка базы вопросов"""
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            self.data = json.load(f)
        print(f"✅ Загружено: {self.data['metadata']['total_programs']} программ, "
              f"{self.data['metadata']['total_blocks']} кластеров, "
              f"{self.data['metadata']['total_questions']} вопросов")

    async def call_llm(self, system: str, user: str, model: str) -> dict:
        """Вызов LLM с парсингом JSON"""
        if self.dry_run:
            return {"dry_run": True}

        try:
            response = await self.client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user}
                ],
                temperature=0.3,
                response_format={"type": "json_object"}
            )
            return json.loads(response.choices[0].message.content)
        except Exception as e:
            print(f"❌ LLM Error: {e}")
            return {"error": str(e)}

    # ─────────────────────────────────────────────────────────────────────────
    # ЭТАП 1: Индивидуальный анализ вопросов
    # ─────────────────────────────────────────────────────────────────────────

    async def stage1_analyze_question(self, question: dict, program: str,
                                       cluster: str, cluster_type: str,
                                       position: int, total: int) -> QuestionAnalysis:
        """Анализ одного вопроса"""
        user_prompt = STAGE1_USER.format(
            program=program,
            cluster=cluster,
            cluster_type=cluster_type,
            position=position,
            total=total,
            question=question["text"]
        )

        result = await self.call_llm(STAGE1_SYSTEM, user_prompt, MODELS["stage1"])

        if "error" in result or "dry_run" in result:
            return QuestionAnalysis(
                question_id=question["id"],
                program=program,
                cluster=cluster,
                cluster_type=cluster_type,
                position=position,
                text=question["text"],
                safety_score=0,
                tone="unknown",
                has_labels=False,
                depth_level="unknown",
                issues=["analysis_failed"] if "error" in result else [],
                needs_review=True,
                comment=result.get("error", "dry_run")
            )

        return QuestionAnalysis(
            question_id=question["id"],
            program=program,
            cluster=cluster,
            cluster_type=cluster_type,
            position=position,
            text=question["text"],
            safety_score=result.get("safety_score", 5),
            tone=result.get("tone", "neutral"),
            has_labels=result.get("has_labels", False),
            depth_level=result.get("depth_level", "conscious"),
            issues=result.get("issues", []),
            needs_review=result.get("needs_review", False),
            comment=result.get("comment", "")
        )

    async def run_stage1(self, sample_size: Optional[int] = None):
        """Запуск Этапа 1 — анализ всех вопросов"""
        print("\n" + "═" * 60)
        print("📋 ЭТАП 1: Индивидуальный анализ вопросов")
        print("═" * 60)

        tasks = []
        count = 0

        for program in self.data["programs"]:
            for block in program["blocks"]:
                total_q = len(block["questions"])
                for i, question in enumerate(block["questions"], 1):
                    if sample_size and count >= sample_size:
                        break

                    tasks.append(self.stage1_analyze_question(
                        question=question,
                        program=program["name"],
                        cluster=block["name"],
                        cluster_type=block["type"],
                        position=i,
                        total=total_q
                    ))
                    count += 1

                if sample_size and count >= sample_size:
                    break
            if sample_size and count >= sample_size:
                break

        print(f"🔄 Анализируем {len(tasks)} вопросов...")

        # Батчевая обработка по 20 параллельных запросов
        batch_size = 20
        for i in range(0, len(tasks), batch_size):
            batch = tasks[i:i+batch_size]
            results = await asyncio.gather(*batch)
            self.results["stage1"].extend(results)
            print(f"   Прогресс: {min(i+batch_size, len(tasks))}/{len(tasks)}")

        # Подсчёт статистики
        needs_review = [r for r in self.results["stage1"] if r.needs_review]
        with_issues = [r for r in self.results["stage1"] if r.issues]
        low_safety = [r for r in self.results["stage1"] if r.safety_score < 6]

        print(f"\n📊 Результаты Этапа 1:")
        print(f"   • Всего проанализировано: {len(self.results['stage1'])}")
        print(f"   • Требуют ревью: {len(needs_review)}")
        print(f"   • С проблемами: {len(with_issues)}")
        print(f"   • Низкий safety (<6): {len(low_safety)}")

    # ─────────────────────────────────────────────────────────────────────────
    # ЭТАП 2: Анализ консистентности кластеров
    # ─────────────────────────────────────────────────────────────────────────

    async def stage2_analyze_cluster(self, program: str, block: dict) -> ClusterAnalysis:
        """Анализ одного кластера"""
        questions_text = "\n".join([
            f"{i}. {q['text']}"
            for i, q in enumerate(block["questions"], 1)
        ])

        user_prompt = STAGE2_USER.format(
            program=program,
            cluster=block["name"],
            cluster_type=block["type"],
            questions=questions_text
        )

        result = await self.call_llm(STAGE2_SYSTEM, user_prompt, MODELS["stage2"])

        if "error" in result or "dry_run" in result:
            return ClusterAnalysis(
                cluster_id=block["id"],
                program=program,
                cluster_name=block["name"],
                cluster_type=block["type"],
                question_count=len(block["questions"]),
                flow_score=0,
                depth_progression="unknown",
                tone_consistency="unknown",
                issues=["analysis_failed"] if "error" in result else [],
                problem_transitions=[],
                recommendation=result.get("error", "dry_run")
            )

        return ClusterAnalysis(
            cluster_id=block["id"],
            program=program,
            cluster_name=block["name"],
            cluster_type=block["type"],
            question_count=len(block["questions"]),
            flow_score=result.get("flow_score", 5),
            depth_progression=result.get("depth_progression", "stable"),
            tone_consistency=result.get("tone_consistency", "consistent"),
            issues=result.get("issues", []),
            problem_transitions=result.get("problem_transitions", []),
            recommendation=result.get("recommendation", "")
        )

    async def run_stage2(self, sample_size: Optional[int] = None):
        """Запуск Этапа 2 — анализ кластеров"""
        print("\n" + "═" * 60)
        print("📋 ЭТАП 2: Анализ консистентности кластеров")
        print("═" * 60)

        tasks = []
        count = 0

        for program in self.data["programs"]:
            for block in program["blocks"]:
                if sample_size and count >= sample_size:
                    break
                tasks.append(self.stage2_analyze_cluster(program["name"], block))
                count += 1
            if sample_size and count >= sample_size:
                break

        print(f"🔄 Анализируем {len(tasks)} кластеров...")

        # Батчевая обработка
        batch_size = 10
        for i in range(0, len(tasks), batch_size):
            batch = tasks[i:i+batch_size]
            results = await asyncio.gather(*batch)
            self.results["stage2"].extend(results)
            print(f"   Прогресс: {min(i+batch_size, len(tasks))}/{len(tasks)}")

        # Статистика
        low_flow = [r for r in self.results["stage2"] if r.flow_score < 6]
        chaotic = [r for r in self.results["stage2"] if r.depth_progression == "chaotic"]
        inconsistent = [r for r in self.results["stage2"] if r.tone_consistency == "inconsistent"]

        print(f"\n📊 Результаты Этапа 2:")
        print(f"   • Всего кластеров: {len(self.results['stage2'])}")
        print(f"   • Низкий flow (<6): {len(low_flow)}")
        print(f"   • Хаотичная глубина: {len(chaotic)}")
        print(f"   • Непоследовательный тон: {len(inconsistent)}")

    # ─────────────────────────────────────────────────────────────────────────
    # ЭТАП 3: Генерация переформулировок
    # ─────────────────────────────────────────────────────────────────────────

    async def stage3_reformulate(self, analysis: QuestionAnalysis) -> Reformulation:
        """Генерация переформулировок для проблемного вопроса"""
        user_prompt = STAGE3_USER.format(
            program=analysis.program,
            cluster=analysis.cluster,
            question=analysis.text,
            issues=", ".join(analysis.issues) if analysis.issues else "needs_review"
        )

        result = await self.call_llm(STAGE3_SYSTEM, user_prompt, MODELS["stage3"])

        if "error" in result or "dry_run" in result:
            return Reformulation(
                question_id=analysis.question_id,
                original=analysis.text,
                issues_summary="analysis_failed",
                alternatives=[],
                recommended=0,
                recommendation_reason=result.get("error", "dry_run")
            )

        return Reformulation(
            question_id=analysis.question_id,
            original=result.get("original", analysis.text),
            issues_summary=result.get("issues_summary", ""),
            alternatives=result.get("alternatives", []),
            recommended=result.get("recommended", 1),
            recommendation_reason=result.get("recommendation_reason", "")
        )

    async def run_stage3(self):
        """Запуск Этапа 3 — переформулировки для проблемных"""
        print("\n" + "═" * 60)
        print("📋 ЭТАП 3: Генерация переформулировок")
        print("═" * 60)

        # Отбираем вопросы для переформулировки
        problem_questions = [
            q for q in self.results["stage1"]
            if q.needs_review or q.issues or q.safety_score < 6
        ]

        if not problem_questions:
            print("✅ Нет проблемных вопросов для переформулировки!")
            return

        print(f"🔄 Генерируем переформулировки для {len(problem_questions)} вопросов...")

        tasks = [self.stage3_reformulate(q) for q in problem_questions]

        # Батчевая обработка
        batch_size = 10
        for i in range(0, len(tasks), batch_size):
            batch = tasks[i:i+batch_size]
            results = await asyncio.gather(*batch)
            self.results["stage3"].extend(results)
            print(f"   Прогресс: {min(i+batch_size, len(tasks))}/{len(tasks)}")

        print(f"\n📊 Результаты Этапа 3:")
        print(f"   • Переформулировок создано: {len(self.results['stage3'])}")

    # ─────────────────────────────────────────────────────────────────────────
    # ЭКСПОРТ РЕЗУЛЬТАТОВ
    # ─────────────────────────────────────────────────────────────────────────

    def generate_summary(self):
        """Генерация сводки"""
        self.results["summary"] = {
            "generated_at": datetime.now().isoformat(),
            "total_questions": len(self.results["stage1"]),
            "total_clusters": len(self.results["stage2"]),
            "questions_needing_review": len([q for q in self.results["stage1"] if q.needs_review]),
            "questions_with_issues": len([q for q in self.results["stage1"] if q.issues]),
            "questions_low_safety": len([q for q in self.results["stage1"] if q.safety_score < 6]),
            "clusters_low_flow": len([c for c in self.results["stage2"] if c.flow_score < 6]),
            "clusters_chaotic": len([c for c in self.results["stage2"] if c.depth_progression == "chaotic"]),
            "reformulations_generated": len(self.results["stage3"]),
            "issue_breakdown": {}
        }

        # Подсчёт типов проблем
        issue_counts = {}
        for q in self.results["stage1"]:
            for issue in q.issues:
                issue_counts[issue] = issue_counts.get(issue, 0) + 1
        self.results["summary"]["issue_breakdown"] = issue_counts

    def export_json(self):
        """Экспорт в JSON"""
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

        output = {
            "summary": self.results["summary"],
            "stage1_questions": [asdict(q) for q in self.results["stage1"]],
            "stage2_clusters": [asdict(c) for c in self.results["stage2"]],
            "stage3_reformulations": [asdict(r) for r in self.results["stage3"]]
        }

        output_file = OUTPUT_DIR / f"validation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(output, f, ensure_ascii=False, indent=2)

        print(f"\n💾 JSON сохранён: {output_file}")
        return output_file

    def export_markdown_report(self):
        """Экспорт отчёта в Markdown для вычитки"""
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

        md_lines = [
            "# 📋 Отчёт валидации вопросов Selfology",
            f"\n**Дата:** {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            "",
            "---",
            "",
            "## 📊 Сводка",
            "",
            f"| Метрика | Значение |",
            f"|---------|----------|",
            f"| Всего вопросов | {self.results['summary'].get('total_questions', 0)} |",
            f"| Требуют ревью | {self.results['summary'].get('questions_needing_review', 0)} |",
            f"| С проблемами | {self.results['summary'].get('questions_with_issues', 0)} |",
            f"| Низкий safety | {self.results['summary'].get('questions_low_safety', 0)} |",
            f"| Кластеров с низким flow | {self.results['summary'].get('clusters_low_flow', 0)} |",
            f"| Переформулировок | {self.results['summary'].get('reformulations_generated', 0)} |",
            "",
        ]

        # Разбивка по типам проблем
        if self.results["summary"].get("issue_breakdown"):
            md_lines.extend([
                "### Типы проблем",
                "",
            ])
            for issue, count in sorted(self.results["summary"]["issue_breakdown"].items(),
                                       key=lambda x: -x[1]):
                md_lines.append(f"- **{issue}**: {count}")
            md_lines.append("")

        # Проблемные вопросы
        problem_questions = [q for q in self.results["stage1"] if q.needs_review or q.issues]
        if problem_questions:
            md_lines.extend([
                "---",
                "",
                "## 🚨 Вопросы для ревью",
                "",
            ])

            for q in sorted(problem_questions, key=lambda x: x.safety_score):
                md_lines.extend([
                    f"### {q.program} → {q.cluster}",
                    "",
                    f"**Вопрос:** {q.text}",
                    "",
                    f"- Safety: {q.safety_score}/10",
                    f"- Тон: {q.tone}",
                    f"- Глубина: {q.depth_level}",
                    f"- Проблемы: {', '.join(q.issues) if q.issues else 'needs_review'}",
                    "",
                ])
                if q.comment:
                    md_lines.append(f"> {q.comment}")
                    md_lines.append("")

        # Переформулировки
        if self.results["stage3"]:
            md_lines.extend([
                "---",
                "",
                "## ✏️ Предложенные переформулировки",
                "",
            ])

            for r in self.results["stage3"]:
                md_lines.extend([
                    f"### Оригинал",
                    f"> {r.original}",
                    "",
                    f"**Проблема:** {r.issues_summary}",
                    "",
                    "**Варианты:**",
                    "",
                ])
                for i, alt in enumerate(r.alternatives, 1):
                    rec = " ✅ **РЕКОМЕНДУЕТСЯ**" if i == r.recommended else ""
                    md_lines.append(f"{i}. {alt.get('text', '')}{rec}")
                    md_lines.append(f"   _{alt.get('approach', '')}_")
                    md_lines.append("")

                if r.recommendation_reason:
                    md_lines.append(f"> 💡 {r.recommendation_reason}")
                md_lines.append("")
                md_lines.append("---")
                md_lines.append("")

        # Проблемные кластеры
        problem_clusters = [c for c in self.results["stage2"]
                          if c.flow_score < 6 or c.depth_progression == "chaotic"]
        if problem_clusters:
            md_lines.extend([
                "",
                "## 🔗 Кластеры с проблемами потока",
                "",
            ])

            for c in sorted(problem_clusters, key=lambda x: x.flow_score):
                md_lines.extend([
                    f"### {c.program} → {c.cluster_name}",
                    "",
                    f"- Flow: {c.flow_score}/10",
                    f"- Глубина: {c.depth_progression}",
                    f"- Тон: {c.tone_consistency}",
                    "",
                ])
                if c.problem_transitions:
                    md_lines.append("**Проблемные переходы:**")
                    for pt in c.problem_transitions:
                        md_lines.append(f"- Вопрос {pt.get('from')} → {pt.get('to')}: {pt.get('issue')}")
                    md_lines.append("")
                if c.recommendation:
                    md_lines.append(f"> 💡 {c.recommendation}")
                    md_lines.append("")

        # Сохранение
        output_file = OUTPUT_DIR / f"validation_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        with open(output_file, "w", encoding="utf-8") as f:
            f.write("\n".join(md_lines))

        print(f"📄 Markdown отчёт: {output_file}")
        return output_file

    # ─────────────────────────────────────────────────────────────────────────
    # ГЛАВНЫЙ МЕТОД
    # ─────────────────────────────────────────────────────────────────────────

    async def run(self, stages: list = [1, 2, 3], sample_size: Optional[int] = None):
        """Запуск валидации"""
        self.load_data()

        if 1 in stages:
            await self.run_stage1(sample_size)

        if 2 in stages:
            await self.run_stage2(sample_size if sample_size else None)

        if 3 in stages and self.results["stage1"]:
            await self.run_stage3()

        self.generate_summary()

        json_file = self.export_json()
        md_file = self.export_markdown_report()

        print("\n" + "═" * 60)
        print("✅ ВАЛИДАЦИЯ ЗАВЕРШЕНА")
        print("═" * 60)
        print(f"\n📁 Результаты в: {OUTPUT_DIR}")

        return json_file, md_file


# ═══════════════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════════════

async def main():
    parser = argparse.ArgumentParser(description="AI Question Validator")
    parser.add_argument("--stage", type=int, choices=[1, 2, 3],
                        help="Запустить только определённый этап")
    parser.add_argument("--dry-run", action="store_true",
                        help="Тестовый прогон без API вызовов")
    parser.add_argument("--sample", type=int,
                        help="Ограничить количество вопросов (для теста)")

    args = parser.parse_args()

    validator = QuestionValidator(dry_run=args.dry_run)

    stages = [args.stage] if args.stage else [1, 2, 3]

    await validator.run(stages=stages, sample_size=args.sample)


if __name__ == "__main__":
    asyncio.run(main())
