#!/usr/bin/env python3
"""
Script для хирургического добавления elaborations в intelligent core

🔬 ПРИНЦИП: Минимальные изменения с максимальной точностью
📋 ЗАДАЧА: Сопоставить MD файл с JSON и добавить дополнения
🛡️ БЕЗОПАСНОСТЬ: Backup + валидация целостности
"""

import json
import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple

class ElaborationsUpdater:
    """Обновление elaborate в intelligent core"""
    
    def __init__(self):
        self.base_path = Path(__file__).parent.parent
        self.json_file = self.base_path / "intelligent_question_core/data/selfology_intelligent_core.json"
        self.md_file = self.base_path / "intelligent_question_core/questions_with_elaborations.md"
        
        # Статистика обработки
        self.stats = {
            "md_questions_found": 0,
            "json_questions_total": 0,
            "matches_found": 0,
            "elaborations_added": 0,
            "classification_breakdown": {
                "инструкции_по_ответу": 0,
                "предостережения": 0,
                "призывы_к_действию": 0,
                "психологические_объяснения": 0,
                "связующие_анализы": 0
            }
        }
    
    def run_update(self) -> bool:
        """Главный метод обновления"""
        
        try:
            print("🔬 Начинаю хирургическое обновление elaborations...")
            
            # 1. Создаем backup
            if not self._create_backup():
                return False
            
            # 2. Загружаем данные
            json_data = self._load_json_data()
            md_elaborations = self._parse_md_elaborations()
            
            if not json_data or not md_elaborations:
                return False
            
            print(f"📊 JSON: {len(json_data['questions'])} вопросов")
            print(f"📊 MD: {len(md_elaborations)} вопросов с дополнениями")
            
            # 3. Сопоставляем и обновляем
            updated_json = self._match_and_update(json_data, md_elaborations)
            
            # 4. Валидируем результат
            if not self._validate_updated_json(updated_json):
                print("❌ Валидация не пройдена - откатываемся к backup")
                return False
            
            # 5. Сохраняем обновленный файл
            if self._save_updated_json(updated_json):
                self._print_statistics()
                print("✅ Elaborations успешно добавлены!")
                return True
            else:
                return False
                
        except Exception as e:
            print(f"❌ Ошибка обновления: {e}")
            return False
    
    def _create_backup(self) -> bool:
        """Создание backup файла"""
        
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = self.json_file.with_suffix(f".backup_{timestamp}.json")
            
            shutil.copy2(self.json_file, backup_path)
            print(f"🛡️ Backup создан: {backup_path.name}")
            return True
            
        except Exception as e:
            print(f"❌ Ошибка создания backup: {e}")
            return False
    
    def _load_json_data(self) -> Optional[Dict]:
        """Загрузка JSON данных"""
        
        try:
            with open(self.json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            self.stats["json_questions_total"] = len(data.get("questions", []))
            print(f"📖 JSON загружен: {self.stats['json_questions_total']} вопросов")
            return data
            
        except Exception as e:
            print(f"❌ Ошибка загрузки JSON: {e}")
            return None
    
    def _parse_md_elaborations(self) -> Dict[str, Dict[str, str]]:
        """Парсинг MD файла и извлечение дополнений"""
        
        try:
            with open(self.md_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            elaborations = {}
            
            # Паттерн для поиска вопросов и дополнений
            # Ищем: ### ... Вопрос: "текст вопроса" ... **💡 Дополнение:** текст
            pattern = r'###[^#]*?Вопрос:[^"]*?"([^"]+)".*?\*\*💡[^:]*:\*\*\s*(.*?)(?=\n---|\n###|$)'
            
            matches = re.findall(pattern, content, re.DOTALL | re.MULTILINE)
            
            for question_text, elaboration_text in matches:
                # Очищаем текст вопроса
                clean_question = question_text.strip()
                
                # Очищаем текст дополнения
                clean_elaboration = elaboration_text.strip()
                clean_elaboration = re.sub(r'\n+', '\n', clean_elaboration)  # Убираем лишние переносы
                
                # Классифицируем тип дополнения
                elaboration_type = self._classify_elaboration(clean_elaboration)
                
                elaborations[clean_question] = {
                    "type": elaboration_type,
                    "content": clean_elaboration,
                    "priority": self._determine_priority(clean_elaboration)
                }
                
                self.stats["classification_breakdown"][elaboration_type] += 1
            
            self.stats["md_questions_found"] = len(elaborations)
            print(f"📝 Извлечено {len(elaborations)} дополнений из MD")
            
            return elaborations
            
        except Exception as e:
            print(f"❌ Ошибка парсинга MD: {e}")
            return {}
    
    def _classify_elaboration(self, elaboration_text: str) -> str:
        """Классификация дополнения по типу"""
        
        text_lower = elaboration_text.lower()
        
        # Инструкции по ответу
        if any(word in text_lower for word in [
            "отвечая", "ответить", "напишите", "выпишите", "отнеситесь", 
            "важна каждая деталь", "нет правильного ответа"
        ]):
            return "инструкции_по_ответу"
        
        # Предостережения
        elif any(word in text_lower for word in [
            "не думайте", "не держите в голове", "не стесняйтесь",
            "важно", "осторожно", "внимание"
        ]):
            return "предостережения"
        
        # Призывы к действию
        elif any(word in text_lower for word in [
            "придумайте", "расскажите", "действию", "сделайте",
            "после того как", "инструмент для"
        ]):
            return "призывы_к_действию"
        
        # Психологические объяснения
        elif any(word in text_lower for word in [
            "философский", "представьте", "система", "развернутое объяснение",
            "психологически", "важно для"
        ]):
            return "психологические_объяснения"
        
        # Связующие анализы (если упоминает связи с другими темами)
        elif any(word in text_lower for word in [
            "связано с", "влияет на", "раскрывающие вопросы",
            "в контексте", "также"
        ]):
            return "связующие_анализы"
        
        # Fallback - по умолчанию инструкции
        return "инструкции_по_ответу"
    
    def _determine_priority(self, elaboration_text: str) -> str:
        """Определение приоритета дополнения"""
        
        text_length = len(elaboration_text)
        
        if text_length > 300:
            return "high"
        elif text_length > 100:
            return "medium"
        else:
            return "low"
    
    def _match_and_update(
        self, 
        json_data: Dict[str, Any], 
        md_elaborations: Dict[str, Dict[str, str]]
    ) -> Dict[str, Any]:
        """Сопоставление и хирургическое обновление"""
        
        print("🔍 Начинаю сопоставление вопросов...")
        
        updated_questions = []
        
        for question in json_data["questions"]:
            question_text = question.get("text", "")
            
            # Ищем точное совпадение или близкое
            matching_elaboration = self._find_matching_elaboration(question_text, md_elaborations)
            
            if matching_elaboration:
                # ХИРУРГИЧЕСКОЕ ДОБАВЛЕНИЕ - сразу после "text"
                updated_question = {}
                
                for key, value in question.items():
                    updated_question[key] = value
                    
                    # Добавляем elaborations сразу после text
                    if key == "text":
                        updated_question["elaborations"] = matching_elaboration
                
                updated_questions.append(updated_question)
                self.stats["matches_found"] += 1
                self.stats["elaborations_added"] += 1
                
                print(f"✅ Совпадение: {question.get('id', 'unknown')} - {matching_elaboration['type']}")
                
            else:
                # Оставляем вопрос без изменений
                updated_questions.append(question)
        
        # Обновляем данные сохраняя всю остальную структуру
        updated_json = json_data.copy()
        updated_json["questions"] = updated_questions
        
        return updated_json
    
    def _find_matching_elaboration(
        self, 
        question_text: str, 
        elaborations: Dict[str, Dict[str, str]]
    ) -> Optional[Dict[str, str]]:
        """Поиск соответствующего дополнения для вопроса"""
        
        # 1. Точное совпадение
        if question_text in elaborations:
            return elaborations[question_text]
        
        # 2. Поиск по ключевым словам
        question_lower = question_text.lower()
        question_words = set(re.findall(r'\w+', question_lower))
        
        best_match = None
        best_score = 0.0
        
        for md_question, elaboration in elaborations.items():
            md_lower = md_question.lower()
            md_words = set(re.findall(r'\w+', md_lower))
            
            # Считаем совпадения слов
            common_words = question_words.intersection(md_words)
            if len(question_words) > 0:
                similarity_score = len(common_words) / len(question_words)
                
                # Если схожесть больше 70% - считаем совпадением
                if similarity_score > 0.7 and similarity_score > best_score:
                    best_score = similarity_score
                    best_match = elaboration
        
        return best_match
    
    def _validate_updated_json(self, updated_json: Dict[str, Any]) -> bool:
        """Валидация обновленного JSON"""
        
        try:
            # Проверяем структуру
            required_keys = ["core_metadata", "questions"]
            for key in required_keys:
                if key not in updated_json:
                    print(f"❌ Отсутствует ключ: {key}")
                    return False
            
            # Проверяем что количество вопросов не изменилось
            original_count = self.stats["json_questions_total"]
            new_count = len(updated_json["questions"])
            
            if original_count != new_count:
                print(f"❌ Количество вопросов изменилось: {original_count} → {new_count}")
                return False
            
            # Проверяем что все вопросы имеют обязательные поля
            for i, question in enumerate(updated_json["questions"]):
                required_question_keys = ["id", "text", "classification", "psychology"]
                for key in required_question_keys:
                    if key not in question:
                        print(f"❌ Вопрос #{i} не имеет ключа: {key}")
                        return False
            
            print("✅ JSON валидация пройдена")
            return True
            
        except Exception as e:
            print(f"❌ Ошибка валидации: {e}")
            return False
    
    def _save_updated_json(self, updated_json: Dict[str, Any]) -> bool:
        """Сохранение обновленного JSON"""
        
        try:
            # Обновляем метаданные
            updated_json["core_metadata"]["last_updated"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            updated_json["core_metadata"]["elaborations_added"] = self.stats["elaborations_added"]
            
            # Сохраняем с красивым форматированием
            with open(self.json_file, 'w', encoding='utf-8') as f:
                json.dump(updated_json, f, ensure_ascii=False, indent=2)
            
            print(f"💾 Обновленный JSON сохранен")
            return True
            
        except Exception as e:
            print(f"❌ Ошибка сохранения: {e}")
            return False
    
    def _print_statistics(self):
        """Вывод статистики обновления"""
        
        print("\n📊 СТАТИСТИКА ОБНОВЛЕНИЯ:")
        print(f"📖 Вопросов в MD файле: {self.stats['md_questions_found']}")
        print(f"📖 Вопросов в JSON: {self.stats['json_questions_total']}")
        print(f"🔍 Найдено совпадений: {self.stats['matches_found']}")
        print(f"✅ Добавлено elaborations: {self.stats['elaborations_added']}")
        
        print("\n🏷️ Классификация дополнений:")
        for type_name, count in self.stats["classification_breakdown"].items():
            if count > 0:
                print(f"  • {type_name}: {count}")
        
        coverage = (self.stats['matches_found'] / max(1, self.stats['md_questions_found'])) * 100
        print(f"\n📈 Покрытие: {coverage:.1f}% вопросов из MD найдены в JSON")

def main():
    """Главная функция"""
    
    updater = ElaborationsUpdater()
    
    print("🔬 Selfology Elaborations Updater")
    print("=" * 50)
    
    success = updater.run_update()
    
    if success:
        print("\n🎉 ОБНОВЛЕНИЕ ЗАВЕРШЕНО УСПЕШНО!")
        print("📁 Backup сохранен для безопасности")
        print("✅ JSON файл готов к использованию")
    else:
        print("\n❌ ОБНОВЛЕНИЕ НЕ УДАЛОСЬ")
        print("🛡️ Исходный файл не изменен")
    
    return success

if __name__ == "__main__":
    main()