#!/usr/bin/env python3
"""Генератор Book 2: Путь в глубину (по уровням глубины)

Поддержка языков: ru, en, es
Использование: python3 generate_book2.py [--lang ru|en|es]
"""

import json
import re
import argparse
from collections import defaultdict

# ============================================
# ЯЗЫКОВЫЕ КОНФИГУРАЦИИ
# ============================================
LANG_CONFIG = {
    'ru': {
        'book_title': 'Путь в глубину',
        'book_subtitle': 'От поверхности к истине',
        'time_format': '{0} – {1} мин',  # с пробелами вокруг тире
        'time_suffix': 'мин',
        'quotes': ('«', '»'),             # кавычки-ёлочки
        'widows': [
            # Союзы
            'и', 'а', 'но', 'да', 'то', 'ни', 'же', 'ли', 'бы', 'что', 'как', 'так', 'раз',
            # Предлоги
            'в', 'к', 'с', 'о', 'у', 'на', 'за', 'из', 'до', 'по', 'об', 'от', 'без', 'для', 'под', 'над', 'при', 'про',
            # Частицы
            'не', 'ведь', 'вот', 'вон', 'уж', 'ну',
            # Местоимения
            'я', 'ты', 'он', 'мы', 'вы', 'все', 'это', 'кто',
        ],
    },
    'en': {
        'book_title': 'The Path Within',
        'book_subtitle': 'From surface to truth',
        'time_format': '{0}–{1} min',     # слитно с en-dash
        'time_suffix': 'min',
        'quotes': ('"', '"'),             # английские кавычки
        'widows': [
            # Articles
            'a', 'an', 'the',
            # Prepositions
            'in', 'on', 'at', 'to', 'of', 'by', 'as', 'or', 'if', 'so',
            # Conjunctions
            'and', 'but', 'for', 'nor', 'yet',
            # Pronouns
            'I', 'we', 'he', 'it', 'my', 'me',
        ],
    },
    'es': {
        'book_title': 'El Camino Interior',
        'book_subtitle': 'De la superficie a la verdad',
        'time_format': '{0}-{1} min',     # обычный дефис (RAE)
        'time_suffix': 'min',
        'quotes': ('«', '»'),             # кавычки-ёлочки (как в русском)
        'widows': [
            # Artículos
            'el', 'la', 'lo', 'un', 'una',
            # Preposiciones
            'a', 'de', 'en', 'y', 'o', 'u', 'e', 'al', 'del',
            # Conjunciones
            'que', 'si', 'ni', 'mas', 'pero',
            # Pronombres
            'yo', 'tú', 'él', 'me', 'te', 'se', 'nos', 'os', 'su', 'mi', 'tu',
        ],
    },
}

# Парсинг аргументов
parser = argparse.ArgumentParser(description='Генератор Book 2')
parser.add_argument('--lang', choices=['ru', 'en', 'es'], default='ru', help='Язык книги')
args = parser.parse_args()

LANG = args.lang
CONFIG = LANG_CONFIG[LANG]

# Загрузка данных из единого источника правды
DATA_FILE = '/home/ksnk/microservices/critical/selfology-bot/intelligent_question_core/data/selfology_master.json'
with open(DATA_FILE) as f:
    data = json.load(f)

print(f"📚 Источник: selfology_master.json (v{data.get('version', '?')})")
print(f"🌍 Язык: {LANG}")

# Преамбулы книги
INTRO = r'''
\thispagestyle{empty}
\vspace*{0.2\textheight}

{\centering\sffamily\bfseries\fontsize{24pt}{28pt}\selectfont Начало пути\par}

\vspace{2em}

Эта книга устроена как погружение.

Вы начнёте с поверхности — там, где безопасно и понятно. Постепенно будете спускаться глубже. К финалу окажетесь в местах, куда редко кто заглядывает.

\vspace{1.5em}
{\sffamily\bfseries Три глубины}

\textbf{Часть I: Первые шаги.} Разминка. Простые вопросы, которые помогут настроиться на честный разговор с собой.

\textbf{Часть II: Исследование.} Здесь начинается работа. Вопросы будут задевать то, о чём вы не задумывались. Это нормально.

\textbf{Часть III: Глубинная работа.} Самое важное. Сюда стоит идти только когда вы готовы. Не торопитесь.

\vspace{1.5em}
{\sffamily\bfseries Почему именно так}

Мы устроены слоями. Сверху — то, что мы про себя знаем и легко рассказываем. Глубже — то, что знаем, но не любим признавать. Ещё глубже — то, что от себя прячем.

Прыгнуть сразу на глубину — больно и бесполезно. Нужен постепенный спуск. Эта книга — ваш проводник.

\newpage
\thispagestyle{empty}
\vspace*{0.1\textheight}

{\sffamily\bfseries Как проходить}

\textbf{Последовательно.} Не перескакивайте. Каждая часть готовит к следующей.

\textbf{С паузами.} Между частями делайте перерыв — день, неделю. Дайте осесть.

\textbf{Письменно.} Мысль, записанная рукой, становится реальнее. Не отвечайте в голове.

\textbf{Честно.} Эту книгу никто не будет проверять. Врать здесь — только себе.

\vspace{2em}
{\centering\itshape Начнём с простого.\par}
'''

WARNING = r'''
\newpage
\thispagestyle{empty}
\vspace*{0.3\textheight}

{\centering\sffamily\bfseries\fontsize{18pt}{22pt}\selectfont Внимание: глубокая работа\par}

\vspace{2em}

Следующий раздел требует особого внимания.

Перед тем как продолжить, убедитесь:

\begin{itemize}
\item Вы находитесь в безопасном месте
\item У вас есть время и силы
\item Вас никто не потревожит
\end{itemize}

\vspace{1em}

Эти вопросы могут вызвать сильные эмоции. Это нормально — значит, вы касаетесь чего-то важного.

Если станет слишком тяжело — остановитесь. Сделайте перерыв. Вернитесь позже.

\vspace{2em}
{\centering\itshape Бережно относитесь к себе.\par}
'''

CONCLUSION = r'''
\newpage
\thispagestyle{empty}
\vspace*{0.2\textheight}

{\centering\sffamily\bfseries\fontsize{24pt}{28pt}\selectfont Вы на дне\par}

\vspace{2em}

В хорошем смысле.

Вы дошли до самой глубины. Увидели то, что обычно остаётся в тени. Это требует мужества — и вы его проявили.

\vspace{1.5em}
{\sffamily\bfseries Что теперь}

То, что вы записали — это не просто ответы. Это карта вашего внутреннего мира. Она будет меняться вместе с вами.

\textbf{Через месяц} перечитайте записи. Вы удивитесь, как изменилось восприятие.

\textbf{Через год} пройдите книгу заново. Вы будете другим человеком — и ответы будут другими.

\vspace{1.5em}
{\sffamily\bfseries Один вопрос напоследок}

Что вы теперь знаете о себе, чего не знали до этой книги?

\vspace{3em}
{\centering\itshape Путь продолжается.\par}

\vspace{3em}
{\centering\sffamily Selfology\par}
'''

# Названия частей книги
PART_NAMES = {
    "Foundation": "Часть I: Первые шаги",
    "Exploration": "Часть II: Исследование",
    "Integration": "Часть III: Глубинная работа"
}

PART_SUBTITLES = {
    "Foundation": "Мягкое начало — знакомство с собой",
    "Exploration": "Погружение — исследование паттернов",
    "Integration": "Трансформация — интеграция открытий"
}

# Время по типу кластера (формат зависит от языка)
def get_time(depth_type):
    """Возвращает время в правильном формате для языка"""
    times = {
        "Foundation": (5, 10),
        "Exploration": (10, 20),
        "Integration": (15, 30),
    }
    t = times.get(depth_type, (10, 15))
    return CONFIG['time_format'].format(t[0], t[1])

# Команда вопроса по типу
DEPTH_QUESTION = {
    "Foundation": "\\questionF",
    "Exploration": "\\questionE",
    "Integration": "\\questionI"
}

def fix_widows(text):
    """Заменяет пробелы после коротких слов на неразрывные (~)

    Предотвращает висячие предлоги, союзы и частицы в конце строки.
    """
    widows = CONFIG['widows']
    for word in widows:
        # Паттерн: слово + пробел (не в начале строки, учитываем регистр)
        pattern = rf'(\s|^)({re.escape(word)})(\s+)'
        # Заменяем пробел после слова на неразрывный
        text = re.sub(pattern, r'\1\2~', text, flags=re.IGNORECASE)
    return text

def normalize_quotes(text):
    """Нормализует все виды кавычек к формату текущего языка

    Использует CONFIG['quotes'] для правильных кавычек языка.
    """
    open_q, close_q = CONFIG['quotes']

    # 1. Прямые кавычки "текст" → «текст» (или "text" для английского)
    text = re.sub(r'"([^"]*)"', rf'{open_q}\1{close_q}', text)

    # 2. Типографские английские кавычки → кавычки языка
    text = text.replace('"', open_q)   # левая английская
    text = text.replace('"', close_q)  # правая английская

    # 3. Немецкие нижние кавычки → открывающая
    text = text.replace('„', open_q)

    # 4. Если в тексте уже есть ёлочки, но язык другой — конвертируем
    if open_q != '«':
        text = text.replace('«', open_q)
        text = text.replace('»', close_q)

    return text

def unicode_to_latex(text):
    """Конвертирует Unicode-символы в LaTeX-команды

    Тире, многоточие, спецсимволы → LaTeX эквиваленты.
    Кавычки обрабатываются отдельно в normalize_quotes().
    """
    replacements = [
        ('—', '---'),            # em-dash (длинное тире)
        ('–', '--'),             # en-dash (короткое тире, диапазоны)
        ('…', '...'),            # многоточие
        ('№', r'\textnumero{}'), # знак номера
        ('\u2019', "'"),         # апостроф (right single quote)
    ]
    for old, new in replacements:
        text = text.replace(old, new)

    return text

def escape_latex(text):
    """Полная обработка текста для LaTeX

    Порядок важен:
    1. Нормализация кавычек (до изменения текста)
    2. Unicode → LaTeX (тире, спецсимволы)
    3. Висячие предлоги (добавляет ~)
    4. Экранирование LaTeX-символов
    5. Очистка от emoji
    """
    # 1. Экранируем ~ которые УЖЕ есть в тексте
    text = text.replace('~', r'\textasciitilde{}')

    # 2. Нормализуем кавычки под язык (ПЕРВЫМ, пока текст чистый)
    text = normalize_quotes(text)

    # 3. Конвертируем Unicode-типографику в LaTeX
    text = unicode_to_latex(text)

    # 4. Исправляем висячие союзы/предлоги (добавляем ~)
    text = fix_widows(text)

    # 5. Экранируем спецсимволы LaTeX (кроме ~, который теперь наш)
    replacements = {
        '&': r'\&',
        '%': r'\%',
        '$': r'\$',
        '#': r'\#',
        '_': r'\_',
        '{': r'\{',
        '}': r'\}',
        '^': r'\textasciicircum{}',
    }
    for old, new in replacements.items():
        text = text.replace(old, new)

    # 6. Убираем emoji, оставляем: ASCII, кириллицу, ~, кавычки языка
    open_q, close_q = CONFIG['quotes']
    allowed_quotes = f'{open_q}{close_q}'
    text = re.sub(rf'[^\x00-\x7F\u0400-\u04FF~{re.escape(allowed_quotes)}]+', '', text)

    return text.strip()

def collect_clusters_by_depth():
    """Собираем все кластеры, группируя по глубине"""
    clusters_by_type = defaultdict(list)

    for prog in data['programs']:
        prog_name = prog['name']
        for block in prog['blocks']:
            block_type = block['type']
            clusters_by_type[block_type].append({
                'block': block,
                'program_name': prog_name
            })

    return clusters_by_type

def generate_cluster(cluster_data, question_cmd):
    """Генерация LaTeX для одного кластера"""
    block = cluster_data['block']
    program_name = escape_latex(cluster_data['program_name'])
    block_name = escape_latex(block['name'])
    block_desc = escape_latex(block['description']) if block.get('description') else ''
    block_type = block['type']
    time = get_time(block_type)

    lines = []

    # Кластер с указанием программы
    lines.append(f"\\clusterWithProgram{{{block_name}}}{{{time}}}{{{block_desc}}}{{{program_name}}}")
    lines.append("")

    # Все вопросы идут в книгу
    question_num = 1
    for q in block['questions']:
        q_text = escape_latex(q['text'])
        lines.append(f"{question_cmd}{{{question_num}. {q_text}}}")
        lines.append("")
        question_num += 1

    lines.append("")
    return "\n".join(lines)

def generate_part(part_type, clusters, is_first=True):
    """Генерация LaTeX для одной части (уровня глубины)"""
    lines = []

    # Page break перед частью (кроме первой)
    if not is_first:
        lines.append("\\newpage")
        lines.append("")

    # Заголовок части
    part_name = PART_NAMES[part_type]
    part_subtitle = PART_SUBTITLES[part_type]

    lines.append(f"\\part{{{part_name}}}")
    lines.append(f"\\partsubtitle{{{part_subtitle}}}")
    lines.append("\\programbreak")
    lines.append("")

    question_cmd = DEPTH_QUESTION[part_type]

    # Кластеры этой части
    for cluster_data in clusters:
        lines.append(generate_cluster(cluster_data, question_cmd))

    return "\n".join(lines)

# Генерация
output = []

# Преамбула
year = __import__('datetime').datetime.now().strftime('%Y')
preamble = r'''% Selfology Book 2: Путь в глубину
% Кластеры организованы по уровню глубины
% Сгенерировано: ''' + __import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M') + r'''

\documentclass[11pt,a4paper,oneside]{book}
\usepackage{selfology-book}

\begin{document}
'''

output.append(preamble)

# Обложка
book_title = CONFIG['book_title']
book_subtitle = CONFIG['book_subtitle']
output.append(f"\\bookcover{{{book_title}}}{{{book_subtitle}}}{{{year}}}")

# Оглавление (для Book 2 показываем части)
output.append("\\booktoc")

# Вступление
output.append(INTRO)

# Собираем кластеры по глубине
clusters_by_type = collect_clusters_by_depth()

# Порядок частей
depth_order = ["Foundation", "Exploration", "Integration"]

# Статистика
stats = {}

for i, depth_type in enumerate(depth_order):
    clusters = clusters_by_type[depth_type]
    stats[depth_type] = len(clusters)

    # Предупреждение перед глубокой частью
    if depth_type == "Integration":
        output.append(WARNING)

    output.append(generate_part(depth_type, clusters, is_first=(i == 0)))
    print(f"  ✓ {PART_NAMES[depth_type]} ({len(clusters)} кластеров)")

# Заключение
output.append(CONCLUSION)

output.append(r'\end{document}')

# Сохранение
with open('/home/ksnk/microservices/critical/selfology-bot/products/book/latex/selfology-book2.tex', 'w') as f:
    f.write("\n".join(output))

total_clusters = sum(stats.values())
print(f"\n✅ Сгенерировано: selfology-book2.tex")
print(f"   Foundation: {stats['Foundation']} кластеров")
print(f"   Exploration: {stats['Exploration']} кластеров")
print(f"   Integration: {stats['Integration']} кластеров")
print(f"   Всего: {total_clusters} кластеров")
