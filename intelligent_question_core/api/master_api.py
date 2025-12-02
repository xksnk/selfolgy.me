#!/usr/bin/env python3
"""
MASTER API - API для работы с unified master базой вопросов.

Читает из selfology_master.json и предоставляет:
- Программную структуру (программы → кластеры → вопросы)
- Поиск по метаданным
- Совместимость со старым core_api
"""

import json
import os
from typing import Dict, List, Any, Optional
from dataclasses import dataclass


@dataclass
class QuestionResult:
    """Результат поиска вопроса с контекстом"""
    id: str
    text: str
    program: str
    cluster: str
    cluster_type: str  # Foundation/Exploration/Integration
    position: int
    metadata: Optional[Dict] = None
    original_text: Optional[str] = None
    core_id: Optional[str] = None


class SelfologyMasterAPI:
    """API для работы с unified master базой"""

    def __init__(self, master_file: str = "selfology_master.json"):
        # Находим файл
        if not os.path.sep in master_file:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            master_file = os.path.join(script_dir, '..', 'data', master_file)

        with open(master_file, 'r', encoding='utf-8') as f:
            self.data = json.load(f)

        # Создаём индексы для быстрого поиска
        self._build_indexes()

        print(f"📚 Master загружен: {self.stats['programs']} программ, "
              f"{self.stats['clusters']} кластеров, {self.stats['questions']} вопросов")

    def _build_indexes(self):
        """Строит индексы для быстрого поиска"""
        self.questions_by_id = {}
        self.questions_by_program = {}
        self.questions_by_cluster_type = {"Foundation": [], "Exploration": [], "Integration": []}
        self.questions_by_domain = {}
        self.questions_by_depth = {}
        self.programs_list = []
        self.clusters_by_program = {}

        total_questions = 0
        total_clusters = 0

        for prog in self.data["programs"]:
            prog_name = prog["name"]
            self.programs_list.append(prog_name)
            self.questions_by_program[prog_name] = []
            self.clusters_by_program[prog_name] = []

            for block in prog["blocks"]:
                total_clusters += 1
                cluster_name = block["name"]
                cluster_type = block.get("type", "Exploration")
                self.clusters_by_program[prog_name].append({
                    "name": cluster_name,
                    "description": block.get("description", ""),
                    "type": cluster_type,
                    "question_count": len(block["questions"])
                })

                for q in block["questions"]:
                    total_questions += 1
                    q_id = q["id"]

                    # Полный объект с контекстом
                    full_q = {
                        **q,
                        "program": prog_name,
                        "cluster": cluster_name,
                        "cluster_type": cluster_type,
                        "cluster_description": block.get("description", "")
                    }

                    self.questions_by_id[q_id] = full_q
                    self.questions_by_program[prog_name].append(full_q)

                    # По типу кластера
                    if cluster_type in self.questions_by_cluster_type:
                        self.questions_by_cluster_type[cluster_type].append(full_q)

                    # По метаданным (если есть)
                    if q.get("metadata"):
                        meta = q["metadata"]
                        domain = meta.get("classification", {}).get("domain")
                        depth = meta.get("classification", {}).get("depth_level")

                        if domain:
                            if domain not in self.questions_by_domain:
                                self.questions_by_domain[domain] = []
                            self.questions_by_domain[domain].append(full_q)

                        if depth:
                            if depth not in self.questions_by_depth:
                                self.questions_by_depth[depth] = []
                            self.questions_by_depth[depth].append(full_q)

        self.stats = {
            "programs": len(self.programs_list),
            "clusters": total_clusters,
            "questions": total_questions,
            "with_metadata": len([q for q in self.questions_by_id.values() if q.get("metadata")])
        }

    # === ОСНОВНЫЕ МЕТОДЫ ===

    def get_question(self, question_id: str) -> Optional[Dict]:
        """Получить вопрос по ID с полным контекстом"""
        return self.questions_by_id.get(question_id)

    def get_programs(self) -> List[str]:
        """Список всех программ"""
        return self.programs_list.copy()

    def get_program_clusters(self, program_name: str) -> List[Dict]:
        """Кластеры программы с описаниями"""
        return self.clusters_by_program.get(program_name, [])

    def get_program_questions(self, program_name: str) -> List[Dict]:
        """Все вопросы программы"""
        return self.questions_by_program.get(program_name, [])

    def get_questions_by_type(self, cluster_type: str) -> List[Dict]:
        """Вопросы по типу кластера (Foundation/Exploration/Integration)"""
        return self.questions_by_cluster_type.get(cluster_type, [])

    def search_questions(self,
                        program: str = None,
                        cluster_type: str = None,
                        domain: str = None,
                        depth_level: str = None,
                        min_safety: int = None,
                        has_metadata: bool = None) -> List[Dict]:
        """Универсальный поиск вопросов"""

        # Начинаем со всех
        results = list(self.questions_by_id.values())

        # Фильтры
        if program:
            results = [q for q in results if q["program"] == program]

        if cluster_type:
            results = [q for q in results if q["cluster_type"] == cluster_type]

        if domain:
            results = [q for q in results
                      if q.get("metadata", {}).get("classification", {}).get("domain") == domain]

        if depth_level:
            results = [q for q in results
                      if q.get("metadata", {}).get("classification", {}).get("depth_level") == depth_level]

        if min_safety:
            results = [q for q in results
                      if q.get("metadata", {}).get("psychology", {}).get("safety_level", 0) >= min_safety]

        if has_metadata is not None:
            if has_metadata:
                results = [q for q in results if q.get("metadata")]
            else:
                results = [q for q in results if not q.get("metadata")]

        return results

    def get_safe_entry_questions(self, program: str = None) -> List[Dict]:
        """Безопасные вводные вопросы (Foundation, высокий safety)"""
        return self.search_questions(
            program=program,
            cluster_type="Foundation",
            min_safety=4
        )

    def get_deep_questions(self, program: str = None) -> List[Dict]:
        """Глубокие вопросы (Integration или SHADOW/CORE depth)"""
        integration = self.search_questions(program=program, cluster_type="Integration")
        shadow = self.search_questions(program=program, depth_level="SHADOW")
        core = self.search_questions(program=program, depth_level="CORE")

        # Объединяем без дубликатов
        seen_ids = set()
        result = []
        for q in integration + shadow + core:
            if q["id"] not in seen_ids:
                seen_ids.add(q["id"])
                result.append(q)
        return result

    def get_processing_recommendation(self, question_id: str) -> Dict[str, Any]:
        """Рекомендует AI модель для обработки вопроса"""

        question = self.get_question(question_id)
        if not question:
            return {"error": "Question not found"}

        # Берём из метаданных если есть
        meta = question.get("metadata", {})
        hints = meta.get("processing_hints", {})

        if hints.get("recommended_model"):
            return {
                "recommended_model": hints["recommended_model"],
                "reasoning": "Из метаданных core базы",
                "batch_compatible": hints.get("batch_compatible", True),
                "requires_context": hints.get("requires_context", False)
            }

        # Иначе определяем по типу кластера
        cluster_type = question.get("cluster_type", "Exploration")

        if cluster_type == "Integration":
            model = "claude-sonnet-4-20250514"
            reasoning = "Integration кластер требует глубокой модели"
        elif cluster_type == "Foundation":
            model = "gpt-4o-mini"
            reasoning = "Foundation кластер можно обработать быстрой моделью"
        else:
            model = "gpt-4o"
            reasoning = "Exploration кластер - балансированная модель"

        return {
            "recommended_model": model,
            "reasoning": reasoning,
            "batch_compatible": True,
            "requires_context": False
        }

    def get_statistics(self) -> Dict[str, Any]:
        """Статистика базы"""
        return {
            **self.stats,
            "version": self.data.get("version"),
            "unified_at": self.data.get("metadata", {}).get("unified_at"),
            "questions_improved": self.data.get("metadata", {}).get("questions_improved", 0),
            "domains": list(self.questions_by_domain.keys()),
            "depth_levels": list(self.questions_by_depth.keys())
        }


# === СОВМЕСТИМОСТЬ СО СТАРЫМ API ===

class SelfologyQuestionCore(SelfologyMasterAPI):
    """
    Обёртка для совместимости со старым core_api.
    Использует master базу, но предоставляет старый интерфейс.
    """

    def __init__(self, core_file: str = "selfology_master.json"):
        super().__init__(core_file)
        print("⚠️  Используется legacy режим через SelfologyQuestionCore")

    def find_connected_questions(self, question_id: str, connection_type: str = None) -> List[Dict]:
        """
        Legacy метод - в master базе нет connections.
        Возвращает вопросы из того же кластера.
        """
        question = self.get_question(question_id)
        if not question:
            return []

        # Берём вопросы из того же кластера
        same_cluster = [
            q for q in self.questions_by_id.values()
            if q["program"] == question["program"]
            and q["cluster"] == question["cluster"]
            and q["id"] != question_id
        ]

        return same_cluster

    def build_question_sequence(self, start_question_id: str,
                               target_domains: List[str],
                               max_length: int = 10) -> List[Dict]:
        """
        Legacy метод - строит последовательность по кластерам.
        """
        question = self.get_question(start_question_id)
        if not question:
            return []

        # Берём вопросы программы, отсортированные по position
        program_questions = sorted(
            self.get_program_questions(question["program"]),
            key=lambda q: q.get("position", 0)
        )

        # Находим стартовую позицию
        start_idx = 0
        for i, q in enumerate(program_questions):
            if q["id"] == start_question_id:
                start_idx = i
                break

        # Возвращаем последовательность
        return program_questions[start_idx:start_idx + max_length]


def demo_usage():
    """Демонстрация возможностей Master API"""

    print("\n🎬 ДЕМОНСТРАЦИЯ MASTER API:")

    try:
        api = SelfologyMasterAPI()

        # Статистика
        stats = api.get_statistics()
        print(f"\n📊 Статистика:")
        print(f"   Версия: {stats['version']}")
        print(f"   Программ: {stats['programs']}")
        print(f"   Кластеров: {stats['clusters']}")
        print(f"   Вопросов: {stats['questions']}")
        print(f"   С метаданными: {stats['with_metadata']}")

        # Программы
        programs = api.get_programs()
        print(f"\n📚 Программы ({len(programs)}):")
        for p in programs[:5]:
            print(f"   - {p}")
        print("   ...")

        # Поиск
        safe_questions = api.get_safe_entry_questions()
        print(f"\n🛡️ Безопасных вводных вопросов: {len(safe_questions)}")

        deep_questions = api.get_deep_questions()
        print(f"🔮 Глубоких вопросов: {len(deep_questions)}")

        # Пример вопроса
        if safe_questions:
            q = safe_questions[0]
            print(f"\n📝 Пример вопроса:")
            print(f"   ID: {q['id']}")
            print(f"   Текст: {q['text'][:60]}...")
            print(f"   Программа: {q['program']}")
            print(f"   Кластер: {q['cluster']} ({q['cluster_type']})")

            rec = api.get_processing_recommendation(q['id'])
            print(f"   Рекомендуемая модель: {rec['recommended_model']}")

    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    demo_usage()
