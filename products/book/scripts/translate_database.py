#!/usr/bin/env python3
"""
Перевод базы вопросов Selfology на EN/ES

Цепочка агентов:
1. Культурный аналитик (Claude Sonnet) — анализ кластера
2. Переводчик (Claude Opus) — адаптивный перевод
3. Психологический валидатор (Claude Sonnet) — проверка смысла
4. Лингвистический редактор (GPT-4o) — финальная полировка
5. Технический валидатор (код) — автоматические проверки

Использование:
  python translate_database.py --test-cluster    # Тест на 1 кластере
  python translate_database.py --test-program   # Тест на 1 программе
  python translate_database.py --full           # Полный перевод
"""

import json
import os
import sys
import argparse
import time
from pathlib import Path
from typing import Optional
from dataclasses import dataclass
from dotenv import load_dotenv

# Загрузка переменных окружения
load_dotenv(Path(__file__).parent.parent.parent.parent / '.env')

import anthropic
import openai

# Клиенты API
claude_client = anthropic.Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))
openai_client = openai.OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

# Пути
DATA_DIR = Path(__file__).parent.parent.parent.parent / 'intelligent_question_core' / 'data'
SOURCE_FILE = DATA_DIR / 'selfology_master.json'
OUTPUT_DIR = DATA_DIR

# Константы
DEPTH_LABELS = {
    'Foundation': 'лёгкий, для разминки',
    'Exploration': 'средний, исследовательский',
    'Integration': 'глубокий, трансформационный'
}


@dataclass
class TranslationResult:
    """Результат перевода одного вопроса"""
    original: str
    en: str
    es: str
    cultural_notes: str = ''
    validation_status: str = 'pending'
    validation_notes: str = ''


def call_claude(prompt: str, model: str = 'claude-sonnet-4-20250514', max_tokens: int = 1024) -> str:
    """Вызов Claude API"""
    response = claude_client.messages.create(
        model=model,
        max_tokens=max_tokens,
        messages=[{'role': 'user', 'content': prompt}]
    )
    return response.content[0].text.strip()


def call_gpt4(prompt: str, model: str = 'gpt-4o') -> str:
    """Вызов OpenAI API"""
    response = openai_client.chat.completions.create(
        model=model,
        messages=[{'role': 'user', 'content': prompt}],
        max_tokens=1024
    )
    return response.choices[0].message.content.strip()


# ============================================
# АГЕНТ 1: Культурный аналитик
# ============================================

CULTURAL_ANALYST_PROMPT = """Ты — культурный консультант для перевода психологических вопросов с русского на английский и испанский.

Проанализируй этот кластер вопросов и дай рекомендации переводчику.

**Программа:** {program_name}
**Кластер:** {cluster_name}
**Описание:** {cluster_description}
**Глубина:** {depth}

**Вопросы:**
{questions}

---

Ответь КРАТКО (максимум 5-7 пунктов):

1. **Культурные особенности:** Какие русские реалии нужно адаптировать? (например: дача → country house, маршрутка → bus)

2. **Метафоры:** Какие метафоры могут не работать в EN/ES и чем заменить?

3. **Тон:** На что обратить внимание в тоне для каждого языка?

4. **Специфика темы:** Есть ли культурные различия в восприятии этой темы (отношения, деньги, работа)?

Если особенностей нет — напиши "Прямой перевод, особенностей нет."
"""

def agent_cultural_analyst(program_name: str, cluster: dict) -> str:
    """Анализирует культурные особенности кластера"""
    questions_text = '\n'.join([f"- {q['text']}" for q in cluster['questions']])

    prompt = CULTURAL_ANALYST_PROMPT.format(
        program_name=program_name,
        cluster_name=cluster['name'],
        cluster_description=cluster.get('description', ''),
        depth=DEPTH_LABELS.get(cluster['type'], cluster['type']),
        questions=questions_text
    )

    return call_claude(prompt, model='claude-sonnet-4-20250514')


# ============================================
# АГЕНТ 2: Переводчик
# ============================================

TRANSLATOR_PROMPT = """Ты — профессиональный переводчик психологических текстов. Переводишь вопросы для самопознания с русского на английский и испанский.

**Контекст:**
- Программа: {program_name}
- Кластер: {cluster_name}
- Глубина: {depth}

**Культурные заметки от аналитика:**
{cultural_notes}

**Требования к переводу:**

ДЛЯ АНГЛИЙСКОГО:
- Используй "you" (неформальное обращение)
- Сохрани эмоциональный вес вопроса
- Вопрос должен звучать естественно для носителя
- Если нужно — адаптируй метафоры, но сохрани смысл
- ВАЖНО: Если оригинал короткий — перевод тоже должен быть ёмким, но полным по смыслу

ДЛЯ ИСПАНСКОГО:
- Используй "tú" (неформальное обращение)
- Учитывай, что аудитория — Латинская Америка + Испания
- Избегай слишком локальных выражений
- ВАЖНО: Не сокращай перевод слишком сильно. "Любишь ли ты себя?" → "¿Te quieres a ti mismo?" (НЕ просто "¿Te amas?")

**Оригинал (русский):**
{text_ru}

---

Ответь СТРОГО в формате:

EN: [перевод на английский]
ES: [перевод на испанский]
"""

def agent_translator(text_ru: str, program_name: str, cluster_name: str,
                     depth: str, cultural_notes: str) -> tuple[str, str]:
    """Переводит вопрос на EN и ES"""
    prompt = TRANSLATOR_PROMPT.format(
        program_name=program_name,
        cluster_name=cluster_name,
        depth=DEPTH_LABELS.get(depth, depth),
        cultural_notes=cultural_notes,
        text_ru=text_ru
    )

    # Используем Opus для качества
    response = call_claude(prompt, model='claude-sonnet-4-20250514', max_tokens=512)

    # Парсим ответ
    en_text = ''
    es_text = ''

    for line in response.split('\n'):
        line = line.strip()
        if line.startswith('EN:'):
            en_text = line[3:].strip()
        elif line.startswith('ES:'):
            es_text = line[3:].strip()

    return en_text, es_text


# ============================================
# АГЕНТ 3: Психологический валидатор
# ============================================

VALIDATOR_PROMPT = """Ты — психолог, проверяющий качество перевода вопросов для самопознания.

**Оригинал (русский):**
{text_ru}

**Перевод на английский:**
{text_en}

**Перевод на испанский:**
{text_es}

**Контекст:**
- Глубина вопроса: {depth}
- Тема: {cluster_name}

---

Проверь КАЖДЫЙ перевод по критериям:

1. **Смысл сохранён?** — Вопрос провоцирует ту же рефлексию?
2. **Тон правильный?** — Не стал мягче/жёстче оригинала?
3. **Естественность?** — Звучит как родной вопрос, не как перевод?

Ответь СТРОГО в формате:

EN_STATUS: OK / NEEDS_WORK
EN_COMMENT: [комментарий если нужна доработка]
ES_STATUS: OK / NEEDS_WORK
ES_COMMENT: [комментарий если нужна доработка]
"""

def agent_validator(text_ru: str, text_en: str, text_es: str,
                    cluster_name: str, depth: str) -> dict:
    """Валидирует психологическую эквивалентность перевода"""
    prompt = VALIDATOR_PROMPT.format(
        text_ru=text_ru,
        text_en=text_en,
        text_es=text_es,
        depth=DEPTH_LABELS.get(depth, depth),
        cluster_name=cluster_name
    )

    response = call_claude(prompt, model='claude-sonnet-4-20250514')

    result = {
        'en_ok': True,
        'es_ok': True,
        'en_comment': '',
        'es_comment': ''
    }

    for line in response.split('\n'):
        line = line.strip()
        if line.startswith('EN_STATUS:'):
            result['en_ok'] = 'OK' in line.upper() and 'NEEDS' not in line.upper()
        elif line.startswith('ES_STATUS:'):
            result['es_ok'] = 'OK' in line.upper() and 'NEEDS' not in line.upper()
        elif line.startswith('EN_COMMENT:'):
            result['en_comment'] = line.split(':', 1)[1].strip()
        elif line.startswith('ES_COMMENT:'):
            result['es_comment'] = line.split(':', 1)[1].strip()

    return result


# ============================================
# АГЕНТ 4: Лингвистический редактор
# ============================================

EDITOR_PROMPT = """You are a professional editor. Polish this {lang} text for grammar, punctuation, and natural flow.

Text: {text}

Requirements:
- Fix any grammar issues
- Ensure natural phrasing
- Keep the question mark at the end (if it's a question)
- Keep imperative/instructional tone if present
- Don't change the meaning
- Don't add quotes around the text
- IMPORTANT: Return the text in the SAME language ({lang})

Return ONLY the polished text, nothing else.
"""

def agent_editor(text: str, lang: str) -> str:
    """Финальная полировка текста"""
    prompt = EDITOR_PROMPT.format(text=text, lang=lang)
    result = call_gpt4(prompt)

    # Убираем случайные кавычки вокруг текста
    result = result.strip('"\'')

    return result


# ============================================
# АГЕНТ 5: Технический валидатор
# ============================================

def agent_technical_validator(original: str, translated: str, lang: str) -> tuple[bool, str]:
    """Автоматические проверки перевода"""
    errors = []

    # Проверка на русские символы
    cyrillic = set('абвгдеёжзийклмнопрстуфхцчшщъыьэюяАБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ')
    if any(c in cyrillic for c in translated):
        errors.append(f'Найдены русские символы в {lang}')

    # Проверка на вопросительный знак — только если оригинал заканчивается на "?"
    # Императивы ("Выпиши...", "Закончи фразу...") не должны иметь "?"
    if original.strip().endswith('?') and not translated.strip().endswith('?'):
        errors.append(f'Нет вопросительного знака в {lang}')

    # Проверка длины — более мягкая для коротких вопросов
    orig_len = len(original)
    trans_len = len(translated)
    # Для коротких вопросов (<30 символов) разрешаем большую вариацию
    if orig_len < 30:
        min_len = orig_len * 0.2
        max_len = orig_len * 3.0
    else:
        min_len = orig_len * 0.3
        max_len = orig_len * 2.0

    if trans_len < min_len or trans_len > max_len:
        errors.append(f'Подозрительная длина {lang}: {trans_len} символов (оригинал {orig_len})')

    # Проверка на пустоту
    if not translated.strip():
        errors.append(f'Пустой перевод {lang}')

    return len(errors) == 0, '; '.join(errors)


# ============================================
# ОСНОВНОЙ ПРОЦЕСС
# ============================================

def translate_cluster(program_name: str, cluster: dict, verbose: bool = True) -> list[dict]:
    """Переводит один кластер целиком"""
    results = []

    # Шаг 1: Культурный анализ
    if verbose:
        print(f"  📚 Культурный анализ кластера '{cluster['name']}'...")
    cultural_notes = agent_cultural_analyst(program_name, cluster)
    if verbose:
        print(f"     Заметки: {cultural_notes[:100]}...")

    # Шаг 2-4: Перевод и валидация каждого вопроса
    for i, q in enumerate(cluster['questions'], 1):
        text_ru = q['text']
        if verbose:
            print(f"  [{i}/{len(cluster['questions'])}] {text_ru[:50]}...")

        # Перевод
        text_en, text_es = agent_translator(
            text_ru, program_name, cluster['name'],
            cluster['type'], cultural_notes
        )

        # Валидация
        validation = agent_validator(
            text_ru, text_en, text_es,
            cluster['name'], cluster['type']
        )

        # Если нужна доработка — повторный перевод с детальным фидбеком
        retry_count = 0
        max_retries = 3  # Увеличено до 3
        while (not validation['en_ok'] or not validation['es_ok']) and retry_count < max_retries:
            retry_count += 1
            if verbose:
                print(f"     ⚠️ Retry {retry_count}/{max_retries}: EN={validation['en_ok']}, ES={validation['es_ok']}")
                if validation['en_comment']:
                    print(f"        EN issue: {validation['en_comment'][:80]}")
                if validation['es_comment']:
                    print(f"        ES issue: {validation['es_comment'][:80]}")

            # Детальный фидбек для переводчика
            feedback_parts = ["\n\n⚠️ ФИДБЕК ВАЛИДАТОРА — ИСПРАВЬ ЭТИ ПРОБЛЕМЫ:"]
            if not validation['en_ok'] and validation['en_comment']:
                feedback_parts.append(f"EN ПРОБЛЕМА: {validation['en_comment']}")
            if not validation['es_ok'] and validation['es_comment']:
                feedback_parts.append(f"ES ПРОБЛЕМА: {validation['es_comment']}")
            feedback = '\n'.join(feedback_parts)

            text_en, text_es = agent_translator(
                text_ru, program_name, cluster['name'],
                cluster['type'], cultural_notes + feedback
            )
            validation = agent_validator(
                text_ru, text_en, text_es,
                cluster['name'], cluster['type']
            )

        # Финальная полировка
        text_en = agent_editor(text_en, 'English')
        text_es = agent_editor(text_es, 'Spanish')

        # Техническая валидация с возможностью авто-исправления
        en_valid, en_errors = agent_technical_validator(text_ru, text_en, 'EN')
        es_valid, es_errors = agent_technical_validator(text_ru, text_es, 'ES')

        # Авто-исправление простых проблем
        if not en_valid and 'вопросительного знака' in en_errors:
            if text_ru.strip().endswith('?') and not text_en.strip().endswith('?'):
                text_en = text_en.rstrip('.!') + '?'
                en_valid, en_errors = agent_technical_validator(text_ru, text_en, 'EN')

        if not es_valid and 'вопросительного знака' in es_errors:
            if text_ru.strip().endswith('?') and not text_es.strip().endswith('?'):
                # Испанский: добавляем ¿ в начало и ? в конец
                text_es = text_es.rstrip('.!') + '?'
                if not text_es.startswith('¿'):
                    text_es = '¿' + text_es
                es_valid, es_errors = agent_technical_validator(text_ru, text_es, 'ES')

        all_errors = f"{en_errors} {es_errors}".strip()
        final_ok = validation['en_ok'] and validation['es_ok'] and en_valid and es_valid

        if not final_ok and verbose:
            print(f"     ⚠️ Проблемы: {all_errors or 'психологическая валидация'}")

        results.append({
            'text_ru': text_ru,
            'text_en': text_en,
            'text_es': text_es,
            'validation_ok': final_ok,
            'notes': all_errors if not final_ok else ''
        })

        # Небольшая пауза чтобы не упереться в rate limits
        time.sleep(0.3)

    return results


def translate_program(program: dict, verbose: bool = True) -> dict:
    """Переводит одну программу целиком"""
    if verbose:
        print(f"\n{'='*60}")
        print(f"📖 Программа: {program['name']}")
        print(f"   Кластеров: {len(program['blocks'])}")

    translated_program = {
        'name_ru': program['name'],
        'name_en': '',  # Заполним позже
        'name_es': '',
        'blocks': []
    }

    for cluster in program['blocks']:
        if verbose:
            print(f"\n  🔹 Кластер: {cluster['name']} ({len(cluster['questions'])} вопросов)")

        # Перевод названия и описания кластера
        cluster_meta = translate_cluster_meta(program['name'], cluster)

        # Перевод вопросов
        translated_questions = translate_cluster(program['name'], cluster, verbose)

        translated_program['blocks'].append({
            'name_ru': cluster['name'],
            'name_en': cluster_meta['name_en'],
            'name_es': cluster_meta['name_es'],
            'description_ru': cluster.get('description', ''),
            'description_en': cluster_meta['description_en'],
            'description_es': cluster_meta['description_es'],
            'type': cluster['type'],
            'questions': translated_questions
        })

    # Перевод названия программы
    program_meta = translate_program_name(program['name'])
    translated_program['name_en'] = program_meta['en']
    translated_program['name_es'] = program_meta['es']

    return translated_program


def translate_cluster_meta(program_name: str, cluster: dict) -> dict:
    """Переводит название и описание кластера"""
    prompt = f"""Переведи название и описание психологического кластера на английский и испанский.

Программа: {program_name}
Название кластера: {cluster['name']}
Описание: {cluster.get('description', '')}

Ответь в формате:
NAME_EN: [перевод названия]
NAME_ES: [перевод названия]
DESC_EN: [перевод описания]
DESC_ES: [перевод описания]
"""
    response = call_claude(prompt, model='claude-sonnet-4-20250514')

    result = {'name_en': '', 'name_es': '', 'description_en': '', 'description_es': ''}
    for line in response.split('\n'):
        line = line.strip()
        if line.startswith('NAME_EN:'):
            result['name_en'] = line.split(':', 1)[1].strip()
        elif line.startswith('NAME_ES:'):
            result['name_es'] = line.split(':', 1)[1].strip()
        elif line.startswith('DESC_EN:'):
            result['description_en'] = line.split(':', 1)[1].strip()
        elif line.startswith('DESC_ES:'):
            result['description_es'] = line.split(':', 1)[1].strip()

    return result


def translate_program_name(name_ru: str) -> dict:
    """Переводит название программы"""
    prompt = f"""Переведи название психологической программы на английский и испанский.

Название: {name_ru}

Ответь в формате:
EN: [перевод]
ES: [перевод]
"""
    response = call_claude(prompt, model='claude-sonnet-4-20250514')

    result = {'en': '', 'es': ''}
    for line in response.split('\n'):
        line = line.strip()
        if line.startswith('EN:'):
            result['en'] = line.split(':', 1)[1].strip()
        elif line.startswith('ES:'):
            result['es'] = line.split(':', 1)[1].strip()

    return result


# ============================================
# ТЕСТОВЫЕ РЕЖИМЫ
# ============================================

def test_on_cluster():
    """Тест на одном кластере"""
    print("🧪 ТЕСТ: Перевод одного кластера")
    print("="*60)

    with open(SOURCE_FILE) as f:
        data = json.load(f)

    # Берём первую программу, первый кластер
    program = data['programs'][0]
    cluster = program['blocks'][0]

    print(f"Программа: {program['name']}")
    print(f"Кластер: {cluster['name']}")
    print(f"Вопросов: {len(cluster['questions'])}")
    print()

    results = translate_cluster(program['name'], cluster, verbose=True)

    # Выводим результаты
    print("\n" + "="*60)
    print("РЕЗУЛЬТАТЫ:")
    print("="*60)

    for i, r in enumerate(results, 1):
        print(f"\n[{i}]")
        print(f"  RU: {r['text_ru']}")
        print(f"  EN: {r['text_en']}")
        print(f"  ES: {r['text_es']}")
        print(f"  ✅ OK" if r['validation_ok'] else f"  ⚠️ {r['notes']}")

    # Сохраняем результат теста
    test_output = OUTPUT_DIR / 'test_cluster_translation.json'
    with open(test_output, 'w') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\n💾 Сохранено: {test_output}")

    return results


def test_on_program():
    """Тест на одной программе"""
    print("🧪 ТЕСТ: Перевод одной программы")
    print("="*60)

    with open(SOURCE_FILE) as f:
        data = json.load(f)

    # Берём первую программу
    program = data['programs'][0]

    result = translate_program(program, verbose=True)

    # Сохраняем результат
    test_output = OUTPUT_DIR / 'test_program_translation.json'
    with open(test_output, 'w') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"\n💾 Сохранено: {test_output}")

    # Статистика
    total = sum(len(b['questions']) for b in result['blocks'])
    ok = sum(1 for b in result['blocks'] for q in b['questions'] if q['validation_ok'])
    print(f"\n📊 Статистика: {ok}/{total} вопросов прошли валидацию")

    return result


def full_translation():
    """Полный перевод всей базы"""
    print("🚀 ПОЛНЫЙ ПЕРЕВОД")
    print("="*60)

    with open(SOURCE_FILE) as f:
        data = json.load(f)

    # Создаём структуры для EN и ES
    data_en = {
        'version': data['version'] + '-en',
        'metadata': data['metadata'].copy(),
        'programs': []
    }
    data_es = {
        'version': data['version'] + '-es',
        'metadata': data['metadata'].copy(),
        'programs': []
    }

    total_questions = 0
    translated_questions = 0
    failed_questions = []  # Список проблемных вопросов

    for program in data['programs']:
        result = translate_program(program, verbose=True)

        # Формируем EN версию
        program_en = {
            'name': result['name_en'],
            'blocks': []
        }
        for block in result['blocks']:
            program_en['blocks'].append({
                'name': block['name_en'],
                'description': block['description_en'],
                'type': block['type'],
                'questions': [{'text': q['text_en']} for q in block['questions']]
            })
        data_en['programs'].append(program_en)

        # Формируем ES версию
        program_es = {
            'name': result['name_es'],
            'blocks': []
        }
        for block in result['blocks']:
            program_es['blocks'].append({
                'name': block['name_es'],
                'description': block['description_es'],
                'type': block['type'],
                'questions': [{'text': q['text_es']} for q in block['questions']]
            })
        data_es['programs'].append(program_es)

        # Статистика и сбор проблемных
        for block in result['blocks']:
            for q in block['questions']:
                total_questions += 1
                if q['validation_ok']:
                    translated_questions += 1
                else:
                    failed_questions.append({
                        'program': result['name_ru'],
                        'cluster': block['name_ru'],
                        'text_ru': q['text_ru'],
                        'text_en': q['text_en'],
                        'text_es': q['text_es'],
                        'notes': q.get('notes', '')
                    })

    # Сохраняем переводы
    en_file = OUTPUT_DIR / 'selfology_master_en.json'
    es_file = OUTPUT_DIR / 'selfology_master_es.json'

    with open(en_file, 'w') as f:
        json.dump(data_en, f, ensure_ascii=False, indent=2)
    with open(es_file, 'w') as f:
        json.dump(data_es, f, ensure_ascii=False, indent=2)

    # Сохраняем отчёт о проблемных вопросах
    if failed_questions:
        failed_file = OUTPUT_DIR / 'translation_issues.json'
        with open(failed_file, 'w') as f:
            json.dump(failed_questions, f, ensure_ascii=False, indent=2)
        print(f"\n⚠️ Проблемные вопросы сохранены: {failed_file}")

    print(f"\n{'='*60}")
    print(f"✅ ГОТОВО!")
    print(f"   EN: {en_file}")
    print(f"   ES: {es_file}")
    print(f"   Переведено: {translated_questions}/{total_questions} ({100*translated_questions/total_questions:.1f}%)")

    if failed_questions:
        print(f"\n⚠️ ТРЕБУЮТ ВНИМАНИЯ: {len(failed_questions)} вопросов")
        print("   Первые 5:")
        for q in failed_questions[:5]:
            print(f"   - [{q['program']}] {q['text_ru'][:50]}...")


# ============================================
# MAIN
# ============================================

def main():
    parser = argparse.ArgumentParser(description='Перевод базы Selfology')
    parser.add_argument('--test-cluster', action='store_true', help='Тест на 1 кластере')
    parser.add_argument('--test-program', action='store_true', help='Тест на 1 программе')
    parser.add_argument('--full', action='store_true', help='Полный перевод')
    parser.add_argument('--yes', '-y', action='store_true', help='Автоподтверждение')
    args = parser.parse_args()

    if args.test_cluster:
        test_on_cluster()
    elif args.test_program:
        test_on_program()
    elif args.full:
        if args.yes:
            full_translation()
        else:
            confirm = input("⚠️ Полный перевод ~$36. Продолжить? (yes/no): ")
            if confirm.lower() == 'yes':
                full_translation()
            else:
                print("Отменено.")
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
