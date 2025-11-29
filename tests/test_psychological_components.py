"""
Comprehensive Test Suite for Psychological Components
Month 5: Technical Validation

Тестирует все компоненты:
- CognitiveDistortionDetector
- DefenseMechanismDetector
- CoreBeliefsExtractor
- BlindSpotDetector
- TherapeuticAllianceTracker
- GatingMechanism
- AttachmentStyleClassifier
- BreakthroughDetector
- GrowthAreaTracker
- MetaPatternAnalyzer
"""

import sys
import time
import logging
from typing import Dict, List, Any, Tuple
from datetime import datetime

# Добавляем путь к проекту
sys.path.insert(0, '/home/ksnk/microservices/critical/selfology-bot')

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

# Импорты компонентов
from selfology_bot.coach.components.cognitive_distortion_detector import get_distortion_detector
from selfology_bot.coach.components.defense_mechanism_detector import get_defense_detector
from selfology_bot.coach.components.core_beliefs_extractor import get_beliefs_extractor
from selfology_bot.coach.components.blind_spot_detector import get_blind_spot_detector
from selfology_bot.coach.components.therapeutic_alliance_tracker import get_alliance_tracker
from selfology_bot.coach.components.gating_mechanism import get_gating_mechanism
from selfology_bot.coach.components.attachment_style_classifier import get_attachment_classifier
from selfology_bot.coach.components.breakthrough_detector import get_breakthrough_detector
from selfology_bot.coach.components.growth_area_tracker import get_growth_tracker
from selfology_bot.coach.components.meta_pattern_analyzer import get_meta_analyzer


class TestResult:
    """Результат теста"""
    def __init__(self, name: str, passed: bool, duration_ms: float, details: str = ""):
        self.name = name
        self.passed = passed
        self.duration_ms = duration_ms
        self.details = details


class PsychologicalComponentsTester:
    """Комплексный тестер психологических компонентов"""

    def __init__(self):
        # Инициализируем все компоненты
        self.distortion_detector = get_distortion_detector()
        self.defense_detector = get_defense_detector()
        self.beliefs_extractor = get_beliefs_extractor()
        self.blind_spot_detector = get_blind_spot_detector()
        self.alliance_tracker = get_alliance_tracker()
        self.gating = get_gating_mechanism()
        self.attachment_classifier = get_attachment_classifier()
        self.breakthrough_detector = get_breakthrough_detector()
        self.growth_tracker = get_growth_tracker()
        self.meta_analyzer = get_meta_analyzer()

        self.results: List[TestResult] = []
        self.user_id = 12345

    def run_all_tests(self) -> Dict[str, Any]:
        """Запустить все тесты"""
        print("\n" + "=" * 60)
        print("🧪 PSYCHOLOGICAL COMPONENTS TEST SUITE")
        print("=" * 60 + "\n")

        # 1. Тесты когнитивных искажений
        self._test_cognitive_distortions()

        # 2. Тесты защитных механизмов
        self._test_defense_mechanisms()

        # 3. Тесты извлечения убеждений
        self._test_core_beliefs()

        # 4. Тесты слепых зон
        self._test_blind_spots()

        # 5. Тесты терапевтического альянса
        self._test_therapeutic_alliance()

        # 6. Тесты gating механизма
        self._test_gating_mechanism()

        # 7. Тесты классификатора привязанности
        self._test_attachment_classifier()

        # 8. Тесты детектора прорывов
        self._test_breakthrough_detector()

        # 9. Тесты трекера роста
        self._test_growth_tracker()

        # 10. Тесты анализатора мета-паттернов
        self._test_meta_patterns()

        # 11. Интеграционный тест
        self._test_full_integration()

        # 12. Тест производительности
        self._test_performance()

        return self._generate_report()

    def _test_cognitive_distortions(self):
        """Тест детектора когнитивных искажений"""
        print("📊 Testing CognitiveDistortionDetector...")

        test_cases = [
            ("Всегда всё идёт не так, никогда ничего не получается", ["Сверхобобщение", "Предсказание будущего"]),
            ("Я должен быть идеальным во всём", ["Долженствование", "Перфекционизм"]),
            ("Он меня игнорирует, значит я никому не нужен", ["Персонализация", "Чтение мыслей"]),
            ("Я чувствую себя плохо, значит день ужасный", ["Эмоциональное рассуждение"]),
            ("Либо я получу эту работу, либо моя жизнь кончена", ["Черно-белое мышление", "Катастрофизация"])
        ]

        start = time.time()
        detected_count = 0
        expected_count = 0

        for text, expected_types in test_cases:
            result = self.distortion_detector.detect(text)
            detected_types = [d.distortion_type for d in result]

            for expected in expected_types:
                expected_count += 1
                if expected in detected_types:
                    detected_count += 1

        duration = (time.time() - start) * 1000
        accuracy = detected_count / expected_count if expected_count > 0 else 0
        passed = accuracy >= 0.6  # Минимум 60% точности

        self.results.append(TestResult(
            "CognitiveDistortionDetector",
            passed,
            duration,
            f"Accuracy: {accuracy:.0%} ({detected_count}/{expected_count})"
        ))

        status = "✅" if passed else "❌"
        print(f"   {status} Accuracy: {accuracy:.0%}, Time: {duration:.1f}ms\n")

    def _test_defense_mechanisms(self):
        """Тест детектора защитных механизмов"""
        print("🛡️ Testing DefenseMechanismDetector...")

        test_cases = [
            ("Меня это вообще не беспокоит, мне всё равно", ["Отрицание"]),
            ("Это не я виноват, это всё из-за него", ["Проекция"]),
            ("Да ладно, это всего лишь маленькая проблема", ["Рационализация"]),
            ("Я не злюсь на него, просто устала", ["Замещение", "Вытеснение"]),
            ("С логической точки зрения, это неэффективно", ["Интеллектуализация"])
        ]

        start = time.time()
        detected_count = 0
        expected_count = 0

        for text, expected_types in test_cases:
            result = self.defense_detector.detect(text)
            detected_types = [d.mechanism_type for d in result]

            for expected in expected_types:
                expected_count += 1
                if expected in detected_types:
                    detected_count += 1

        duration = (time.time() - start) * 1000
        accuracy = detected_count / expected_count if expected_count > 0 else 0
        passed = accuracy >= 0.6

        self.results.append(TestResult(
            "DefenseMechanismDetector",
            passed,
            duration,
            f"Accuracy: {accuracy:.0%} ({detected_count}/{expected_count})"
        ))

        status = "✅" if passed else "❌"
        print(f"   {status} Accuracy: {accuracy:.0%}, Time: {duration:.1f}ms\n")

    def _test_core_beliefs(self):
        """Тест экстрактора глубинных убеждений"""
        print("💎 Testing CoreBeliefsExtractor...")

        test_cases = [
            "Я никому не нужен и всегда буду одинок",
            "Я не заслуживаю любви и счастья",
            "Люди всегда предают, никому нельзя доверять",
            "Я должен быть идеальным чтобы меня любили",
            "Мир опасен и нужно всегда быть настороже"
        ]

        start = time.time()
        total_beliefs = 0

        for text in test_cases:
            result = self.beliefs_extractor.extract(text)
            total_beliefs += len(result)

        duration = (time.time() - start) * 1000
        avg_beliefs = total_beliefs / len(test_cases)
        passed = avg_beliefs >= 0.5  # Минимум 0.5 убеждения на текст

        self.results.append(TestResult(
            "CoreBeliefsExtractor",
            passed,
            duration,
            f"Avg beliefs per text: {avg_beliefs:.1f}"
        ))

        status = "✅" if passed else "❌"
        print(f"   {status} Avg beliefs: {avg_beliefs:.1f}, Time: {duration:.1f}ms\n")

    def _test_blind_spots(self):
        """Тест детектора слепых зон"""
        print("🔍 Testing BlindSpotDetector...")

        test_cases = [
            ("Я не злюсь, просто немного раздражён. Это нормально.", "avoidance"),
            ("Я хочу близости, но держу дистанцию чтобы не страдать", "contradiction"),
            ("Я опоздал потому что пробки были ужасные", "rationalization"),
            ("Почему она так себя ведёт? Она должна измениться", "deflection")
        ]

        start = time.time()
        detected_count = 0

        for text, expected_type in test_cases:
            result = self.blind_spot_detector.detect(text)
            detected_types = [s.spot_type for s in result]
            if expected_type in detected_types:
                detected_count += 1

        duration = (time.time() - start) * 1000
        accuracy = detected_count / len(test_cases)
        passed = accuracy >= 0.5

        self.results.append(TestResult(
            "BlindSpotDetector",
            passed,
            duration,
            f"Accuracy: {accuracy:.0%} ({detected_count}/{len(test_cases)})"
        ))

        status = "✅" if passed else "❌"
        print(f"   {status} Accuracy: {accuracy:.0%}, Time: {duration:.1f}ms\n")

    def _test_therapeutic_alliance(self):
        """Тест трекера терапевтического альянса"""
        print("🤝 Testing TherapeuticAllianceTracker...")

        test_cases = [
            ("Спасибо вам за поддержку, вы мне очень помогаете", 0.6),  # High alliance
            ("Не знаю, это глупый вопрос", 0.3),  # Low alliance
            ("Хочу разобраться в своих чувствах", 0.5),  # Medium alliance
        ]

        start = time.time()
        correct = 0

        for text, expected_min in test_cases:
            result = self.alliance_tracker.measure(self.user_id, text)
            if result.overall_score >= expected_min - 0.15:  # 15% tolerance
                correct += 1

        duration = (time.time() - start) * 1000
        accuracy = correct / len(test_cases)
        passed = accuracy >= 0.6

        self.results.append(TestResult(
            "TherapeuticAllianceTracker",
            passed,
            duration,
            f"Accuracy: {accuracy:.0%}"
        ))

        status = "✅" if passed else "❌"
        print(f"   {status} Accuracy: {accuracy:.0%}, Time: {duration:.1f}ms\n")

    def _test_gating_mechanism(self):
        """Тест механизма gating"""
        print("🚪 Testing GatingMechanism...")

        test_cases = [
            # (content_type, alliance, days, expected_allowed)
            ("surface", 0.3, 1, True),
            ("cognitive_distortions", 0.5, 5, True),
            ("cognitive_distortions", 0.3, 1, False),
            ("core_beliefs", 0.7, 20, True),
            ("core_beliefs", 0.4, 5, False),
            ("trauma", 0.9, 40, True),
            ("trauma", 0.5, 10, False),
        ]

        start = time.time()
        correct = 0

        for content_type, alliance, days, expected in test_cases:
            result = self.gating.should_surface_content(content_type, alliance, days)
            if result.allowed == expected:
                correct += 1

        duration = (time.time() - start) * 1000
        accuracy = correct / len(test_cases)
        passed = accuracy >= 0.8

        self.results.append(TestResult(
            "GatingMechanism",
            passed,
            duration,
            f"Accuracy: {accuracy:.0%} ({correct}/{len(test_cases)})"
        ))

        status = "✅" if passed else "❌"
        print(f"   {status} Accuracy: {accuracy:.0%}, Time: {duration:.1f}ms\n")

    def _test_attachment_classifier(self):
        """Тест классификатора привязанности"""
        print("💕 Testing AttachmentStyleClassifier...")

        test_cases = [
            ("Я легко сближаюсь с людьми и доверяю им", "secure"),
            ("Боюсь что меня бросят, постоянно нужно подтверждение", "anxious"),
            ("Мне комфортнее одному, не люблю зависеть от других", "avoidant"),
            ("Хочу близости но боюсь её, не знаю чего хочу", "disorganized")
        ]

        start = time.time()
        correct = 0

        for text, expected_style in test_cases:
            result = self.attachment_classifier.assess(self.user_id, text)
            if result.primary_style == expected_style:
                correct += 1

        duration = (time.time() - start) * 1000
        accuracy = correct / len(test_cases)
        passed = accuracy >= 0.5  # 50% для сложной классификации

        self.results.append(TestResult(
            "AttachmentStyleClassifier",
            passed,
            duration,
            f"Accuracy: {accuracy:.0%} ({correct}/{len(test_cases)})"
        ))

        status = "✅" if passed else "❌"
        print(f"   {status} Accuracy: {accuracy:.0%}, Time: {duration:.1f}ms\n")

    def _test_breakthrough_detector(self):
        """Тест детектора прорывов"""
        print("🌟 Testing BreakthroughDetector...")

        test_cases = [
            ("Вдруг понял связь между своим страхом и детством", "insight"),
            ("Наконец-то позволила себе заплакать, такое облегчение", "emotional_release"),
            ("Может я не обязан быть идеальным? Это новая мысль", "belief_shift"),
            ("Признаюсь честно - мне страшно и я устала", "defense_lowering"),
            ("Теперь вижу как всё связано, это имеет смысл", "integration")
        ]

        start = time.time()
        correct = 0

        for text, expected_type in test_cases:
            result = self.breakthrough_detector.detect(text)
            detected_types = [b.breakthrough_type for b in result]
            if expected_type in detected_types:
                correct += 1

        duration = (time.time() - start) * 1000
        accuracy = correct / len(test_cases)
        passed = accuracy >= 0.6

        self.results.append(TestResult(
            "BreakthroughDetector",
            passed,
            duration,
            f"Accuracy: {accuracy:.0%} ({correct}/{len(test_cases)})"
        ))

        status = "✅" if passed else "❌"
        print(f"   {status} Accuracy: {accuracy:.0%}, Time: {duration:.1f}ms\n")

    def _test_growth_tracker(self):
        """Тест трекера зон роста"""
        print("📈 Testing GrowthAreaTracker...")

        user_id = 99999  # Отдельный user для теста

        test_messages = [
            "Ненавижу себя за эту ошибку",  # -> self_compassion area
            "Не могу отказать людям, всегда соглашаюсь",  # -> boundary_setting area
            "Сегодня сказала нет и не чувствую вины",  # -> progress in boundary_setting
        ]

        start = time.time()

        # Обрабатываем сообщения
        for msg in test_messages:
            self.growth_tracker.identify_growth_areas(user_id, msg)
            self.growth_tracker.measure_progress(user_id, msg)

        # Проверяем результаты
        areas = self.growth_tracker.get_user_growth_areas(user_id)
        summary = self.growth_tracker.get_progress_summary(user_id)

        duration = (time.time() - start) * 1000
        passed = len(areas) >= 2 and summary["total_areas"] >= 2

        self.results.append(TestResult(
            "GrowthAreaTracker",
            passed,
            duration,
            f"Areas detected: {len(areas)}, Total: {summary['total_areas']}"
        ))

        status = "✅" if passed else "❌"
        print(f"   {status} Areas: {len(areas)}, Time: {duration:.1f}ms\n")

    def _test_meta_patterns(self):
        """Тест анализатора мета-паттернов"""
        print("🔄 Testing MetaPatternAnalyzer...")

        user_id = 88888  # Отдельный user для теста

        test_messages = [
            "Опять завалена работой, не успеваю к дедлайну",
            "Столько дел накопилось, выгораю",
            "Снова не успела закончить проект вовремя",
        ]

        start = time.time()

        # Обрабатываем сообщения
        for msg in test_messages:
            self.meta_analyzer.analyze(user_id, msg)

        # Проверяем результаты
        patterns = self.meta_analyzer.get_user_patterns(user_id)
        summary = self.meta_analyzer.get_pattern_summary(user_id)

        duration = (time.time() - start) * 1000
        # Должен найти work_overwhelm с несколькими occurrences
        work_pattern = [p for p in patterns if p.pattern_id == "work_overwhelm"]
        passed = len(work_pattern) > 0 and (work_pattern[0].occurrences if work_pattern else 0) >= 2

        self.results.append(TestResult(
            "MetaPatternAnalyzer",
            passed,
            duration,
            f"Patterns: {len(patterns)}, Recurrences: {work_pattern[0].occurrences if work_pattern else 0}"
        ))

        status = "✅" if passed else "❌"
        print(f"   {status} Patterns: {len(patterns)}, Time: {duration:.1f}ms\n")

    def _test_full_integration(self):
        """Интеграционный тест всех компонентов вместе"""
        print("🔗 Testing Full Integration...")

        user_id = 77777
        test_text = """
        Я всегда всё делаю неправильно. Ненавижу себя за это.
        Не могу сказать нет людям, боюсь их обидеть.
        Наверное я никому не нужен на самом деле.
        Вдруг понял почему так происходит - это из детства.
        """

        start = time.time()
        errors = []

        try:
            # Детекция всего
            distortions = self.distortion_detector.detect(test_text)
            defenses = self.defense_detector.detect(test_text)
            beliefs = self.beliefs_extractor.extract(test_text)
            blind_spots = self.blind_spot_detector.detect(test_text)
            alliance = self.alliance_tracker.measure(user_id, test_text)
            breakthroughs = self.breakthrough_detector.detect(test_text)
            self.growth_tracker.identify_growth_areas(user_id, test_text)
            self.meta_analyzer.analyze(user_id, test_text)

            # Проверяем что всё вернуло результаты
            if not distortions:
                errors.append("No distortions detected")
            if not beliefs:
                errors.append("No beliefs extracted")
            if not breakthroughs:
                errors.append("No breakthroughs detected")

        except Exception as e:
            errors.append(f"Exception: {str(e)}")

        duration = (time.time() - start) * 1000
        passed = len(errors) == 0

        self.results.append(TestResult(
            "Full Integration",
            passed,
            duration,
            f"Errors: {len(errors)}" if errors else "All components working together"
        ))

        status = "✅" if passed else "❌"
        print(f"   {status} {len(errors)} errors, Time: {duration:.1f}ms\n")

    def _test_performance(self):
        """Тест производительности"""
        print("⚡ Testing Performance...")

        test_text = "Я чувствую себя очень плохо, не знаю что делать. Всё кажется безнадёжным."
        iterations = 100

        start = time.time()

        for _ in range(iterations):
            self.distortion_detector.detect(test_text)
            self.defense_detector.detect(test_text)
            self.beliefs_extractor.extract(test_text)
            self.breakthrough_detector.detect(test_text)

        duration = (time.time() - start) * 1000
        avg_time = duration / iterations

        # Должно быть меньше 50ms на итерацию
        passed = avg_time < 50

        self.results.append(TestResult(
            "Performance",
            passed,
            duration,
            f"Avg per iteration: {avg_time:.2f}ms ({iterations} iterations)"
        ))

        status = "✅" if passed else "❌"
        print(f"   {status} Avg: {avg_time:.2f}ms/iteration\n")

    def _generate_report(self) -> Dict[str, Any]:
        """Генерация финального отчёта"""
        print("=" * 60)
        print("📊 TEST RESULTS SUMMARY")
        print("=" * 60 + "\n")

        passed_count = sum(1 for r in self.results if r.passed)
        total_count = len(self.results)
        total_time = sum(r.duration_ms for r in self.results)

        print("Individual Results:")
        for result in self.results:
            status = "✅ PASS" if result.passed else "❌ FAIL"
            print(f"  {status} {result.name}")
            print(f"        {result.details}")
            print(f"        Time: {result.duration_ms:.1f}ms\n")

        print("=" * 60)
        overall_passed = passed_count == total_count
        status = "✅ ALL TESTS PASSED" if overall_passed else f"❌ {total_count - passed_count} TESTS FAILED"
        print(f"\n{status}")
        print(f"Passed: {passed_count}/{total_count}")
        print(f"Total Time: {total_time:.1f}ms")
        print(f"Timestamp: {datetime.now().isoformat()}")
        print("=" * 60)

        return {
            "passed": overall_passed,
            "passed_count": passed_count,
            "total_count": total_count,
            "total_time_ms": total_time,
            "results": [
                {
                    "name": r.name,
                    "passed": r.passed,
                    "duration_ms": r.duration_ms,
                    "details": r.details
                }
                for r in self.results
            ]
        }


if __name__ == "__main__":
    tester = PsychologicalComponentsTester()
    report = tester.run_all_tests()

    # Exit code для CI/CD
    exit(0 if report["passed"] else 1)
