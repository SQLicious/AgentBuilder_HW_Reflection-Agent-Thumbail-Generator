# Thumbnail Creator — Reflexion Agent Design

**Date:** 2026-05-24  
**Assignment:** YouTube Thumbnail Designer (LangGraph Reflexion Agent)

---

## Overview

A LangGraph state machine that takes a video topic, generates a YouTube thumbnail via gpt-image-1, critiques it with GPT-4o vision, and loops until the rating meets a target or an iteration cap is hit. Outputs `final.png` + `report.md` per run.

---

## State Schema (`state.py`)

`TypedDict` with an append-reducer on `history`:

```python
class ThumbnailState(TypedDict):
    topic: str
    search_summary: str
    current_prompt: str
    image_path: str
    rating: int
    critique: str
    iteration: int
    history: Annotated[list[dict], operator.add]   # reducer: accumulates
    target_rating: int      # default 8
    max_iterations: int     # default 3
    output_dir: str
```

Each `history` entry: `{iteration, prompt, image_path, rating, critique}`.

---

## Graph Architecture (`graph.py`)

**Flow:**

```
START → web_search → prompt_writer → generator → critic
                          ▲                          │
                          │   score < target         │  should_continue
                          │   AND iter < max         │
                          └──────────────────────────┤
                                                     │  score >= target
                                                     │  OR iter >= max
                                                     ▼
                                                   saver → END
```

5 nodes registered with `add_node`. 1 conditional edge via `add_conditional_edges` from `critic` to `{prompt_writer, saver}`.

---

## Nodes (`nodes.py`)

### `web_search`
- Calls Tavily search with the topic
- Writes `search_summary` to state
- Runs once (before loop)

### `prompt_writer`
- Input: `topic`, `search_summary`, `critique` (empty on iter 1)
- Calls GPT-4o with system prompt from `prompts.py`
- On iteration > 1: incorporates previous critique explicitly
- Writes `current_prompt` to state

### `generator`
- Calls `openai.images.generate(model="gpt-image-1", size="1536x1024")`
- Increments `iteration`
- Saves PNG as `outputs/<ts>_<topic>/iter_N.png`
- Writes `image_path` to state

### `critic`
- Reads PNG, encodes as base64 data URL
- Calls GPT-4o with `with_structured_output(CritiqueOutput)` where:
  ```python
  class CritiqueOutput(BaseModel):
      rating: int       # 1-10, strict — most thumbnails 5-7
      critique: str     # actionable, specific
  ```
- Appends `{iteration, prompt, image_path, rating, critique}` to `history`
- Writes `rating`, `critique` to state

### `saver`
- Picks highest-rated entry from `history`
- Copies that image as `final.png`
- Writes `report.md` with all iterations in a markdown table + details
- Returns final state

### `should_continue` (conditional edge function)
```python
def should_continue(state) -> str:
    if state["rating"] >= state["target_rating"]:
        return "saver"
    if state["iteration"] >= state["max_iterations"]:
        return "saver"
    return "prompt_writer"
```

---

## Prompts (`prompts.py`)

**Prompt writer system prompt:**
- Forbids AI clichés ("delve", "in today's world", "unleash")
- Requires concrete visual elements: focal subject, text overlay position, color palette, lighting, mood, background
- On revision: must address every point from the critique explicitly

**Critic system prompt:**
- Be strict — most thumbnails score 5-7, 9+ exceptional
- Rate on: visual clarity, text readability, click-worthiness, relevance to topic, composition
- Critique must be actionable (specific changes, not vague feedback)

---

## Tools (`tools.py`)

Single Tavily wrapper:
```python
def search_topic(topic: str) -> str:
    # TavilyClient().search(topic, max_results=5)
    # Returns summarised text of top results
```

---

## Entry Point (`main.py`)

```bash
python -m thumbnail_agent.main "Why Python is best for AI"
python -m thumbnail_agent.main "..." --stream
```

- `--stream`: uses `graph.stream()` and prints each node update via `rich`
- Default: `graph.invoke()` then prints final report path

---

## Diagram (`make_diagram.py`)

```bash
python -m thumbnail_agent.make_diagram   # writes graph.png
```

Uses `graph.get_graph().draw_mermaid_png()`.

---

## File Outputs

```
outputs/<timestamp>_<topic_slug>/
  iter_1.png
  iter_2.png       # if loop fired
  final.png        # copy of best-rated
  report.md        # iteration table + per-iteration details
```

---

## Package Init (`__init__.py`)

`load_dotenv()` so all submodules pick up `OPENAI_API_KEY` and `TAVILY_API_KEY`.

---

## Grading Checklist

| # | Criterion | Covered by |
|---|---|---|
| 1 | Compiles and runs end-to-end | All files + `uv sync` |
| 2 | 5 nodes + conditional edge | `graph.py` |
| 3 | Loop fires (iter ≥ 2) | Strict critic prompt |
| 4 | Structured output (Pydantic int rating) | `CritiqueOutput` in `nodes.py` |
| 5 | History append reducer | `Annotated[list, operator.add]` in `state.py` |
| 6 | `final.png` + `report.md` | `saver` node |
| 7 | `graph.png` via `make_diagram.py` | `make_diagram.py` |
| 8 | Clean multi-file layout | 7 separate files |
