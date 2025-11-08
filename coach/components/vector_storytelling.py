"""
Vector Storytelling - Создание нарратива путешествия личности через векторы

Превращает 132 точки эволюции в историю трансформации
"""
from typing import Dict, Any, List, Optional
import logging

logger = logging.getLogger(__name__)

class VectorStorytelling:
    """Создает нарратив путешествия личности"""

    async def create_narrative(self, user_id: int, evolution_points: List[Dict]) -> str:
        """
        Создает историю трансформации

        Args:
            user_id: ID пользователя
            evolution_points: Точки эволюции личности

        Returns:
            Текстовый нарратив путешествия
        """
        if len(evolution_points) < 3:
            return ""

        # Находим ключевые моменты
        start = evolution_points[0]
        current = evolution_points[-1]
        breakthroughs = self._find_breakthroughs(evolution_points)

        # Строим нарратив
        narrative = f"""📖 **Ваше путешествие:**

Вы начали как {self._describe_archetype(start)}.

"""
        # 🔥 FIX: Генерируем УНИКАЛЬНЫЕ описания для каждого breakthrough
        if breakthroughs:
            for i, bt in enumerate(breakthroughs[:3], 1):
                big_five_changes = self._analyze_breakthrough_changes(bt, start if i == 1 else breakthroughs[i-2])

                if big_five_changes:
                    trigger = big_five_changes['trigger_description']
                    new_quality = big_five_changes['quality_gained']
                else:
                    # 🔥 FIX: Fallback с ЧЕЛОВЕЧНЫМ описанием
                    snapshot_id = bt.get('snapshot_id')

                    if snapshot_id and isinstance(snapshot_id, (int, float)) and snapshot_id > 10**12:
                        # Timestamp в миллисекундах → datetime → дата
                        from datetime import datetime
                        timestamp_sec = snapshot_id / 1000
                        date_str = datetime.fromtimestamp(timestamp_sec).strftime('%d %B')  # "5 октября"
                        trigger = f"важный момент {date_str}"
                    else:
                        # Если snapshot_id не timestamp - порядковый номер
                        trigger = f"этап развития №{i}"

                    new_quality = f"более глубокое понимание себя"

                narrative += f"Через {trigger}, вы открыли в себе {new_quality}.\n"

        # Текущее состояние
        narrative += f"\nСейчас вы - {self._describe_archetype(current)}.\n\n"

        # Траектория
        narrative += self._describe_trajectory(start, current)

        return narrative

    def _find_breakthroughs(self, points: List[Dict]) -> List[Dict]:
        """Находит breakthrough моменты"""
        breakthroughs = [
            p for p in points
            if p.get('is_milestone') or p.get('delta_magnitude', 0) > 0.3
        ]
        return sorted(breakthroughs, key=lambda x: x.get('delta_magnitude', 0), reverse=True)

    def _describe_archetype(self, point: Dict) -> str:
        """Описывает архетип на основе Big Five"""
        big_five = point.get('big_five', {})
        o = big_five.get('openness', 0.5)
        c = big_five.get('conscientiousness', 0.5)

        if o > 0.7 and c > 0.7:
            return "Организованный Исследователь"
        elif o > 0.7:
            return "Творческий Мечтатель"
        elif c > 0.7:
            return "Надежный Организатор"
        else:
            return "Гармоничная Личность"

    def _analyze_breakthrough_changes(self, current: Dict, previous: Dict) -> Optional[Dict]:
        """
        Анализирует КОНКРЕТНЫЕ изменения между двумя точками эволюции

        🔥 FIX: Генерирует уникальные описания на основе реальных изменений Big Five
        """
        current_bf = current.get('big_five', {})
        previous_bf = previous.get('big_five', {})

        if not current_bf or not previous_bf:
            return None

        # Находим черту с максимальным изменением
        max_change = 0
        max_trait = None

        for trait in ['openness', 'conscientiousness', 'extraversion', 'agreeableness', 'neuroticism']:
            delta = current_bf.get(trait, 0.5) - previous_bf.get(trait, 0.5)
            if abs(delta) > max_change:
                max_change = abs(delta)
                max_trait = (trait, delta)

        if not max_trait or max_change < 0.05:
            return None

        trait_name, delta = max_trait

        # Словарь описаний изменений
        trait_descriptions = {
            'openness': {
                'positive': ('открытие для нового опыта', 'творческое мышление и гибкость'),
                'negative': ('фокусировку на проверенных путях', 'практичность')
            },
            'conscientiousness': {
                'positive': ('развитие структуры и дисциплины', 'организованность'),
                'negative': ('спонтанность', 'гибкость в планах')
            },
            'extraversion': {
                'positive': ('расширение социальных связей', 'энергию общения'),
                'negative': ('углубление во внутренний мир', 'способность к рефлексии')
            },
            'agreeableness': {
                'positive': ('развитие эмпатии', 'гармонию в отношениях'),
                'negative': ('здоровые границы', 'способность говорить "нет"')
            },
            'neuroticism': {
                'positive': ('чувствительность к эмоциям', 'внимание к деталям'),
                'negative': ('эмоциональную стабильность', 'внутреннее спокойствие')
            }
        }

        direction = 'positive' if delta > 0 else 'negative'
        trigger, quality = trait_descriptions.get(trait_name, {}).get(direction, ('изменение', 'новое понимание'))

        return {
            'trigger_description': trigger,
            'quality_gained': quality
        }

    def _describe_trajectory(self, start: Dict, current: Dict) -> str:
        """Описывает траекторию изменений"""
        start_bf = start.get('big_five', {})
        current_bf = current.get('big_five', {})

        # 🔥 FIX: Словарь переводов на русский
        trait_names = {
            "openness": "открытость новому",
            "conscientiousness": "организованность",
            "extraversion": "общительность",
            "agreeableness": "доброжелательность",
            "neuroticism": "эмоциональная нестабильность"
        }

        changes = []
        for trait in ['openness', 'conscientiousness', 'extraversion', 'agreeableness', 'neuroticism']:
            delta = current_bf.get(trait, 0.5) - start_bf.get(trait, 0.5)
            if abs(delta) > 0.15:
                direction = "растет" if delta > 0 else "снижается"
                trait_ru = trait_names.get(trait, trait)  # 🔥 ПЕРЕВОД!

                # 🔥 FIX: Понятное описание величины изменения
                magnitude_percent = int(abs(delta) * 100)

                if abs(delta) > 0.30:
                    significance = "значительно"
                elif abs(delta) > 0.20:
                    significance = "заметно"
                else:
                    significance = "немного"

                changes.append(f"- Ваша {trait_ru} {significance} {direction} (на {magnitude_percent}%)")

        if changes:
            return "**Траектория показывает:**\n" + "\n".join(changes)
        return "Вы находитесь в стабильной фазе развития."
