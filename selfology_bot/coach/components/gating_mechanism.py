"""
Gating Mechanism - Контроль глубины психологических интервенций

🎯 ЦЕЛЬ: Определить, когда безопасно показывать глубокий контент
🔒 ПРИНЦИП: "Primum non nocere" - прежде всего не навреди
📊 ФАКТОРЫ: Alliance level, время, тип контента, состояние пользователя
"""

import logging
from typing import Dict, Any, Tuple, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


@dataclass
class GatingDecision:
    """Решение о показе контента"""
    allowed: bool
    reason: str
    alternative_action: Optional[str] = None
    wait_conditions: Optional[str] = None


class GatingMechanism:
    """
    Механизм контроля глубины психологических интервенций

    Типы контента по чувствительности:
    - SURFACE: базовые вопросы, поддержка (всегда разрешено)
    - CONSCIOUS: осознанные паттерны (alliance > 0.4)
    - EDGE: граница осознания (alliance > 0.5, days > 7)
    - SHADOW: теневые аспекты (alliance > 0.6, days > 14)
    - UNCONSCIOUS: глубинный материал (alliance > 0.7, days > 21)

    Принципы:
    1. Безопасность превыше инсайтов
    2. Уважение к защитным механизмам
    3. Постепенное углубление
    4. Право пользователя на границы
    """

    # Пороги для разных типов контента
    CONTENT_THRESHOLDS = {
        "surface": {
            "min_alliance": 0.0,
            "min_days": 0,
            "description": "Базовые вопросы и поддержка"
        },
        "conscious": {
            "min_alliance": 0.4,
            "min_days": 0,
            "description": "Осознанные паттерны поведения"
        },
        "cognitive_distortions": {
            "min_alliance": 0.45,
            "min_days": 3,
            "description": "Когнитивные искажения"
        },
        "edge": {
            "min_alliance": 0.5,
            "min_days": 7,
            "description": "Граница осознания"
        },
        "defense_mechanisms": {
            "min_alliance": 0.55,
            "min_days": 10,
            "description": "Защитные механизмы"
        },
        "core_beliefs": {
            "min_alliance": 0.6,
            "min_days": 14,
            "description": "Глубинные убеждения"
        },
        "shadow": {
            "min_alliance": 0.6,
            "min_days": 14,
            "description": "Теневые аспекты личности"
        },
        "blind_spots": {
            "min_alliance": 0.7,
            "min_days": 21,
            "description": "Слепые зоны"
        },
        "unconscious": {
            "min_alliance": 0.7,
            "min_days": 21,
            "description": "Бессознательный материал"
        },
        "trauma": {
            "min_alliance": 0.8,
            "min_days": 30,
            "description": "Травматический опыт"
        }
    }

    # Альтернативные действия
    ALTERNATIVE_ACTIONS = {
        "build_trust": "Сфокусироваться на построении доверия и поддержке",
        "stabilize": "Работать со стабилизацией текущего состояния",
        "surface_work": "Продолжить работу на поверхностном уровне",
        "wait": "Подождать, пока отношения окрепнут"
    }

    def __init__(self):
        """Инициализация механизма гейтинга"""
        logger.info("✅ GatingMechanism initialized")

    def should_surface_content(
        self,
        content_type: str,
        alliance_level: float,
        days_since_start: int,
        user_state: Optional[Dict[str, Any]] = None
    ) -> GatingDecision:
        """
        Определить, можно ли показать данный тип контента

        Args:
            content_type: Тип контента (см. CONTENT_THRESHOLDS)
            alliance_level: Текущий уровень альянса (0.0 - 1.0)
            days_since_start: Дней с начала работы
            user_state: Дополнительное состояние пользователя

        Returns:
            GatingDecision с разрешением и объяснением
        """
        user_state = user_state or {}

        # Проверяем известность типа контента
        if content_type not in self.CONTENT_THRESHOLDS:
            logger.warning(f"Unknown content type: {content_type}")
            content_type = "conscious"  # Fallback

        threshold = self.CONTENT_THRESHOLDS[content_type]
        min_alliance = threshold["min_alliance"]
        min_days = threshold["min_days"]

        # === ПРОВЕРКА КРИЗИСНОГО СОСТОЯНИЯ ===
        if user_state.get("crisis_detected"):
            return GatingDecision(
                allowed=False,
                reason="Обнаружено кризисное состояние - приоритет на стабилизацию",
                alternative_action=self.ALTERNATIVE_ACTIONS["stabilize"]
            )

        # === ПРОВЕРКА АЛЬЯНСА ===
        if alliance_level < min_alliance:
            deficit = min_alliance - alliance_level
            return GatingDecision(
                allowed=False,
                reason=f"Альянс {alliance_level:.2f} < {min_alliance} для {threshold['description']}",
                alternative_action=self.ALTERNATIVE_ACTIONS["build_trust"],
                wait_conditions=f"Нужно повысить альянс на {deficit:.2f}"
            )

        # === ПРОВЕРКА ВРЕМЕНИ ===
        if days_since_start < min_days:
            days_left = min_days - days_since_start
            return GatingDecision(
                allowed=False,
                reason=f"Прошло {days_since_start} дней < {min_days} для {threshold['description']}",
                alternative_action=self.ALTERNATIVE_ACTIONS["surface_work"],
                wait_conditions=f"Ещё {days_left} дней до глубокой работы"
            )

        # === ПРОВЕРКА СОПРОТИВЛЕНИЯ ===
        if user_state.get("high_resistance"):
            return GatingDecision(
                allowed=False,
                reason="Высокое сопротивление - лучше не углублять сейчас",
                alternative_action=self.ALTERNATIVE_ACTIONS["build_trust"]
            )

        # === ПРОВЕРКА УСТАЛОСТИ ===
        fatigue_level = user_state.get("fatigue_level", 0.0)
        if fatigue_level > 0.7 and content_type in ["shadow", "unconscious", "trauma"]:
            return GatingDecision(
                allowed=False,
                reason=f"Высокая усталость ({fatigue_level:.2f}) - слишком глубоко сейчас",
                alternative_action=self.ALTERNATIVE_ACTIONS["stabilize"]
            )

        # === ВСЁ ОК - РАЗРЕШАЕМ ===
        return GatingDecision(
            allowed=True,
            reason=f"Условия выполнены для {threshold['description']} (alliance: {alliance_level:.2f}, days: {days_since_start})"
        )

    def get_max_allowed_depth(
        self,
        alliance_level: float,
        days_since_start: int
    ) -> str:
        """
        Определить максимально допустимую глубину работы

        Returns:
            content_type string
        """
        # Сортируем по строгости (min_alliance + min_days)
        sorted_types = sorted(
            self.CONTENT_THRESHOLDS.items(),
            key=lambda x: (x[1]["min_alliance"], x[1]["min_days"]),
            reverse=True
        )

        for content_type, threshold in sorted_types:
            if (alliance_level >= threshold["min_alliance"] and
                days_since_start >= threshold["min_days"]):
                return content_type

        return "surface"

    def get_readiness_report(
        self,
        alliance_level: float,
        days_since_start: int
    ) -> Dict[str, Any]:
        """
        Получить отчёт о готовности к разным типам контента

        Returns:
            Dict с типами контента и их статусами
        """
        report = {}

        for content_type, threshold in self.CONTENT_THRESHOLDS.items():
            alliance_ok = alliance_level >= threshold["min_alliance"]
            days_ok = days_since_start >= threshold["min_days"]

            if alliance_ok and days_ok:
                status = "ready"
                progress = 1.0
            elif alliance_ok:
                status = "waiting_time"
                progress = days_since_start / threshold["min_days"] if threshold["min_days"] > 0 else 1.0
            elif days_ok:
                status = "need_alliance"
                progress = alliance_level / threshold["min_alliance"] if threshold["min_alliance"] > 0 else 1.0
            else:
                progress = min(
                    days_since_start / threshold["min_days"] if threshold["min_days"] > 0 else 1.0,
                    alliance_level / threshold["min_alliance"] if threshold["min_alliance"] > 0 else 1.0
                )
                status = "not_ready"

            report[content_type] = {
                "status": status,
                "progress": min(1.0, progress),
                "description": threshold["description"],
                "requirements": {
                    "alliance": threshold["min_alliance"],
                    "days": threshold["min_days"]
                }
            }

        return report

    def suggest_intervention_type(
        self,
        detected_content: Dict[str, Any],
        alliance_level: float,
        days_since_start: int
    ) -> Tuple[str, str]:
        """
        Предложить тип интервенции на основе обнаруженного контента

        Args:
            detected_content: Dict с обнаруженными паттернами
            alliance_level: Текущий альянс
            days_since_start: Дней с начала

        Returns:
            (intervention_type, explanation)
        """
        # Определяем максимальную глубину
        max_depth = self.get_max_allowed_depth(alliance_level, days_since_start)

        # Проверяем что есть в обнаруженном контенте
        if detected_content.get("blind_spots") and max_depth in ["blind_spots", "unconscious", "trauma"]:
            return "blind_spot_exploration", "Можно осторожно исследовать слепую зону"

        if detected_content.get("core_beliefs") and max_depth in ["core_beliefs", "shadow", "blind_spots", "unconscious", "trauma"]:
            return "belief_work", "Можно работать с глубинными убеждениями"

        if detected_content.get("defense_mechanisms") and max_depth in ["defense_mechanisms", "core_beliefs", "shadow", "blind_spots", "unconscious", "trauma"]:
            return "defense_awareness", "Можно мягко обратить внимание на защитные механизмы"

        if detected_content.get("cognitive_distortions") and max_depth in ["cognitive_distortions", "edge", "defense_mechanisms", "core_beliefs", "shadow", "blind_spots", "unconscious", "trauma"]:
            return "cognitive_reframing", "Можно работать с когнитивными искажениями"

        # По умолчанию - поддержка и валидация
        return "supportive", "Продолжаем поддерживающую работу"


# Singleton instance
_gating_mechanism = None


def get_gating_mechanism() -> GatingMechanism:
    """Получить singleton экземпляр механизма гейтинга"""
    global _gating_mechanism
    if _gating_mechanism is None:
        _gating_mechanism = GatingMechanism()
    return _gating_mechanism


# === ТЕСТИРОВАНИЕ ===
if __name__ == "__main__":
    gating = GatingMechanism()

    print("🚪 GATING MECHANISM TEST\n" + "=" * 50)

    # Тестовые сценарии
    test_cases = [
        # (alliance, days, content_type, expected)
        (0.3, 1, "cognitive_distortions", "blocked_alliance"),
        (0.5, 5, "cognitive_distortions", "allowed"),
        (0.5, 10, "defense_mechanisms", "blocked_alliance"),
        (0.6, 10, "defense_mechanisms", "allowed"),
        (0.6, 14, "core_beliefs", "allowed"),
        (0.6, 20, "blind_spots", "blocked_alliance"),
        (0.7, 20, "blind_spots", "blocked_time"),
        (0.7, 21, "blind_spots", "allowed"),
        (0.8, 30, "trauma", "allowed"),
    ]

    for alliance, days, content_type, expected in test_cases:
        decision = gating.should_surface_content(content_type, alliance, days)
        status = "✅" if decision.allowed else "❌"
        print(f"\n{status} {content_type} (alliance={alliance}, days={days})")
        print(f"   Reason: {decision.reason}")
        if decision.alternative_action:
            print(f"   Alternative: {decision.alternative_action}")

    # Отчёт о готовности
    print("\n" + "=" * 50)
    print("📊 READINESS REPORT (alliance=0.65, days=15)")
    report = gating.get_readiness_report(0.65, 15)

    for content_type, info in report.items():
        emoji = "✅" if info["status"] == "ready" else "🟡" if info["progress"] > 0.7 else "❌"
        print(f"   {emoji} {content_type}: {info['status']} ({info['progress']*100:.0f}%)")

    print("\n✅ Test completed!")
