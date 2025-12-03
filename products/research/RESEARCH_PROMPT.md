# Research Prompt for Perplexity

Дата: 2025-12-01
Статус: готов к отправке

---

```
I'm designing two premium self-reflection books (PDF, A4) in three languages: Russian, English, Spanish. These are psychological self-discovery tools, not typical workbooks.

THE TWO BOOKS:

Book 1: "29 Programs of Self-Discovery" (thematic approach)
- User has a specific pain point (relationships, career, fears, health)
- Opens table of contents → finds their topic → works through clusters
- Structure: 29 programs → 3-6 clusters each → 5-8 questions per cluster
- Clusters progress from surface-level to deep within each program

Book 2: "Journey to the Depths" (progressive approach)
- User wants general self-exploration without specific focus
- Gradual deepening: Part 1 (easy) → Part 2 (medium) → Part 3 (deep)
- Topics INTERLEAVE within each depth level for variety
- Same clusters as Book 1, reorganized by depth

METADATA PER CLUSTER:
- Name (e.g., "People Around Me")
- Description (e.g., "ecosystem of influences")
- Depth level: Foundation / Exploration / Integration
- Time estimate: 5-10 / 10-20 / 15-30 minutes
- Parent program name (needed in Book 2 for context)

DESIGN CHALLENGES:

1. How to show depth levels VISUALLY (not with labels like "DEEP" or "SURFACE" — these mean nothing to users). Should feel heavier/more intense as you go deeper.

2. How to elegantly integrate metadata without it looking like a database dump. Time and context matter, but current implementation is ugly.

3. Clear visual separation between programs (Book 1) — currently they blend together.

4. How to show parent program in Book 2 without ugly [square brackets].

5. Typography that works across Cyrillic + Latin. Current PT Serif/Sans feels dated, "grandmother's books". Need modern, bold, high-contrast.

6. Visual hierarchy for nested structure: Program title >> Cluster header >> Question. Currently broken.

7. Creating psychological safety signals — visual cues that say "deep work ahead, prepare yourself" without being heavy-handed.

LOOKING FOR:

1. Modern multilingual font pairings (RU/EN/ES) — bold, contemporary, good for both headlines and body
2. How premium guided journals show difficulty/intensity through design (weight, color, spacing) not labels
3. Elegant ways to display cluster metadata (time, theme, context)
4. Visual systems for progressive depth (like dive levels, layers, stages)
5. Section dividers and program separators for clear navigation
6. Examples: Therapy workbooks, premium journals, self-help books 2022-2024 with strong design
7. How to create "breathing room" and psychological safety through layout

AESTHETIC: Minimalist but bold. High contrast. Generous whitespace. Swiss-inspired but contemporary. NOT decorative, NOT vintage, NOT corporate.
```

---

## После ресерча

Обновить:
- `templates/STYLE_SPEC.md` — новая типографика
- `templates/selfology-book.latex` — новый шаблон
- `scripts/generate_books.py` — новая структура вывода
