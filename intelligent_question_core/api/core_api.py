#!/usr/bin/env python3
"""
CORE API - Полноценное API для работы с умным ядром вопросов
"""

import json
import os
from typing import Dict, List, Any, Optional

class SelfologyQuestionCore:
    """Умное ядро вопросов Selfology с полным API"""
    
    def __init__(self, core_file: str = "selfology_intelligent_core.json"):
        # If core_file is just a filename, look for it in the data/ directory
        if not os.path.sep in core_file:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            core_file = os.path.join(script_dir, '..', 'data', core_file)
        
        with open(core_file, 'r', encoding='utf-8') as f:
            self.core_data = json.load(f)
        
        # Создаем быстрые lookup таблицы
        self.questions_lookup = {
            q["id"]: q for q in self.core_data["questions"]
        }
        
        self.connections = self.core_data["connections"]
        self.search_indexes = self.core_data["search_indexes"]
        self.energy_rules = self.core_data["energy_rules"]
        
        print(f"🧠 Ядро загружено: {len(self.questions_lookup)} вопросов")
    
    # === ОСНОВНЫЕ ФУНКЦИИ ПОИСКА ===
    
    def get_question(self, question_id: str) -> Optional[Dict]:
        """Получить вопрос по ID с полными метаданными"""
        return self.questions_lookup.get(question_id)

    def get_question_by_id(self, question_id: str) -> Optional[Dict]:
        """Alias для get_question - получить вопрос по ID"""
        return self.get_question(question_id)
    
    def search_questions(self, domain: str = None, depth_level: str = None, 
                        energy: str = None, min_safety: int = None) -> List[Dict]:
        """Универсальный поиск вопросов по параметрам"""
        
        # Начинаем со всех вопросов
        result_ids = set(self.questions_lookup.keys())
        
        # Фильтруем по домену
        if domain:
            domain_ids = set(self.search_indexes["by_classification"]["domain"].get(domain, []))
            result_ids = result_ids.intersection(domain_ids)
        
        # Фильтруем по глубине
        if depth_level:
            depth_ids = set(self.search_indexes["by_classification"]["depth_level"].get(depth_level, []))
            result_ids = result_ids.intersection(depth_ids)
        
        # Фильтруем по энергетике
        if energy:
            energy_ids = set(self.search_indexes["by_classification"]["energy_dynamic"].get(energy, []))
            result_ids = result_ids.intersection(energy_ids)
        
        # Фильтруем по безопасности
        if min_safety:
            safe_ids = set()
            for safety_level in range(min_safety, 6):
                level_ids = self.search_indexes["by_psychology"]["safety_level"].get(str(safety_level), [])
                safe_ids.update(level_ids)
            result_ids = result_ids.intersection(safe_ids)
        
        # Возвращаем полные объекты вопросов
        return [self.questions_lookup[qid] for qid in result_ids]
    
    def find_connected_questions(self, question_id: str, 
                               connection_type: str = None) -> List[Dict]:
        """Найти вопросы, связанные с данным"""
        
        if question_id not in self.connections:
            return []
        
        connections = self.connections[question_id]
        
        # Фильтруем по типу связи если указан
        if connection_type:
            connections = [c for c in connections if c["type"] == connection_type]
        
        # Возвращаем полные объекты связанных вопросов
        connected_questions = []
        for connection in connections:
            target_question = self.questions_lookup.get(connection["target"])
            if target_question:
                # Добавляем информацию о связи
                target_with_connection = target_question.copy()
                target_with_connection["connection_info"] = {
                    "type": connection["type"],
                    "strength": connection["strength"],
                    "reasoning": connection.get("reasoning", "")
                }
                connected_questions.append(target_with_connection)
        
        return connected_questions
    
    def build_question_sequence(self, start_question_id: str,
                              target_domains: List[str], 
                              max_length: int = 10) -> List[Dict]:
        """Строит оптимальную последовательность вопросов"""
        
        sequence = []
        current_question_id = start_question_id
        visited = set()
        
        for step in range(max_length):
            if current_question_id in visited:
                break
            
            current_question = self.get_question(current_question_id)
            if not current_question:
                break
            
            sequence.append(current_question)
            visited.add(current_question_id)
            
            # Находим лучший следующий вопрос
            connected = self.find_connected_questions(current_question_id)
            
            # Фильтруем по целевым доменам
            candidates = [
                q for q in connected 
                if q["classification"]["domain"] in target_domains
                and q["id"] not in visited
            ]
            
            if not candidates:
                break
            
            # Выбираем лучшего кандидата (по силе связи)
            next_question = max(candidates, key=lambda x: x["connection_info"]["strength"])
            current_question_id = next_question["id"]
        
        return sequence
    
    def get_processing_recommendation(self, question_id: str) -> Dict[str, Any]:
        """Рекомендует AI модель для обработки вопроса"""
        
        question = self.get_question(question_id)
        if not question:
            return {"error": "Question not found"}
        
        # Извлекаем характеристики
        complexity = question["psychology"]["complexity"]
        depth = question["classification"]["depth_level"]
        domain = question["classification"]["domain"]
        
        # Рекомендуем модель по правилам
        if complexity >= 4 or depth in ["SHADOW", "CORE"]:
            model = "claude-3.5-sonnet"
            reasoning = "Высокая сложность или глубина требует топовой модели"
        elif domain in ["IDENTITY", "EMOTIONS", "SPIRITUALITY"]:
            model = "claude-3.5-sonnet"
            reasoning = "Психологические домены лучше обрабатывает Claude"
        elif complexity <= 2 and depth in ["SURFACE", "CONSCIOUS"]:
            model = "gpt-4o-mini"
            reasoning = "Простые вопросы можно обработать быстрой моделью"
        else:
            model = "gpt-4o"
            reasoning = "Средняя сложность -> балансированная модель"
        
        return {
            "recommended_model": model,
            "reasoning": reasoning,
            "question_characteristics": {
                "complexity": complexity,
                "depth": depth,
                "domain": domain
            }
        }

# Демонстрация использования
def demo_usage():
    """Демонстрирует возможности ядра"""
    
    print("\n🎬 ДЕМОНСТРАЦИЯ ВОЗМОЖНОСТЕЙ ЯДРА:")
    
    try:
        core = SelfologyQuestionCore()
        
        # 1. Поиск вопросов
        identity_questions = core.search_questions(domain="IDENTITY", min_safety=4)
        print(f"📝 Безопасные вопросы про личность: {len(identity_questions)}")
        
        # 2. Поиск связанных вопросов
        if identity_questions:
            first_q = identity_questions[0]
            connected = core.find_connected_questions(first_q["id"])
            print(f"🔗 К вопросу '{first_q['text'][:50]}...' связано: {len(connected)} вопросов")
        
        # 3. Построение последовательности
        if identity_questions:
            sequence = core.build_question_sequence(
                identity_questions[0]["id"], 
                ["IDENTITY", "RELATIONSHIPS"],
                max_length=5
            )
            print(f"🗺️ Построена последовательность из {len(sequence)} вопросов")
        
        # 4. Рекомендация модели
        if identity_questions:
            recommendation = core.get_processing_recommendation(identity_questions[0]["id"])
            print(f"🤖 Рекомендуемая модель: {recommendation['recommended_model']}")
        
    except Exception as e:
        print(f"❌ Ошибка демо: {e}")

if __name__ == "__main__":
    demo_usage()
