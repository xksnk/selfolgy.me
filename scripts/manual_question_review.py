#!/usr/bin/env python3
"""
Скрипт для ручной проверки вопросов программ Selfology
Позволяет последовательно проверять вопросы, одобрять, отклонять, редактировать и перемещать их
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import shutil

# Константы
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "intelligent_question_core" / "data"
QUESTIONS_FILE = DATA_DIR / "selfology_final_sequenced.json"
BACKUP_DIR = BASE_DIR / "backups"
LOG_DIR = BASE_DIR / "logs"
LOG_FILE = LOG_DIR / "question_review.log"

# Переводы классификаций
DOMAIN_TRANSLATIONS = {
    "IDENTITY": "Идентичность",
    "WORK": "Работа",
    "RELATIONSHIPS": "Отношения",
    "EMOTIONS": "Эмоции",
    "VALUES": "Ценности",
    "GOALS": "Цели",
    "FEARS": "Страхи",
    "GROWTH": "Рост",
    "PAST": "Прошлое",
    "SPIRITUALITY": "Духовность",
    "FUTURE": "Будущее",
    "BODY": "Тело",
    "CREATIVITY": "Творчество"
}

DEPTH_TRANSLATIONS = {
    "SURFACE": "Поверхностное",
    "CONSCIOUS": "Сознательное",
    "EDGE": "Граница",
    "SHADOW": "Тень",
    "CORE": "Ядро"
}

ENERGY_TRANSLATIONS = {
    "OPENING": "Открывающая",
    "NEUTRAL": "Нейтральная",
    "PROCESSING": "Обрабатывающая",
    "HEAVY": "Тяжелая",
    "HEALING": "Исцеляющая"
}

STAGE_TRANSLATIONS = {
    "ENTRY": "Вход",
    "EXPLORING": "Исследование",
    "DEEPENING": "Углубление",
    "INTEGRATING": "Интеграция",
    "TRANSFORMING": "Трансформация"
}

# Иконки статусов
STATUS_ICONS = {
    "approved": "✅",
    "doubt": "❓",
    "rejected": "❌",
    "wrong_position": "🔄",
    "needs_rework": "🔧",
    "unprocessed": "⬜"
}


class QuestionReviewer:
    """Основной класс для проверки вопросов"""

    def __init__(self):
        self.data = None
        self.questions = []
        self.current_program = None
        self.question_history = []  # История просмотренных вопросов для навигации назад

        # Создать необходимые директории
        BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        LOG_DIR.mkdir(parents=True, exist_ok=True)

    def create_backup(self) -> str:
        """Создать бекап файла с timestamp"""
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        backup_path = BACKUP_DIR / f"selfology_final_sequenced_{timestamp}.json"

        shutil.copy2(QUESTIONS_FILE, backup_path)
        self.log(f"BACKUP", "system", "system", f"Created backup: {backup_path.name}")

        return str(backup_path)

    def load_data(self) -> bool:
        """Загрузить данные из JSON файла"""
        try:
            with open(QUESTIONS_FILE, 'r', encoding='utf-8') as f:
                self.data = json.load(f)
                self.questions = self.data.get('questions', [])

            self.log("LOAD", "system", "system", f"Loaded {len(self.questions)} questions")
            return True
        except Exception as e:
            print(f"❌ Ошибка загрузки данных: {e}")
            return False

    def save_data(self) -> bool:
        """Сохранить изменения в JSON файл"""
        try:
            # Обновить метаданные
            self.data['metadata']['last_updated'] = datetime.now().isoformat()

            with open(QUESTIONS_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, ensure_ascii=False, indent=2)

            self.log("SAVE", "system", "system", "Data saved successfully")
            return True
        except Exception as e:
            print(f"❌ Ошибка сохранения данных: {e}")
            return False

    def log(self, action: str, question_id: str, program: str, details: str):
        """Записать действие в лог"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"{timestamp} | {action:15} | {question_id:10} | {program:30} | {details}\n"

        with open(LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(log_entry)

    def should_log_action(self, action: str, question: dict, program: str) -> bool:
        """Определить, нужно ли логировать это действие"""
        # Не логировать простое одобрение без предыдущих изменений
        if action == "APPROVE":
            # Проверить, были ли изменения в метаданных
            review_meta = self.get_review_metadata(question, program)
            if not review_meta or (
                'old_text' not in review_meta and
                'old_position' not in review_meta and
                'previous_status' not in review_meta
            ):
                return False
        return True

    def clear_screen(self):
        """Очистить экран"""
        os.system('clear' if os.name != 'nt' else 'cls')

    def get_all_programs(self) -> List[str]:
        """Получить список всех уникальных программ"""
        programs = set()
        for question in self.questions:
            programs_final = question.get('programs_final', [])
            for prog in programs_final:
                programs.add(prog['program'])

        return sorted(list(programs))

    def get_program_questions(self, program_name: str) -> List[Tuple[dict, dict]]:
        """
        Получить все вопросы программы, отсортированные по позиции
        Возвращает список кортежей (question, program_entry)
        Показывает ВСЕ вопросы программы (included и excluded)
        """
        program_questions = []

        for question in self.questions:
            programs_final = question.get('programs_final', [])
            for prog_entry in programs_final:
                if prog_entry['program'] == program_name:
                    program_questions.append((question, prog_entry))
                    break

        # Сортировка: сначала по позиции, потом вопросы без позиции
        program_questions.sort(key=lambda x: (
            x[1].get('position') is None,  # Сначала с позицией, потом без
            x[1].get('position', 999999)   # Потом по номеру позиции
        ))

        return program_questions

    def get_review_status(self, prog_entry: dict) -> str:
        """Получить статус проверки вопроса"""
        return prog_entry.get('review_status', 'unprocessed')

    def get_review_metadata(self, question: dict, program: str) -> Optional[dict]:
        """Получить метаданные проверки для конкретной программы"""
        programs_final = question.get('programs_final', [])
        for prog_entry in programs_final:
            if prog_entry['program'] == program:
                return prog_entry.get('review_metadata', {})
        return None

    def get_program_statistics(self, program_name: str) -> Dict[str, int]:
        """Получить статистику по программе"""
        questions = self.get_program_questions(program_name)

        stats = {
            'total': len(questions),
            'approved': 0,
            'rejected': 0,
            'doubt': 0,
            'wrong_position': 0,
            'needs_rework': 0,
            'unprocessed': 0
        }

        for _, prog_entry in questions:
            status = self.get_review_status(prog_entry)

            if status in ['approved', 'rejected']:
                stats[status] += 1
            elif status == 'doubt':
                stats['doubt'] += 1
            elif status == 'wrong_position':
                stats['wrong_position'] += 1
            elif status == 'needs_rework':
                stats['needs_rework'] += 1
            else:
                stats['unprocessed'] += 1

        stats['processed'] = stats['approved'] + stats['rejected']

        return stats

    def update_review_status(self, question: dict, program: str, status: str,
                           old_position: Optional[int] = None,
                           new_position: Optional[int] = None,
                           old_text: Optional[str] = None):
        """Обновить статус проверки вопроса"""
        programs_final = question.get('programs_final', [])

        for prog_entry in programs_final:
            if prog_entry['program'] == program:
                # Обновить статус
                prog_entry['review_status'] = status
                prog_entry['reviewed_at'] = datetime.now().isoformat()

                # Инициализировать метаданные если нужно
                if 'review_metadata' not in prog_entry:
                    prog_entry['review_metadata'] = {}

                # Сохранить изменения позиции
                if old_position is not None and new_position is not None:
                    prog_entry['review_metadata']['old_position'] = old_position
                    prog_entry['position'] = new_position

                # Сохранить изменение текста
                if old_text is not None:
                    prog_entry['review_metadata']['old_text'] = old_text

                break

    def display_main_menu(self):
        """Отобразить главное меню со списком программ"""
        self.clear_screen()

        print("=" * 70)
        print(" " * 15 + "SELFOLOGY - Проверка вопросов программ")
        print("=" * 70)
        print()

        programs = self.get_all_programs()

        for idx, program in enumerate(programs, 1):
            stats = self.get_program_statistics(program)

            # Прогресс бар
            if stats['total'] > 0:
                progress = int((stats['processed'] / stats['total']) * 10)
                progress_bar = "✅" * progress + "⬜" * (10 - progress)

                # Статус завершенности
                completion = ""
                if stats['needs_rework'] > 0:
                    completion = f" 🔧 НА ДОРАБОТКУ ({stats['needs_rework']})"
                elif stats['processed'] == stats['total']:
                    completion = " ✅ ЗАВЕРШЕНО"

                print(f"{idx:2}. {program:40} [{stats['processed']:2}/{stats['total']:2}] {progress_bar}{completion}")
            else:
                print(f"{idx:2}. {program:40} [0/0] (нет вопросов)")

        print()
        print("=" * 70)
        print("Введите номер программы (или 'q' для выхода): ", end="")

    def run(self):
        """Главная функция запуска"""
        # Создать бекап
        backup_path = self.create_backup()
        print(f"\n✅ Создан бекап: {Path(backup_path).name}\n")

        # Загрузить данные
        if not self.load_data():
            return

        # Главный цикл
        while True:
            self.display_main_menu()

            choice = input().strip().lower()

            if choice == 'q':
                print("\n👋 До свидания!")
                break

            try:
                program_idx = int(choice) - 1
                programs = self.get_all_programs()

                if 0 <= program_idx < len(programs):
                    program_name = programs[program_idx]
                    self.process_program(program_name)
                else:
                    print("❌ Неверный номер программы")
                    input("\nНажмите Enter для продолжения...")
            except ValueError:
                print("❌ Введите число или 'q'")
                input("\nНажмите Enter для продолжения...")

    def process_program(self, program_name: str):
        """Обработать все вопросы программы"""
        self.current_program = program_name
        self.question_history = []
        exited_early = False

        # Фаза 1: Необработанные вопросы
        unprocessed = self.get_questions_by_status(program_name, 'unprocessed')
        if unprocessed:
            result = self.process_question_phase(program_name, unprocessed, "Необработанные вопросы")
            if result == 'exit_to_menu':
                exited_early = True
        else:
            # Все вопросы обработаны - показать список и дать выбрать вопрос
            self.show_processed_program_menu(program_name)
            return

        # Фаза 2: Вопросы под сомнением
        if not exited_early:
            doubt = self.get_questions_by_status(program_name, 'doubt')
            if doubt:
                result = self.process_question_phase(program_name, doubt, "Вопросы под сомнением")
                if result == 'exit_to_menu':
                    exited_early = True

        # Фаза 3: Вопросы с неправильной позицией
        if not exited_early:
            wrong_pos = self.get_questions_by_status(program_name, 'wrong_position')
            if wrong_pos:
                result = self.process_reposition_phase(program_name, wrong_pos)
                if result == 'exit_to_menu':
                    exited_early = True

        # Сохранить изменения
        self.save_data()

        if not exited_early:
            print(f"\n✅ Программа '{program_name}' полностью обработана!")
        else:
            print(f"\n💾 Изменения сохранены. Программа '{program_name}' обработана частично.")

        input("\nНажмите Enter для возврата в главное меню...")

    def get_questions_by_status(self, program_name: str, status: str) -> List[Tuple[dict, dict]]:
        """Получить вопросы программы с определенным статусом"""
        all_questions = self.get_program_questions(program_name)
        filtered = []

        for question, prog_entry in all_questions:
            current_status = self.get_review_status(prog_entry)
            if current_status == status:
                filtered.append((question, prog_entry))

        return filtered

    def display_question(self, question: dict, prog_entry: dict, current_idx: int, total: int, phase_title: str = ""):
        """Отобразить вопрос с информацией и командами"""
        self.clear_screen()

        print("=" * 70)
        print(f"Программа: {self.current_program}")
        if phase_title:
            print(f"Фаза: {phase_title}")
        print(f"Вопрос {current_idx + 1} из {total}")

        # Показать статус включения в программу
        prog_status = prog_entry.get('status', 'included')
        position = prog_entry.get('position')

        if prog_status == 'excluded':
            print(f"Позиция: ИСКЛЮЧЕН ИЗ ПРОГРАММЫ")
        elif position is not None:
            print(f"Позиция: {position}")
        else:
            print(f"Позиция: НЕТ ПОЗИЦИИ")

        print("=" * 70)
        print()

        # ID и текст вопроса
        print(f"ID: {question.get('id', 'N/A')}")
        print(f'Текст: "{question.get("text", "")}"')
        print()

        # Классификация
        classification = question.get('classification', {})
        print("Классификация:")

        domain = classification.get('domain', 'N/A')
        domain_ru = DOMAIN_TRANSLATIONS.get(domain, domain)
        print(f"  Домен: {domain} ({domain_ru})")

        depth = classification.get('depth_level', 'N/A')
        depth_ru = DEPTH_TRANSLATIONS.get(depth, depth)
        print(f"  Глубина: {depth} ({depth_ru})")

        energy = classification.get('energy_dynamic', 'N/A')
        energy_ru = ENERGY_TRANSLATIONS.get(energy, energy)
        print(f"  Энергия: {energy} ({energy_ru})")

        stage = classification.get('journey_stage', 'N/A')
        stage_ru = STAGE_TRANSLATIONS.get(stage, stage)
        print(f"  Стадия: {stage} ({stage_ru})")
        print()

        # Статус проверки
        status = self.get_review_status(prog_entry)
        status_icon = STATUS_ICONS.get(status, "⬜")
        status_text = {
            'approved': 'Одобрен',
            'rejected': 'Отклонен',
            'doubt': 'Под сомнением',
            'wrong_position': 'Неправильная позиция',
            'needs_rework': 'На доработку',
            'unprocessed': 'Не обработано'
        }.get(status, 'Неизвестно')

        print(f"Статус: {status_icon} {status_text}")
        print()

        # Команды
        print("-" * 70)

        # Показать статус включения в программу
        prog_status = prog_entry.get('status', 'unknown')
        if prog_status == 'excluded':
            print("0 - Включить в программу (сейчас ИСКЛЮЧЕН)")
        else:
            print("0 - Исключить из программы (сейчас ВКЛЮЧЕН)")

        print("1 - Одобрить")
        print("2 - Под сомнением")
        print("3 - Отклонить")
        print("4 - Неправильная позиция")
        print("5 - Редактировать формулировку")
        print("6 - Предыдущий вопрос")
        print("7 - Показать все вопросы программы")
        print("8 - Главное меню")
        print("9 - Отправить всю программу на доработку")
        print("q - Выход")
        print()

    def handle_question_command(self, question: dict, prog_entry: dict, command: str) -> str:
        """
        Обработать команду пользователя для вопроса
        Возвращает: 'next', 'previous', 'main_menu', 'quit', 'stay'
        """
        if command == '0':
            # Включить/исключить из программы
            current_status = prog_entry.get('status', 'included')

            if current_status == 'excluded':
                # Включить в программу
                prog_entry['status'] = 'included'

                # Проставить позицию в конец
                all_questions = self.get_program_questions(self.current_program)
                max_pos = max([pe.get('position', 0) for q, pe in all_questions if pe.get('position') is not None], default=0)
                prog_entry['position'] = max_pos + 1

                self.log('INCLUDE', question['id'], self.current_program, f'Включен в программу, позиция {max_pos + 1}')
                print(f"✅ Вопрос включен в программу на позицию {max_pos + 1}")
            else:
                # Исключить из программы
                prog_entry['status'] = 'excluded'
                old_pos = prog_entry.get('position')
                prog_entry.pop('position', None)  # Удалить позицию

                self.log('EXCLUDE', question['id'], self.current_program, f'Исключен из программы (была позиция {old_pos})')
                print(f"❌ Вопрос исключен из программы")

            input("\nНажмите Enter для продолжения...")
            return 'stay'

        elif command == '1':
            # Одобрить
            old_status = self.get_review_status(prog_entry)

            # Если вопрос excluded - автоматически включить в программу
            current_prog_status = prog_entry.get('status', 'included')
            if current_prog_status == 'excluded':
                prog_entry['status'] = 'included'

                # Проставить позицию в конец
                all_questions = self.get_program_questions(self.current_program)
                max_pos = max([pe.get('position', 0) for q, pe in all_questions if pe.get('position') is not None], default=0)
                prog_entry['position'] = max_pos + 1

                self.log('INCLUDE', question['id'], self.current_program, f'Автоматически включен при одобрении, позиция {max_pos + 1}')
                print(f"✅ Вопрос включен в программу (позиция {max_pos + 1}) и одобрен!")
            else:
                print("✅ Вопрос одобрен!")

            self.update_review_status(question, self.current_program, 'approved')

            if self.should_log_action('APPROVE', question, self.current_program):
                self.log('APPROVE', question['id'], self.current_program, f'Previous status: {old_status}')

            input("\nНажмите Enter для продолжения...")
            return 'next'

        elif command == '2':
            # Под сомнением
            self.update_review_status(question, self.current_program, 'doubt')
            self.log('DOUBT', question['id'], self.current_program, 'Помечен под сомнением')
            print("❓ Вопрос помечен под сомнением")
            input("\nНажмите Enter для продолжения...")
            return 'next'

        elif command == '3':
            # Отклонить
            self.update_review_status(question, self.current_program, 'rejected')
            self.log('REJECT', question['id'], self.current_program, 'Отклонен')
            print("❌ Вопрос отклонен")
            input("\nНажмите Enter для продолжения...")
            return 'next'

        elif command == '4':
            # Неправильная позиция
            self.update_review_status(question, self.current_program, 'wrong_position')
            self.log('WRONG_POSITION', question['id'], self.current_program, 'Помечен для перемещения')
            print("🔄 Вопрос помечен с неправильной позицией")
            input("\nНажмите Enter для продолжения...")
            return 'next'

        elif command == '5':
            # Редактировать формулировку
            if self.edit_question_text(question):
                # Текст изменен, показываем вопрос снова
                pass
            return 'stay'

        elif command == '6':
            # Предыдущий вопрос
            return 'previous'

        elif command == '7':
            # Показать все вопросы программы
            self.show_all_program_questions()
            return 'stay'

        elif command == '8':
            # Главное меню
            return 'main_menu'

        elif command == '9':
            # Отправить всю программу на доработку
            confirm = input(f"\n⚠️  Отправить ВСЮ программу '{self.current_program}' на доработку? (y/n): ").lower()
            if confirm == 'y':
                self.mark_program_for_rework(self.current_program)
                print(f"\n🔧 Программа '{self.current_program}' отправлена на доработку")
                input("\nНажмите Enter для возврата в главное меню...")
                return 'main_menu'
            else:
                print("❌ Отмена")
                input("\nНажмите Enter для продолжения...")
                return 'stay'

        elif command == 'q':
            # Выход
            return 'quit'

        else:
            print("❌ Неверная команда")
            input("\nНажмите Enter для продолжения...")
            return 'stay'

    def edit_question_text(self, question: dict) -> bool:
        """
        Редактировать текст вопроса
        Возвращает True если текст был изменен
        """
        print("\n" + "=" * 70)
        print("РЕДАКТИРОВАНИЕ ФОРМУЛИРОВКИ")
        print("=" * 70)
        print()
        print("Текущая формулировка:")
        print(f'"{question["text"]}"')
        print()

        new_text = input("Введите новую формулировку (или Enter для отмены): ").strip()

        if not new_text:
            print("❌ Редактирование отменено")
            input("\nНажмите Enter для возврата...")
            return False

        print()
        print(f'Новая формулировка: "{new_text}"')
        confirm = input("Сохранить изменение? (y/n): ").lower()

        if confirm == 'y':
            old_text = question['text']
            question['text'] = new_text

            # Логировать изменение
            self.log('EDIT_TEXT', question['id'], self.current_program,
                    f'"{old_text}" -> "{new_text}"')

            # Обновить метаданные в программе
            self.update_review_status(question, self.current_program,
                                    self.get_review_status(
                                        self.get_program_entry(question, self.current_program)),
                                    old_text=old_text)

            print("✅ Формулировка изменена!")
            input("\nНажмите Enter для возврата...")
            return True
        else:
            print("❌ Изменение отменено")
            input("\nНажмите Enter для возврата...")
            return False

    def get_program_entry(self, question: dict, program: str) -> Optional[dict]:
        """Получить запись программы из вопроса"""
        programs_final = question.get('programs_final', [])
        for prog_entry in programs_final:
            if prog_entry['program'] == program:
                return prog_entry
        return None

    def show_all_program_questions(self):
        """Показать список всех вопросов программы"""
        self.clear_screen()

        print("=" * 70)
        print(f"Все вопросы программы: {self.current_program}")
        print("=" * 70)
        print()

        stats = self.get_program_statistics(self.current_program)
        print(f"Всего вопросов: {stats['total']}")
        print(f"Обработано: {stats['processed']}")
        print(f"Одобрено: {stats['approved']}")
        print(f"Отклонено: {stats['rejected']}")
        print(f"Под сомнением: {stats['doubt']}")
        print(f"На доработку: {stats['needs_rework']}")
        print()
        print("-" * 70)
        print()

        # Заголовок таблицы
        print(f"{'Поз.':<6} {'ID':<12} {'Статус':<15} {'Текст вопроса':<35}")
        print("-" * 70)

        questions = self.get_program_questions(self.current_program)
        for question, prog_entry in questions:
            position = prog_entry.get('position', 'N/A')
            question_id = question.get('id', 'N/A')
            status = self.get_review_status(prog_entry)
            status_icon = STATUS_ICONS.get(status, "⬜")

            status_text = {
                'approved': f'{status_icon} Одобрен',
                'rejected': f'{status_icon} Отклонен',
                'doubt': f'{status_icon} Сомнение',
                'wrong_position': f'{status_icon} Позиция',
                'needs_rework': f'{status_icon} Доработка',
                'unprocessed': f'{status_icon} Новый'
            }.get(status, f'{status_icon} N/A')

            # Обрезать текст если слишком длинный
            text = question.get('text', '')
            if len(text) > 35:
                text = text[:32] + "..."

            print(f"{position:<6} {question_id:<12} {status_text:<15} {text:<35}")

        print()
        print("-" * 70)
        input("Нажмите Enter для возврата...")

    def process_question_phase(self, program_name: str, questions: List[Tuple[dict, dict]], phase_title: str):
        """Обработать фазу вопросов"""
        current_idx = 0

        while current_idx < len(questions):
            question, prog_entry = questions[current_idx]

            # Показать вопрос
            self.display_question(question, prog_entry, current_idx, len(questions), phase_title)

            # Получить команду
            command = input("Ваш выбор: ").strip().lower()

            # Обработать команду
            action = self.handle_question_command(question, prog_entry, command)

            if action == 'next':
                current_idx += 1
            elif action == 'previous':
                if current_idx > 0:
                    current_idx -= 1
                else:
                    print("❌ Это первый вопрос")
                    input("\nНажмите Enter для продолжения...")
            elif action == 'main_menu':
                # Сохранить и вернуться в главное меню
                self.save_data()
                return 'exit_to_menu'
            elif action == 'quit':
                # Сохранить и выйти
                self.save_data()
                print("\n👋 До свидания!")
                sys.exit(0)
            elif action == 'stay':
                # Остаться на текущем вопросе
                pass

        return 'completed'

    def process_reposition_phase(self, program_name: str, questions: List[Tuple[dict, dict]]):
        """Обработать фазу перемещения вопросов"""
        current_idx = 0

        while current_idx < len(questions):
            question, prog_entry = questions[current_idx]

            # Показать вопрос с контекстом
            self.display_reposition_question(question, prog_entry, current_idx, len(questions))

            # Получить команду
            command = input("Ваш выбор: ").strip().lower()

            # Обработать команду
            action = self.handle_reposition_command(question, prog_entry, command)

            if action == 'next':
                current_idx += 1
            elif action == 'main_menu':
                self.save_data()
                return 'exit_to_menu'
            elif action == 'quit':
                self.save_data()
                print("\n👋 До свидания!")
                sys.exit(0)

        return 'completed'

    def display_reposition_question(self, question: dict, prog_entry: dict, current_idx: int, total: int):
        """Показать вопрос с неправильной позицией с контекстом"""
        self.clear_screen()

        print("=" * 70)
        print(f"Вопросы с неправильной позицией: {current_idx + 1} из {total}")
        print("=" * 70)
        print()

        current_position = prog_entry.get('position', 0)
        print(f"Текущая позиция: {current_position}")
        print(f"ID: {question.get('id', 'N/A')}")
        print(f'Текст: "{question.get("text", "")}"')
        print()

        # Получить все вопросы программы для контекста
        all_questions = self.get_program_questions(self.current_program)

        # Показать контекст (2 вопроса до и 2 после)
        print("--- Контекст (предыдущие 2 вопроса) ---")
        for q, pe in all_questions:
            pos = pe.get('position', 0)
            if current_position - 2 <= pos < current_position:
                text = q.get('text', '')[:50] + "..." if len(q.get('text', '')) > 50 else q.get('text', '')
                print(f"Поз. {pos}: \"{text}\"")

        print()
        print("--- Текущий вопрос ---")
        text = question.get('text', '')[:50] + "..." if len(question.get('text', '')) > 50 else question.get('text', '')
        print(f"Поз. {current_position}: \"{text}\" [ЭТОТ ВОПРОС]")
        print()

        print("--- Следующие 2 вопроса ---")
        for q, pe in all_questions:
            pos = pe.get('position', 0)
            if current_position < pos <= current_position + 2:
                text = q.get('text', '')[:50] + "..." if len(q.get('text', '')) > 50 else q.get('text', '')
                print(f"Поз. {pos}: \"{text}\"")

        print()
        print("-" * 70)
        print("Команды:")
        print("  Введите новую позицию (число 1-{})".format(len(all_questions)))
        print("  o - Отклонить вопрос")
        print("  g - Главное меню")
        print()

    def handle_reposition_command(self, question: dict, prog_entry: dict, command: str) -> str:
        """
        Обработать команду перемещения вопроса
        Возвращает: 'next', 'main_menu', 'quit'
        """
        if command == 'o':
            # Отклонить вопрос
            self.update_review_status(question, self.current_program, 'rejected')
            self.log('REJECT', question['id'], self.current_program, 'Отклонен при перемещении')
            print("❌ Вопрос отклонен")
            input("\nНажмите Enter для продолжения...")
            return 'next'

        elif command == 'g':
            # Главное меню
            return 'main_menu'

        elif command == 'q':
            # Выход
            return 'quit'

        else:
            # Попробовать распарсить как число (новая позиция)
            try:
                new_position = int(command)
                all_questions = self.get_program_questions(self.current_program)
                max_position = len(all_questions)

                if 1 <= new_position <= max_position:
                    confirm = input(f"Переместить вопрос на позицию {new_position}? (y/n): ").lower()
                    if confirm == 'y':
                        old_position = prog_entry.get('position', 0)
                        self.reposition_question(question, old_position, new_position)
                        print("✅ Вопрос перемещен! Все позиции пересчитаны.")
                        input("\nНажмите Enter для продолжения...")
                        return 'next'
                    else:
                        print("❌ Перемещение отменено")
                        input("\nНажмите Enter для продолжения...")
                        return 'next'
                else:
                    print(f"❌ Позиция должна быть от 1 до {max_position}")
                    input("\nНажмите Enter для продолжения...")
                    return 'next'
            except ValueError:
                print("❌ Неверная команда. Введите число, 'o' или 'g'")
                input("\nНажмите Enter для продолжения...")
                return 'next'

    def reposition_question(self, question: dict, old_position: int, new_position: int):
        """Переместить вопрос на новую позицию и пересчитать все позиции"""
        all_questions = self.get_program_questions(self.current_program)

        # Найти вопрос и обновить его позицию
        for q, prog_entry in all_questions:
            if q['id'] == question['id']:
                # Обновить статус и позицию
                self.update_review_status(question, self.current_program, 'approved',
                                        old_position=old_position, new_position=new_position)

                # Логировать
                self.log('REPOSITION', question['id'], self.current_program,
                        f'{old_position} -> {new_position}')
                break

        # Пересчитать позиции всех вопросов
        # Если вопрос перемещается вниз (old_pos < new_pos), сдвигаем промежуточные вверх
        # Если вопрос перемещается вверх (old_pos > new_pos), сдвигаем промежуточные вниз
        for q, prog_entry in all_questions:
            if q['id'] == question['id']:
                continue

            current_pos = prog_entry.get('position', 0)

            if old_position < new_position:
                # Перемещение вниз: все между old и new сдвигаются вверх (-1)
                if old_position < current_pos <= new_position:
                    prog_entry['position'] = current_pos - 1
            else:
                # Перемещение вверх: все между new и old сдвигаются вниз (+1)
                if new_position <= current_pos < old_position:
                    prog_entry['position'] = current_pos + 1

    def mark_program_for_rework(self, program_name: str):
        """Пометить всю программу как требующую доработки"""
        questions = self.get_program_questions(program_name)

        for question, prog_entry in questions:
            # Пометить каждый вопрос программы
            self.update_review_status(question, program_name, 'needs_rework')

        # Логировать
        self.log('PROGRAM_REWORK', 'ALL', program_name, f'Программа отправлена на доработку ({len(questions)} вопросов)')

        print(f"\n✅ Помечено {len(questions)} вопросов для доработки")

    def show_processed_program_menu(self, program_name: str):
        """Показать меню для обработанной программы с возможностью выбора вопроса"""
        import textwrap

        while True:
            self.clear_screen()

            print("=" * 90)
            print(f"Программа: {program_name}")
            print("✅ Все вопросы обработаны")
            print("=" * 90)
            print()

            stats = self.get_program_statistics(program_name)
            print(f"Всего вопросов: {stats['total']}")
            print(f"Одобрено: {stats['approved']}")
            print(f"Отклонено: {stats['rejected']}")
            print(f"Под сомнением: {stats['doubt']}")
            print(f"Неправильная позиция: {stats['wrong_position']}")
            print(f"На доработку: {stats['needs_rework']}")
            print()
            print("-" * 90)
            print()

            # Показать список вопросов
            questions = self.get_program_questions(program_name)

            for idx, (question, prog_entry) in enumerate(questions, 1):
                position = prog_entry.get('position')
                prog_status = prog_entry.get('status', 'unknown')

                # Если вопрос excluded, показать это
                if prog_status == 'excluded':
                    position_str = 'ИСКЛ'
                elif position is None:
                    position_str = '?'
                else:
                    position_str = str(position)

                status = self.get_review_status(prog_entry)
                status_icon = STATUS_ICONS.get(status, "⬜")

                status_text = {
                    'approved': f'{status_icon} Одобрен',
                    'rejected': f'{status_icon} Отклонен',
                    'doubt': f'{status_icon} Сомнение',
                    'wrong_position': f'{status_icon} Позиция',
                    'needs_rework': f'{status_icon} Доработка',
                    'unprocessed': f'{status_icon} Новый'
                }.get(status, f'{status_icon} N/A')

                # Полный текст вопроса с переносом
                text = question.get('text', '')

                # Заголовок вопроса
                print(f"{idx:2}. Поз: {position_str:<4} | {status_text:<15}")

                # Текст с отступом и переносом (макс 75 символов в строке)
                wrapped_lines = textwrap.wrap(text, width=75)
                for line in wrapped_lines:
                    print(f"    {line}")
                print()  # Пустая строка между вопросами

            print("-" * 90)
            print("Команды:")
            print("  Введите номер вопроса (1-{}) для просмотра/редактирования".format(len(questions)))
            print("  b - Назад в главное меню")
            print()

            choice = input("Ваш выбор: ").strip().lower()

            if choice == 'b':
                return

            try:
                question_idx = int(choice) - 1
                if 0 <= question_idx < len(questions):
                    # Перейти к выбранному вопросу
                    question, prog_entry = questions[question_idx]
                    self.edit_specific_question(question, prog_entry, question_idx, len(questions))
                else:
                    print(f"❌ Номер вопроса должен быть от 1 до {len(questions)}")
                    input("\nНажмите Enter для продолжения...")
            except ValueError:
                print("❌ Введите номер вопроса или 'b'")
                input("\nНажмите Enter для продолжения...")

    def edit_specific_question(self, question: dict, prog_entry: dict, idx: int, total: int):
        """Редактировать конкретный вопрос"""
        while True:
            # Показать вопрос
            self.display_question(question, prog_entry, idx, total, "Редактирование")

            # Получить команду
            command = input("Ваш выбор: ").strip().lower()

            # Обработать команду
            action = self.handle_question_command(question, prog_entry, command)

            if action == 'next':
                # Сохранить и вернуться к списку
                self.save_data()
                return
            elif action == 'previous':
                # Вернуться к списку (игнорируем навигацию назад в этом режиме)
                return
            elif action == 'main_menu':
                # Сохранить и вернуться в главное меню
                self.save_data()
                return
            elif action == 'quit':
                # Сохранить и выйти
                self.save_data()
                print("\n👋 До свидания!")
                sys.exit(0)
            elif action == 'stay':
                # Остаться на текущем вопросе
                pass


def main():
    """Точка входа"""
    reviewer = QuestionReviewer()
    reviewer.run()


if __name__ == "__main__":
    main()
