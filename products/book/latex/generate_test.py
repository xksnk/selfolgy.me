#!/usr/bin/env python3
"""Генератор тестового LaTeX файла для 2 программ"""

import json

# Загрузка данных
with open('/home/ksnk/microservices/critical/selfology-bot/intelligent_question_core/data/selfology_programs_v2.json') as f:
    data = json.load(f)

# Время по типу кластера
DEPTH_TIME = {
    "Foundation": "5--10 мин",
    "Exploration": "10--20 мин",
    "Integration": "15--30 мин"
}

# Команда вопроса по типу (вопрос + линии вместе)
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
    import re
    text = re.sub(r'[^\x00-\x7F\u0400-\u04FF]+', '', text)
    return text.strip()

def generate_program(prog, is_first=True):
    """Генерация LaTeX для одной программы"""
    lines = []

    # Page break перед программой (кроме первой)
    if not is_first:
        lines.append("\\newpage")
        lines.append("")

    # Заголовок программы на отдельной странице
    name = escape_latex(prog['name'])
    lines.append(f"\\chapter{{{name}}}")
    lines.append("\\programbreak")
    lines.append("")

    # Кластеры
    for block in prog['blocks']:
        block_name = escape_latex(block['name'])
        block_desc = escape_latex(block['description']) if block['description'] else ''
        block_type = block['type']
        time = DEPTH_TIME[block_type]
        question_cmd = DEPTH_QUESTION[block_type]

        lines.append(f"\\cluster{{{block_name}}}{{{time}}}{{{block_desc}}}")
        lines.append("")

        # Вопросы (вопрос + линии = единый блок)
        for i, q in enumerate(block['questions'], 1):
            q_text = escape_latex(q['text'])
            lines.append(f"{question_cmd}{{{i}. {q_text}}}")
            lines.append("")

        lines.append("")

    return "\n".join(lines)

# Генерация
output = []

# Преамбула (копируем из test-fragment.tex, только контент меняем)
preamble = r'''% Selfology Test - 2 программы
% Для проверки page breaks и колонтитулов

\documentclass[11pt,a4paper,oneside]{book}

% ============================================
% GEOMETRY
% ============================================
\usepackage[
  a4paper,
  inner=20mm,
  outer=25mm,
  top=20mm,
  bottom=25mm,
  headheight=14pt,
  headsep=20pt,
  footskip=30pt
]{geometry}

% ============================================
% FONTS
% ============================================
\usepackage{fontspec}

\setmainfont{IBM Plex Sans}[Scale=1.0]

\setsansfont{Montserrat}[
  Path = /home/ksnk/.local/share/fonts/,
  Extension = .ttf,
  UprightFont = *-Regular,
  BoldFont = *-SemiBold,
  ItalicFont = *-Italic,
  Scale = 1.0
]

% ============================================
% LANGUAGE
% ============================================
\usepackage{polyglossia}
\setdefaultlanguage{russian}

% ============================================
% PACKAGES
% ============================================
\usepackage{xcolor}
\usepackage{titlesec}
\usepackage{fancyhdr}
\usepackage{needspace}
\usepackage{tikz}

% ============================================
% COLORS
% ============================================
\definecolor{primary}{HTML}{282828}
\definecolor{secondary}{HTML}{666666}
\definecolor{linegray}{HTML}{D0D0D0}

\color{primary}

% ============================================
% TYPOGRAPHY
% ============================================
\usepackage{microtype}
\usepackage{ragged2e}
\RaggedRight

\setlength{\parindent}{0pt}
\setlength{\parskip}{1em}

\widowpenalty=10000
\clubpenalty=10000

% ============================================
% HEADERS
% ============================================

% Запрет переносов слов
\hyphenpenalty=10000
\exhyphenpenalty=10000

% Chapter = Program (28pt) — на отдельной странице
\titleformat{\chapter}[display]
  {\thispagestyle{empty}\vspace*{0.3\textheight}\sffamily\bfseries\fontsize{28pt}{32pt}\selectfont\color{primary}}
  {}
  {0pt}
  {}
\titlespacing*{\chapter}{0pt}{0pt}{2em}

\setcounter{secnumdepth}{-1}

% После заголовка программы — новая страница
\newcommand{\programbreak}{\newpage}

% Кластер: каждый с новой страницы
\newcommand{\cluster}[3]{%
  \newpage%
  \noindent%
  {\sffamily\bfseries\fontsize{16pt}{20pt}\selectfont\color{primary}#1}%
  \hfill%
  {\small\sffamily\color{secondary}#2}%
  \par\vspace{0.3em}%
  {\itshape\color{secondary}#3}%
  \par\vspace{0.8em}%
}

% ============================================
% RUNNING HEADERS
% ============================================
\pagestyle{fancy}
\fancyhf{}

\renewcommand{\chaptermark}[1]{\markboth{#1}{#1}}

% Название программы вверху справа
\fancyhead[R]{\small\sffamily\color{secondary}\leftmark}

% Номер страницы внизу справа
\fancyfoot[R]{\small\sffamily\color{secondary}\thepage}

\renewcommand{\headrulewidth}{0pt}
\renewcommand{\footrulewidth}{0pt}

\fancypagestyle{plain}{
  \fancyhf{}
  \fancyfoot[R]{\small\sffamily\color{secondary}\thepage}
}

% ============================================
% COMMANDS
% ============================================

% Вопрос + линии = единый блок, не разрывается
% Foundation: 2 линии (~4 baselineskip)
\newcommand{\questionF}[1]{%
  \needspace{6\baselineskip}%
  \par\noindent\textbf{#1}%
  \par\vspace{0.8em}%
  \foreach \i in {1,2} {%
    \noindent\textcolor{linegray}{\rule{\linewidth}{0.4pt}}%
    \par\vspace{0.8em}%
  }%
  \vspace{0.5em}%
}

% Exploration: 3 линии (~5 baselineskip)
\newcommand{\questionE}[1]{%
  \needspace{7\baselineskip}%
  \par\noindent\textbf{#1}%
  \par\vspace{0.8em}%
  \foreach \i in {1,2,3} {%
    \noindent\textcolor{linegray}{\rule{\linewidth}{0.4pt}}%
    \par\vspace{0.8em}%
  }%
  \vspace{0.8em}%
}

% Integration: 4 линии (~6 baselineskip)
\newcommand{\questionI}[1]{%
  \needspace{8\baselineskip}%
  \par\noindent\textbf{#1}%
  \par\vspace{0.8em}%
  \foreach \i in {1,2,3,4} {%
    \noindent\textcolor{linegray}{\rule{\linewidth}{0.4pt}}%
    \par\vspace{0.8em}%
  }%
  \vspace{1em}%
}

% ============================================
% DOCUMENT
% ============================================
\begin{document}
'''

output.append(preamble)

# Программа 1
output.append(generate_program(data['programs'][0], is_first=True))

# Программа 2
output.append(generate_program(data['programs'][1], is_first=False))

# Программа 3
output.append(generate_program(data['programs'][2], is_first=False))

output.append(r'\end{document}')

# Сохранение
with open('/home/ksnk/microservices/critical/selfology-bot/products/book/latex/test-2programs.tex', 'w') as f:
    f.write("\n".join(output))

print("Generated: test-2programs.tex")
