"""
Интеграционный тест Phase 2-3 компонентов в ChatCoachService

Проверяет что все 6 компонентов правильно инициализируются и работают:
- Enhanced AI Router
- Adaptive Communication Style
- Deep Question Generator
- Micro Interventions
- Confidence Calculator
- Vector Storytelling
"""
import sys
sys.path.append('/home/ksnk/n8n-enterprise/projects/selfology')

from coach.components.enhanced_ai_router import EnhancedAIRouter
from coach.components.adaptive_communication_style import AdaptiveCommunicationStyle
from coach.components.deep_question_generator import DeepQuestionGenerator
from coach.components.micro_interventions import MicroInterventions
from coach.components.confidence_calculator import ConfidenceCalculator
from coach.components.vector_storytelling import VectorStorytelling


def test_enhanced_router():
    """Тест Enhanced AI Router"""
    print("\n🧪 Тест 1: Enhanced AI Router")

    router = EnhancedAIRouter()

    # Test crisis detection → Claude Sonnet
    crisis_context = {
        'message': 'Я в кризисе, не знаю что делать',
        'crisis_detected': True,
        'existential_question': False,
        'depth_level': 'SHADOW'
    }
    model = router.route(crisis_context)
    assert model == 'claude-3-5-sonnet', f"Expected claude-3-5-sonnet, got {model}"
    print(f"  ✅ Crisis → {model}")

    # Test simple chat → GPT-4o-mini
    simple_context = {
        'message': 'Привет, как дела?',
        'crisis_detected': False,
        'existential_question': False
    }
    model = router.route(simple_context)
    assert model == 'gpt-4o-mini', f"Expected gpt-4o-mini, got {model}"
    print(f"  ✅ Simple → {model}")

    print("  ✅ Enhanced Router работает корректно")


def test_adaptive_style():
    """Тест Adaptive Communication Style"""
    print("\n🧪 Тест 2: Adaptive Communication Style")

    styler = AdaptiveCommunicationStyle()

    # Test high openness → profound depth
    user_context = {
        'personality_profile': {
            'traits': {
                'big_five': {
                    'openness': 0.9,
                    'conscientiousness': 0.5,
                    'extraversion': 0.6,
                    'agreeableness': 0.7,
                    'neuroticism': 0.4
                }
            }
        },
        'current_mood': 'positive',
        'conversation_stage': 'deep_coaching'
    }

    style = styler.determine_style(user_context)
    assert style['depth_level'] in ['deep', 'profound'], f"Expected deep/profound, got {style['depth_level']}"
    print(f"  ✅ High openness → depth={style['depth_level']}")

    # Test format_response
    response = "Это базовый ответ."
    formatted = styler.format_response(response, style)
    assert len(formatted) > 0, "Formatted response is empty"
    print(f"  ✅ Response formatting работает")

    print("  ✅ Adaptive Style работает корректно")


def test_deep_questions():
    """Тест Deep Question Generator"""
    print("\n🧪 Тест 3: Deep Question Generator")

    generator = DeepQuestionGenerator()

    user_context = {
        'big_five': {
            'openness': 0.8,
            'conscientiousness': 0.6
        },
        'conversation_stage': 'deep_coaching'
    }

    message_context = {
        'intent': 'advice_request',
        'domain': 'relationships',
        'insights_detected': True
    }

    questions = generator.generate_questions(user_context, message_context, count=2)
    assert isinstance(questions, list), "Questions should be a list"
    assert len(questions) <= 2, f"Expected max 2 questions, got {len(questions)}"

    if questions:
        print(f"  ✅ Сгенерировано {len(questions)} вопросов:")
        for q in questions:
            print(f"    • {q[:80]}...")

    print("  ✅ Deep Questions работает корректно")


def test_micro_interventions():
    """Тест Micro Interventions"""
    print("\n🧪 Тест 4: Micro Interventions")

    interventions = MicroInterventions()

    # Test reframing
    response = "Вот ваш ответ."
    context = {
        'negative_belief_detected': True,
        'negative_statement': 'Я не могу этого сделать'
    }

    result = interventions.inject(response, context)
    assert len(result) >= len(response), "Intervention should add content"
    print(f"  ✅ Reframing применен (длина: {len(response)} → {len(result)})")

    # Test anchoring
    context_positive = {
        'positive_state_detected': True,
        'positive_state': 'уверенность'
    }

    result = interventions.inject(response, context_positive)
    assert "💫" in result or len(result) >= len(response), "Anchoring should work"
    print(f"  ✅ Anchoring применен")

    print("  ✅ Micro Interventions работает корректно")


def test_confidence_calculator():
    """Тест Confidence Calculator"""
    print("\n🧪 Тест 5: Confidence Calculator")

    calc = ConfidenceCalculator()

    insight = {
        'text': 'Пользователь демонстрирует рост осознанности',
        'type': 'spontaneous_realization',
        'domain': 'emotions'
    }

    user_context = {
        'personality_profile': {
            'traits': {
                'big_five': {
                    'openness': 0.7,
                    'conscientiousness': 0.6
                }
            }
        },
        'insights_history': [
            {'text': 'Previous insight 1'},
            {'text': 'Previous insight 2'}
        ]
    }

    confidence, explanation = calc.calculate(insight, user_context)

    assert 0.0 <= confidence <= 1.0, f"Confidence should be 0-1, got {confidence}"
    assert isinstance(explanation, str), "Explanation should be string"
    assert len(explanation) > 0, "Explanation should not be empty"

    print(f"  ✅ Confidence: {confidence:.2f}")
    print(f"  ✅ Explanation: {explanation[:80]}...")

    # Test formatting
    formatted = calc.format_with_confidence(insight['text'], confidence, explanation)
    assert insight['text'] in formatted, "Original text should be in formatted output"

    print("  ✅ Confidence Calculator работает корректно")


def test_vector_storytelling():
    """Тест Vector Storytelling"""
    print("\n🧪 Тест 6: Vector Storytelling (mock data)")

    storyteller = VectorStorytelling()

    # Mock evolution points
    evolution_points = [
        {
            'big_five': {'openness': 0.5, 'conscientiousness': 0.6},
            'is_milestone': False,
            'delta_magnitude': 0.1
        },
        {
            'big_five': {'openness': 0.7, 'conscientiousness': 0.65},
            'is_milestone': True,
            'delta_magnitude': 0.35,
            'trigger': 'самоанализ',
            'new_quality': 'творческое мышление'
        },
        {
            'big_five': {'openness': 0.75, 'conscientiousness': 0.7},
            'is_milestone': False,
            'delta_magnitude': 0.15
        }
    ]

    # Note: create_narrative is async, but we can test sync parts
    breakthroughs = storyteller._find_breakthroughs(evolution_points)
    assert isinstance(breakthroughs, list), "Breakthroughs should be a list"
    print(f"  ✅ Найдено {len(breakthroughs)} прорывов")

    # Test archetype description
    archetype = storyteller._describe_archetype(evolution_points[1])
    assert isinstance(archetype, str), "Archetype should be string"
    print(f"  ✅ Архетип: {archetype}")

    # Test trajectory
    trajectory = storyteller._describe_trajectory(evolution_points[0], evolution_points[2])
    assert isinstance(trajectory, str), "Trajectory should be string"
    print(f"  ✅ Траектория: {trajectory[:80]}...")

    print("  ✅ Vector Storytelling работает корректно")


def run_all_tests():
    """Запуск всех тестов"""
    print("=" * 70)
    print("🚀 ИНТЕГРАЦИОННОЕ ТЕСТИРОВАНИЕ PHASE 2-3 КОМПОНЕНТОВ")
    print("=" * 70)

    try:
        test_enhanced_router()
        test_adaptive_style()
        test_deep_questions()
        test_micro_interventions()
        test_confidence_calculator()
        test_vector_storytelling()

        print("\n" + "=" * 70)
        print("✅ ВСЕ ТЕСТЫ ПРОЙДЕНЫ УСПЕШНО!")
        print("=" * 70)
        print("\n📊 Результаты:")
        print("  • Enhanced AI Router: ✅")
        print("  • Adaptive Communication Style: ✅")
        print("  • Deep Question Generator: ✅")
        print("  • Micro Interventions: ✅")
        print("  • Confidence Calculator: ✅")
        print("  • Vector Storytelling: ✅")
        print("\n🎉 Phase 2-3 компоненты готовы к использованию!")

        return True

    except AssertionError as e:
        print(f"\n❌ ТЕСТ ПРОВАЛЕН: {e}")
        return False
    except Exception as e:
        print(f"\n❌ ОШИБКА: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
