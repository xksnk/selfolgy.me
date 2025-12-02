#!/usr/bin/env python3
"""Генератор Book 2: Путь в глубину (по уровням глубины)"""

import json
import re
from collections import defaultdict

# Загрузка данных из единого источника правды
DATA_FILE = '/home/ksnk/microservices/critical/selfology-bot/intelligent_question_core/data/selfology_master.json'
with open(DATA_FILE) as f:
    data = json.load(f)

print(f"📚 Источник: selfology_master.json (v{data.get('version', '?')})")

# Преамбулы книги
INTRO = r'''
\thispagestyle{empty}
\vspace*{0.2\textheight}

{\centering\sffamily\bfseries\fontsize{24pt}{28pt}\selectfont Добро пожаловать\par}

\vspace{2em}

Эта книга — путешествие вглубь себя.

Вы будете двигаться постепенно: от простого к сложному, от поверхности к глубине.

\vspace{1.5em}
{\sffamily\bfseries Три уровня погружения}

\textbf{Часть I: Первые шаги} — мягкое начало. Знакомство с собой через простые вопросы.

\textbf{Часть II: Исследование} — погружение глубже. Здесь начинается настоящая работа.

\textbf{Часть III: Глубинная работа} — самые важные вопросы. Они требуют сил и безопасного пространства.

\vspace{1.5em}
{\sffamily\bfseries Метафора аквариума}

Представьте, что ваш разум — это аквариум.

Наверху — кристально чистая вода. Это ваше сознание — лишь 10–20\%.

Остальные 80–90\% — мутная вода на глубине. Это ваше подсознание — место, где живут настоящие причины ваших решений.

Эта книга — как сито. Вы будете доставать со дна мысли и чувства, которые обычно остаются невидимыми.

\newpage
\thispagestyle{empty}
\vspace*{0.1\textheight}

{\sffamily\bfseries Как проходить}

\textbf{Создайте пространство.} Выберите время, когда вас никто не потревожит.

\textbf{Двигайтесь последовательно.} Начните с Части I и постепенно углубляйтесь.

\textbf{Пишите от руки.} Когда вы пишете рукой, мозг обрабатывает информацию глубже.

\textbf{Не торопитесь.} Делайте перерывы между частями.

\vspace{1.5em}
{\sffamily\bfseries Время на разделы}

\textbf{5–10 минут} — вопросы Части I

\textbf{10–20 минут} — вопросы Части II

\textbf{15–30 минут} — вопросы Части III

\vspace{2em}
{\centering\itshape Готовы? Тогда начнём.\par}
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

{\centering\sffamily\bfseries\fontsize{24pt}{28pt}\selectfont В завершение\par}

\vspace{2em}

Вы прошли долгий путь — от поверхности до самой глубины.

Не важно, ответили вы на все вопросы или только на часть. Важно, что вы начали этот разговор с собой.

\vspace{1.5em}
{\sffamily\bfseries Что делать дальше}

\textbf{Перечитайте записи.} Через неделю, через месяц. Вы удивитесь, как изменится восприятие.

\textbf{Замечайте паттерны.} Какие темы повторяются? На каком уровне было сложнее всего?

\textbf{Возвращайтесь.} Эта книга не одноразовая. Вы меняетесь. Ваши ответы будут меняться вместе с вами.

\vspace{2em}
{\centering\itshape Самопознание — это не пункт назначения, а путь.\par}

\vspace{1em}
{\centering\itshape Вы уже на нём.\par}

\vspace{3em}
{\centering\sffamily Selfology — искусство понимать себя.\par}
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

# Время по типу кластера
DEPTH_TIME = {
    "Foundation": "5--10 мин",
    "Exploration": "10--20 мин",
    "Integration": "15--30 мин"
}

# Команда вопроса по типу
DEPTH_QUESTION = {
    "Foundation": "\\questionF",
    "Exploration": "\\questionE",
    "Integration": "\\questionI"
}

def escape_latex(text):
    """Экранирование спецсимволов LaTeX"""
    replacements = {
        '&': r'\&',
        '%': r'\%',
        '$': r'\$',
        '#': r'\#',
        '_': r'\_',
        '{': r'\{',
        '}': r'\}',
        '~': r'\textasciitilde{}',
        '^': r'\textasciicircum{}',
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    # Убираем emoji
    text = re.sub(r'[^\x00-\x7F\u0400-\u04FF]+', '', text)
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
    time = DEPTH_TIME.get(block_type, "10--15 мин")

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
preamble = r'''% Selfology Book 2: Путь в глубину
% Кластеры организованы по уровню глубины
% Сгенерировано: ''' + __import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M') + r'''

\documentclass[11pt,a4paper,oneside]{book}
\usepackage{selfology-book}

\begin{document}
'''

output.append(preamble)

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
