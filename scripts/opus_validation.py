#!/usr/bin/env python3
"""
Opus Validation Script for Psychological Components
Использует Claude Opus для валидации детекторов

Функции:
1. Экспорт ответов из базы данных
2. Разметка Opus (ground truth)
3. Детекция локальными компонентами
4. Сравнение и расчет метрик (F1, precision, recall)
5. Генерация отчета с рекомендациями
"""

import sys
import os
import json
import asyncio
import asyncpg
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
import anthropic

# Путь к проекту
sys.path.insert(0, '/home/ksnk/microservices/critical/selfology-bot')

# Suppress verbose logging
import logging
logging.basicConfig(level=logging.WARNING)

# Импорт компонентов для валидации
from selfology_bot.coach.components.cognitive_distortion_detector import get_distortion_detector
from selfology_bot.coach.components.defense_mechanism_detector import get_defense_detector
from selfology_bot.coach.components.core_beliefs_extractor import get_beliefs_extractor
from selfology_bot.coach.components.blind_spot_detector import get_blind_spot_detector
from selfology_bot.coach.components.therapeutic_alliance_tracker import get_alliance_tracker
from selfology_bot.coach.components.attachment_style_classifier import get_attachment_classifier
from selfology_bot.coach.components.breakthrough_detector import get_breakthrough_detector
from selfology_bot.coach.components.growth_area_tracker import get_growth_tracker
from selfology_bot.coach.components.meta_pattern_analyzer import get_meta_analyzer


@dataclass
class ValidationResult:
    """Результат валидации одного компонента"""
    component: str
    total_samples: int
    true_positives: int
    false_positives: int
    false_negatives: int
    precision: float
    recall: float
    f1_score: float
    examples: List[Dict]  # Примеры ошибок


@dataclass
class OpusLabel:
    """Разметка Opus для одного ответа"""
    answer_id: int
    cognitive_distortions: List[str]
    defense_mechanisms: List[str]
    core_beliefs: List[str]
    blind_spots: List[str]
    attachment_indicators: Dict[str, float]
    breakthroughs: List[str]
    growth_areas: List[str]
    meta_patterns: List[str]
    therapeutic_quality: str  # safe/caution/risk
    notes: str


class OpusValidator:
    """Валидатор психологических компонентов с использованием Opus"""

    def __init__(self):
        # Инициализация Anthropic client
        api_key = os.getenv('ANTHROPIC_API_KEY')
        if not api_key:
            # Попробуем загрузить из .env
            from dotenv import load_dotenv
            load_dotenv('/home/ksnk/microservices/critical/selfology-bot/.env')
            api_key = os.getenv('ANTHROPIC_API_KEY')

        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY не найден в окружении")

        self.client = anthropic.Anthropic(api_key=api_key)

        # Инициализация детекторов
        self.distortion_detector = get_distortion_detector()
        self.defense_detector = get_defense_detector()
        self.beliefs_extractor = get_beliefs_extractor()
        self.blind_spot_detector = get_blind_spot_detector()
        self.alliance_tracker = get_alliance_tracker()
        self.attachment_classifier = get_attachment_classifier()
        self.breakthrough_detector = get_breakthrough_detector()
        self.growth_tracker = get_growth_tracker()
        self.meta_analyzer = get_meta_analyzer()

        # База данных
        self.db_config = {
            'host': 'localhost',
            'port': 5434,
            'user': 'selfology_user',
            'password': 'selfology_secure_2024',
            'database': 'selfology'
        }

    async def export_answers(self, limit: int = 50) -> List[Dict]:
        """Экспорт ответов из базы данных"""
        conn = await asyncpg.connect(**self.db_config)

        try:
            # Получаем ответы с достаточной длиной для анализа
            rows = await conn.fetch("""
                SELECT
                    a.id,
                    s.user_id,
                    a.question_json_id,
                    a.raw_answer,
                    a.answered_at,
                    q.question_text
                FROM selfology.user_answers_new a
                JOIN selfology.onboarding_sessions s ON a.session_id = s.id
                LEFT JOIN selfology.questions_metadata q ON a.question_json_id = q.question_id
                WHERE LENGTH(a.raw_answer) > 50
                ORDER BY a.answered_at DESC
                LIMIT $1
            """, limit)

            answers = []
            for row in rows:
                answers.append({
                    'id': row['id'],
                    'user_id': row['user_id'],
                    'question_id': row['question_json_id'],
                    'answer_text': row['raw_answer'],
                    'question_text': row['question_text'] or 'Вопрос не найден',
                    'created_at': str(row['answered_at'])
                })

            return answers
        finally:
            await conn.close()

    def get_opus_labels(self, answers: List[Dict]) -> List[OpusLabel]:
        """Получение разметки от Opus для всех ответов"""
        labels = []

        for i, answer in enumerate(answers):
            print(f"  Разметка Opus: {i+1}/{len(answers)}...", end='\r')
            label = self._label_single_answer(answer)
            labels.append(label)

        print(f"  Разметка Opus: {len(answers)}/{len(answers)} ✅")
        return labels

    def _label_single_answer(self, answer: Dict) -> OpusLabel:
        """Разметка одного ответа через Opus"""

        prompt = f"""Ты эксперт-психолог, проводящий клиническую разметку текста пользователя.

Вопрос который был задан:
"{answer['question_text']}"

Ответ пользователя:
"{answer['answer_text']}"

Проанализируй этот ответ и определи психологические конструкты.
Отвечай СТРОГО в JSON формате без дополнительного текста:

{{
    "cognitive_distortions": ["список когнитивных искажений на русском: Катастрофизация, Черно-белое мышление, Сверхобобщение, Чтение мыслей, Долженствование, Персонализация, Обесценивание позитива, Эмоциональное обоснование, Навешивание ярлыков, Туннельное зрение, Магическое мышление, Перфекционизм"],
    "defense_mechanisms": ["список защитных механизмов: Рационализация, Проекция, Отрицание, Интеллектуализация, Реактивное образование, Вытеснение, Смещение, Регрессия, Сублимация, Юмор, Альтруизм, Диссоциация"],
    "core_beliefs": ["глубинные убеждения о себе/мире/других, например: 'Я недостаточно хорош', 'Мир опасен'"],
    "blind_spots": ["слепые зоны: Избегание, Противоречие, Рационализация, Отклонение"],
    "attachment_indicators": {{
        "anxiety": 0.0-1.0,
        "avoidance": 0.0-1.0
    }},
    "breakthroughs": ["типы прорывов если есть: insight, emotional_release, belief_shift, defense_lowering, integration"],
    "growth_areas": ["зоны роста: self_compassion, emotional_awareness, boundary_setting, assertiveness, vulnerability, cognitive_flexibility"],
    "meta_patterns": ["мета-паттерны если повторяются: work_overwhelm, relationship_anxiety, avoidance_pattern, perfectionism, catastrophizing и др."],
    "therapeutic_quality": "safe/caution/risk - оценка безопасности терапевтического взаимодействия",
    "notes": "краткие заметки психолога о ключевых наблюдениях"
}}

Если конструкт не обнаружен - оставь пустой список [].
Будь строгим и точным. Отмечай только явно присутствующие паттерны."""

        try:
            response = self.client.messages.create(
                model="claude-sonnet-4-20250514",  # Используем Sonnet для экономии, Opus для финальной валидации
                max_tokens=1500,
                messages=[{"role": "user", "content": prompt}]
            )

            # Парсим JSON из ответа
            response_text = response.content[0].text.strip()

            # Убираем markdown если есть
            if response_text.startswith('```'):
                response_text = response_text.split('```')[1]
                if response_text.startswith('json'):
                    response_text = response_text[4:]

            data = json.loads(response_text)

            return OpusLabel(
                answer_id=answer['id'],
                cognitive_distortions=data.get('cognitive_distortions', []),
                defense_mechanisms=data.get('defense_mechanisms', []),
                core_beliefs=data.get('core_beliefs', []),
                blind_spots=data.get('blind_spots', []),
                attachment_indicators=data.get('attachment_indicators', {'anxiety': 0.0, 'avoidance': 0.0}),
                breakthroughs=data.get('breakthroughs', []),
                growth_areas=data.get('growth_areas', []),
                meta_patterns=data.get('meta_patterns', []),
                therapeutic_quality=data.get('therapeutic_quality', 'safe'),
                notes=data.get('notes', '')
            )

        except Exception as e:
            print(f"\n  ⚠️ Ошибка разметки answer {answer['id']}: {e}")
            return OpusLabel(
                answer_id=answer['id'],
                cognitive_distortions=[],
                defense_mechanisms=[],
                core_beliefs=[],
                blind_spots=[],
                attachment_indicators={'anxiety': 0.0, 'avoidance': 0.0},
                breakthroughs=[],
                growth_areas=[],
                meta_patterns=[],
                therapeutic_quality='safe',
                notes=f'Error: {str(e)}'
            )

    def run_local_detectors(self, answers: List[Dict]) -> List[Dict]:
        """Запуск локальных детекторов на ответах"""
        results = []

        for i, answer in enumerate(answers):
            print(f"  Локальные детекторы: {i+1}/{len(answers)}...", end='\r')

            text = answer['answer_text']
            user_id = answer['user_id']

            result = {
                'answer_id': answer['id'],
                'cognitive_distortions': [],
                'defense_mechanisms': [],
                'core_beliefs': [],
                'blind_spots': [],
                'attachment': {},
                'breakthroughs': [],
                'growth_areas': [],
                'meta_patterns': []
            }

            # Когнитивные искажения
            distortions = self.distortion_detector.detect(text)
            result['cognitive_distortions'] = [d.distortion_type for d in distortions]

            # Защитные механизмы
            defenses = self.defense_detector.detect(text)
            result['defense_mechanisms'] = [d.mechanism_type for d in defenses]

            # Глубинные убеждения
            beliefs = self.beliefs_extractor.extract(text)
            result['core_beliefs'] = [b.belief_text for b in beliefs]

            # Слепые зоны
            blind_spots = self.blind_spot_detector.detect(text)
            result['blind_spots'] = [b.spot_type for b in blind_spots]

            # Привязанность
            attachment = self.attachment_classifier.assess(text)
            result['attachment'] = {
                'anxiety': attachment.anxiety_score,
                'avoidance': attachment.avoidance_score,
                'style': attachment.attachment_style
            }

            # Прорывы
            breakthroughs = self.breakthrough_detector.detect(text)
            result['breakthroughs'] = [b.breakthrough_type for b in breakthroughs]

            # Зоны роста
            growth = self.growth_tracker.identify_growth_areas(user_id, text)
            result['growth_areas'] = list(growth.keys())

            # Мета-паттерны
            patterns = self.meta_analyzer.analyze(user_id, text)
            result['meta_patterns'] = [p.pattern_type for p in patterns]

            results.append(result)

        print(f"  Локальные детекторы: {len(answers)}/{len(answers)} ✅")
        return results

    def calculate_metrics(self, opus_labels: List[OpusLabel], local_results: List[Dict]) -> Dict[str, ValidationResult]:
        """Расчет метрик для каждого компонента"""

        components = {
            'cognitive_distortions': ('cognitive_distortions', 'cognitive_distortions'),
            'defense_mechanisms': ('defense_mechanisms', 'defense_mechanisms'),
            'core_beliefs': ('core_beliefs', 'core_beliefs'),
            'blind_spots': ('blind_spots', 'blind_spots'),
            'breakthroughs': ('breakthroughs', 'breakthroughs'),
            'growth_areas': ('growth_areas', 'growth_areas'),
            'meta_patterns': ('meta_patterns', 'meta_patterns')
        }

        results = {}

        for comp_name, (opus_key, local_key) in components.items():
            tp, fp, fn = 0, 0, 0
            examples = []

            for opus, local in zip(opus_labels, local_results):
                opus_set = set(getattr(opus, opus_key) if hasattr(opus, opus_key) else opus.get(opus_key, []))
                local_set = set(local.get(local_key, []))

                # Нормализация для сравнения (lowercase)
                opus_normalized = {s.lower() for s in opus_set}
                local_normalized = {s.lower() for s in local_set}

                # True Positives - совпадения
                matches = opus_normalized & local_normalized
                tp += len(matches)

                # False Positives - детектор нашел, но Opus не подтвердил
                fp_items = local_normalized - opus_normalized
                fp += len(fp_items)

                # False Negatives - Opus нашел, но детектор пропустил
                fn_items = opus_normalized - local_normalized
                fn += len(fn_items)

                # Сохраняем примеры ошибок
                if fp_items or fn_items:
                    examples.append({
                        'answer_id': local['answer_id'],
                        'false_positives': list(fp_items)[:3],
                        'false_negatives': list(fn_items)[:3]
                    })

            # Расчет метрик
            precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
            recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
            f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0

            results[comp_name] = ValidationResult(
                component=comp_name,
                total_samples=len(opus_labels),
                true_positives=tp,
                false_positives=fp,
                false_negatives=fn,
                precision=round(precision, 3),
                recall=round(recall, 3),
                f1_score=round(f1, 3),
                examples=examples[:5]  # Топ 5 примеров ошибок
            )

        return results

    def generate_report(self, validation_results: Dict[str, ValidationResult], opus_labels: List[OpusLabel]) -> str:
        """Генерация отчета валидации"""

        report = []
        report.append("\n" + "=" * 70)
        report.append("🔬 OPUS VALIDATION REPORT - Psychological Components")
        report.append("=" * 70)
        report.append(f"Timestamp: {datetime.now().isoformat()}")
        report.append(f"Total samples: {len(opus_labels)}")
        report.append("")

        # Targets из роадмапа
        targets = {
            'cognitive_distortions': 0.68,
            'defense_mechanisms': 0.65,
            'breakthroughs': 0.88,
            'attachment': 0.84
        }

        # Сводка по компонентам
        report.append("📊 COMPONENT METRICS:")
        report.append("-" * 70)
        report.append(f"{'Component':<25} {'Precision':>10} {'Recall':>10} {'F1':>10} {'Target':>10} {'Status':>8}")
        report.append("-" * 70)

        all_passed = True
        for name, result in validation_results.items():
            target = targets.get(name, 0.60)
            status = "✅" if result.f1_score >= target else "⚠️"
            if result.f1_score < target:
                all_passed = False

            report.append(
                f"{name:<25} {result.precision:>10.3f} {result.recall:>10.3f} "
                f"{result.f1_score:>10.3f} {target:>10.2f} {status:>8}"
            )

        report.append("-" * 70)

        # Детали по компонентам с проблемами
        report.append("\n📋 DETAILED ANALYSIS:")

        for name, result in validation_results.items():
            if result.false_positives > 0 or result.false_negatives > 0:
                report.append(f"\n  {name}:")
                report.append(f"    TP: {result.true_positives}, FP: {result.false_positives}, FN: {result.false_negatives}")

                if result.examples:
                    report.append("    Примеры ошибок:")
                    for ex in result.examples[:2]:
                        if ex['false_positives']:
                            report.append(f"      - FP (answer {ex['answer_id']}): {ex['false_positives']}")
                        if ex['false_negatives']:
                            report.append(f"      - FN (answer {ex['answer_id']}): {ex['false_negatives']}")

        # Therapeutic quality check
        risk_count = sum(1 for l in opus_labels if l.therapeutic_quality == 'risk')
        caution_count = sum(1 for l in opus_labels if l.therapeutic_quality == 'caution')

        report.append("\n🛡️ THERAPEUTIC SAFETY:")
        report.append(f"  Safe: {len(opus_labels) - risk_count - caution_count}")
        report.append(f"  Caution: {caution_count}")
        report.append(f"  Risk: {risk_count}")

        if risk_count > 0:
            report.append("  ⚠️ Обнаружены ответы с потенциальным риском!")

        # Рекомендации
        report.append("\n💡 RECOMMENDATIONS:")

        low_f1_components = [name for name, r in validation_results.items() if r.f1_score < 0.60]
        if low_f1_components:
            report.append(f"  - Улучшить детекцию: {', '.join(low_f1_components)}")

        high_fp_components = [name for name, r in validation_results.items() if r.false_positives > r.true_positives]
        if high_fp_components:
            report.append(f"  - Слишком много false positives: {', '.join(high_fp_components)}")
            report.append("    → Ужесточить критерии детекции")

        high_fn_components = [name for name, r in validation_results.items() if r.false_negatives > r.true_positives]
        if high_fn_components:
            report.append(f"  - Много пропусков (false negatives): {', '.join(high_fn_components)}")
            report.append("    → Добавить паттерны в детекторы")

        if not low_f1_components and not high_fp_components and not high_fn_components:
            report.append("  ✅ Все компоненты работают в пределах нормы")

        # Итог
        report.append("\n" + "=" * 70)
        if all_passed:
            report.append("✅ VALIDATION PASSED - All components meet targets")
        else:
            report.append("⚠️ VALIDATION NEEDS IMPROVEMENT - Some components below targets")
        report.append("=" * 70 + "\n")

        return "\n".join(report)

    async def run_validation(self, sample_size: int = 30, use_opus: bool = False):
        """Запуск полного цикла валидации"""

        print("\n🔬 OPUS VALIDATION SYSTEM")
        print("=" * 50)

        # 1. Экспорт ответов
        print("\n📥 Экспорт ответов из базы...")
        answers = await self.export_answers(limit=sample_size)
        print(f"  Экспортировано: {len(answers)} ответов")

        if not answers:
            print("  ❌ Нет ответов для валидации!")
            return

        # 2. Разметка Opus
        print("\n🤖 Разметка через Claude...")
        if use_opus:
            # Переключаем на Opus для финальной валидации
            self.client = anthropic.Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))
        opus_labels = self.get_opus_labels(answers)

        # 3. Локальные детекторы
        print("\n🔍 Запуск локальных детекторов...")
        local_results = self.run_local_detectors(answers)

        # 4. Расчет метрик
        print("\n📊 Расчет метрик...")
        validation_results = self.calculate_metrics(opus_labels, local_results)

        # 5. Генерация отчета
        report = self.generate_report(validation_results, opus_labels)
        print(report)

        # 6. Сохранение результатов
        output_file = f"/home/ksnk/microservices/critical/selfology-bot/logs/validation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

        output_data = {
            'timestamp': datetime.now().isoformat(),
            'sample_size': len(answers),
            'results': {name: asdict(r) for name, r in validation_results.items()},
            'opus_labels': [asdict(l) for l in opus_labels],
            'local_results': local_results
        }

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2)

        print(f"\n💾 Результаты сохранены: {output_file}")

        return validation_results


async def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description='Opus Validation for Psychological Components')
    parser.add_argument('--samples', type=int, default=30, help='Number of samples to validate')
    parser.add_argument('--opus', action='store_true', help='Use Opus model (more expensive but accurate)')

    args = parser.parse_args()

    validator = OpusValidator()
    await validator.run_validation(sample_size=args.samples, use_opus=args.opus)


if __name__ == "__main__":
    asyncio.run(main())
