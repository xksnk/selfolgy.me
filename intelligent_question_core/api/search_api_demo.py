#!/usr/bin/env python3
"""
ДЕМО API для поиска вопросов по индексам
"""

import json

class QuestionSearchAPI:
    """API для быстрого поиска вопросов"""
    
    def __init__(self):
        # Загружаем индексы
        with open('question_search_indexes.json', 'r') as f:
            self.indexes = json.load(f)
        
        # Загружаем вопросы  
        with open('enhanced_questions.json', 'r') as f:
            questions_data = json.load(f)
            self.questions_lookup = {
                q["id"]: q for q in questions_data["questions"]
            }
    
    def search_by_domain(self, domain: str) -> List[Dict]:
        """Поиск вопросов по тематическому домену"""
        question_ids = self.indexes["by_classification"]["domain"].get(domain, [])
        return [self.questions_lookup[qid] for qid in question_ids]
    
    def search_by_complexity(self, min_complexity: int, max_complexity: int) -> List[Dict]:
        """Поиск по уровню сложности"""
        question_ids = []
        for level in range(min_complexity, max_complexity + 1):
            level_questions = self.indexes["by_psychology"]["complexity"].get(str(level), [])
            question_ids.extend(level_questions)
        
        return [self.questions_lookup[qid] for qid in question_ids]
    
    def search_combination(self, domain: str, depth_level: str) -> List[Dict]:
        """Поиск по комбинации параметров"""
        combo_key = f"{domain}+{depth_level}"
        question_ids = self.indexes["combinations"]["domain+depth_level"].get(combo_key, [])
        return [self.questions_lookup[qid] for qid in question_ids]
    
    def search_by_keyword(self, keyword: str) -> List[Dict]:
        """Поиск по ключевому слову"""
        question_ids = self.indexes["keywords"].get(keyword.lower(), [])
        return [self.questions_lookup[qid] for qid in question_ids]

# Примеры использования:
if __name__ == "__main__":
    api = QuestionSearchAPI()
    
    # Найти все вопросы про личность
    identity_questions = api.search_by_domain("IDENTITY")
    print(f"Вопросы про личность: {len(identity_questions)}")
    
    # Найти безопасные вопросы для новичков
    safe_questions = api.search_by_complexity(1, 2)
    print(f"Безопасные вопросы: {len(safe_questions)}")
    
    # Найти глубокие вопросы про отношения
    deep_relationships = api.search_combination("RELATIONSHIPS", "SHADOW")
    print(f"Глубокие вопросы про отношения: {len(deep_relationships)}")
