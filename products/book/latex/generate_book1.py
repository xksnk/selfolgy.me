#!/usr/bin/env python3
"""Генератор Book 1: Полная книга по программам"""

import json
import re

# Загрузка данных
with open('/home/ksnk/microservices/critical/selfology-bot/intelligent_question_core/data/selfology_programs_v2.json') as f:
    data = json.load(f)

# Преамбулы книги
INTRO = r'''
\thispagestyle{empty}
\vspace*{0.2\textheight}

{\centering\sffamily\bfseries\fontsize{24pt}{28pt}\selectfont Добро пожаловать\par}

\vspace{2em}

Эта книга — не тест и не анкета. Это пространство для встречи с собой.

Здесь нет правильных или неправильных ответов. Есть только ваши — честные, настоящие, живые.

\vspace{1.5em}
{\sffamily\bfseries Как устроена эта книга}

Вы увидите три уровня вопросов:

\textbf{Поверхность} — лёгкие вопросы для разминки. Они помогут настроиться и войти в контакт с собой.

\textbf{Исследование} — вопросы глубже. Здесь начинается настоящая работа. Может быть некомфортно — это нормально.

\textbf{Глубина} — самые важные вопросы. Они требуют сил, времени и безопасного пространства.

\vspace{1.5em}
{\sffamily\bfseries Метафора аквариума}

Представьте, что ваш разум — это аквариум.

Наверху — кристально чистая вода. Там вы ясно видите свои мысли, желания, решения. Но эта часть составляет лишь 10–20\%. Это ваше сознание.

Остальные 80–90\% — мутная вода на глубине. Там трудно что-то разглядеть. Это ваше подсознание — место, где живут настоящие причины ваших решений, страхов и желаний.

Эта книга — как сито. Вы будете доставать со дна мысли и чувства, которые обычно остаются невидимыми.

\newpage
\thispagestyle{empty}
\vspace*{0.1\textheight}

{\sffamily\bfseries Как проходить}

\textbf{Создайте пространство.} Выберите время, когда вас никто не потревожит.

\textbf{Настройтесь.} Налейте себе любимый напиток. Устройтесь удобно. Дайте себе разрешение на честность.

\textbf{Пишите от руки.} Когда вы пишете рукой, мозг обрабатывает информацию глубже.

\textbf{Не торопитесь.} У каждого вопроса указано рекомендуемое время. Но это лишь ориентир.

\vspace{1.5em}
{\sffamily\bfseries Техника безопасности}

Вам понадобятся силы на это путешествие.

Не пытайтесь пройти всё за один раз. Двигайтесь в своём темпе. Делайте перерывы.

Если какой-то вопрос вызывает сильные эмоции — это знак того, что вы коснулись чего-то важного. Побудьте с этим бережно.

\vspace{1.5em}
{\sffamily\bfseries Время на разделы}

\textbf{5–10 минут} — вопросы уровня Поверхность

\textbf{10–20 минут} — вопросы уровня Исследование

\textbf{15–30 минут} — вопросы уровня Глубина

\vspace{2em}
{\centering\itshape Готовы? Тогда начнём.\par}
'''

CONCLUSION = r'''
\newpage
\thispagestyle{empty}
\vspace*{0.2\textheight}

{\centering\sffamily\bfseries\fontsize{24pt}{28pt}\selectfont В завершение\par}

\vspace{2em}

Вы прошли долгий путь.

Не важно, ответили вы на все вопросы или только на часть. Важно, что вы начали этот разговор с собой.

\vspace{1.5em}
{\sffamily\bfseries Что делать дальше}

\textbf{Перечитайте записи.} Через неделю, через месяц. Вы удивитесь, как изменится восприятие.

\textbf{Замечайте паттерны.} Какие темы повторяются? Какие вопросы было сложнее всего отвечать? Там — ваши точки роста.

\textbf{Возвращайтесь.} Эта книга не одноразовая. Вы меняетесь. Ваши ответы будут меняться вместе с вами.

\textbf{Действуйте.} Понимание — это первый шаг. Но настоящие изменения происходят через действие.

\vspace{2em}
{\centering\itshape Самопознание — это не пункт назначения, а путь.\par}

\vspace{1em}
{\centering\itshape Вы уже на нём.\par}

\vspace{3em}
{\centering\sffamily Selfology — искусство понимать себя.\par}
'''

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

def generate_program(prog, is_first=True):
    """Генерация LaTeX для одной программы"""
    lines = []

    # Page break перед программой (кроме первой)
    if not is_first:
        lines.append("\\newpage")
        lines.append("")

    # Заголовок программы
    name = escape_latex(prog['name'])
    lines.append(f"\\chapter{{{name}}}")
    lines.append("\\programbreak")
    lines.append("")

    # Кластеры
    for block in prog['blocks']:
        block_name = escape_latex(block['name'])
        block_desc = escape_latex(block['description']) if block.get('description') else ''
        block_type = block['type']
        time = DEPTH_TIME.get(block_type, "10--15 мин")
        question_cmd = DEPTH_QUESTION.get(block_type, "\\questionE")

        lines.append(f"\\cluster{{{block_name}}}{{{time}}}{{{block_desc}}}")
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

# Генерация
output = []

# Преамбула с использованием стиля
preamble = r'''% Selfology Book 1: Тематические программы
% Полная книга - 29 программ, 190 кластеров
% Сгенерировано: ''' + __import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M') + r'''

\documentclass[11pt,a4paper,oneside]{book}
\usepackage{selfology-book}

\begin{document}
'''

output.append(preamble)

# Вступление
output.append(INTRO)

# Все программы
for i, prog in enumerate(data['programs']):
    output.append(generate_program(prog, is_first=(i == 0)))
    print(f"  ✓ {prog['name']} ({len(prog['blocks'])} кластеров)")

# Заключение
output.append(CONCLUSION)

output.append(r'\end{document}')

# Сохранение
with open('/home/ksnk/microservices/critical/selfology-bot/products/book/latex/selfology-book1.tex', 'w') as f:
    f.write("\n".join(output))

print(f"\n✅ Сгенерировано: selfology-book1.tex")
print(f"   Программ: {len(data['programs'])}")
print(f"   Кластеров: {data['metadata']['total_blocks']}")
print(f"   Вопросов: {data['metadata']['total_questions']}")
