# Показать BACKLOG с задачами

Покажи содержимое файла `.claude/BACKLOG.md` и выдели:

## Текущие приоритеты

### P0 - Критичные задачи
```bash
grep -A 5 "### P0" .claude/BACKLOG.md | grep "\[ \]"
```

### P1 - Высокий приоритет
```bash
grep -A 5 "### P1" .claude/BACKLOG.md | grep "\[ \]"
```

## Быстрая статистика

```bash
# Всего задач
echo "Всего задач: $(grep -c '\[ \]' .claude/BACKLOG.md)"

# Завершенных задач
echo "Завершено: $(grep -c '\[x\]' .claude/BACKLOG.md)"

# В работе
echo "В работе: $(grep -c '\[WIP\]' .claude/BACKLOG.md)"
```

## Покажи полный BACKLOG

```bash
cat .claude/BACKLOG.md
```

Предложи что делать дальше исходя из приоритетов.
