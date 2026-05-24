# Thumbnail Creator — LangGraph Reflexion Agent

A LangGraph agent that designs YouTube thumbnails through iterative self-criticism.  
Hand it a video topic → it searches the web → builds a visual strategy → generates an image → critiques it → loops until the score is good enough → saves the best result.

**Tech stack:** LangGraph 0.2+, LangChain OpenAI, `gpt-image-1` + GPT-4o vision, Tavily, Pydantic v2, python-dotenv, rich, Pillow

---

## How it works

![Architecture diagram](thumbnail_agent/graph.png)

### Node breakdown

| Node | What it does |
|------|-------------|
| `web_search` | Runs two Tavily searches (viral hooks + visual trends) and merges them into `search_summary`. Runs once before the loop. |
| `strategy` | `gpt-4o` with a structured JSON schema — produces a visual blueprint: archetype, dominant subject, brand elements, composition, text overlay, and what to avoid |
| `prompt_writer` | Translates the strategy JSON into a `gpt-image-1` prompt. On loop iterations, the full critique history is injected so every previous weakness is explicitly addressed |
| `generator` | Calls `gpt-image-1` (1536×1024, 16:9), saves `iter_N.png`, then composites real brand logos (Claude, OpenAI, Gemini, etc.) via PIL |
| `critic` | Vision LLM (`gpt-4o`) reads the PNG and returns a structured score (1–10) + critique via `with_structured_output(CritiqueOutput)`. Strict by design — most thumbnails score 5–7 so the loop actually fires |
| `should_continue` | Conditional edge — loops back to `prompt_writer` if score < target **and** iterations remain; otherwise routes to `saver` |
| `saver` | Picks the highest-rated image from `history`, copies it as `final.png`, writes `report.md` with a full iteration table and per-iteration details |

### Reflexion loop

```
START → web_search → strategy ──────────────────────────────── (runs once)
                                  │
                                  ▼
              ┌─────────────────────────────────────┐
              │  score < target AND iter < max_iter  │
              ▼                                      │
        prompt_writer → generator → critic ──────────┘
                                         └──► saver → END  (score OK or cap hit)
```

The loop is wired as a **conditional edge** (`add_conditional_edges`) from `critic` to `{prompt_writer, saver}`. The `history` field uses `Annotated[list, operator.add]` so every iteration's prompt + image path + score + critique accumulates instead of overwriting.

---

## Project structure

```
Thumbnail-Creator/
├── .env                          ← API keys (never committed)
├── .gitignore
├── pyproject.toml
├── README.md
├── assets/
│   └── logos/                    ← official brand PNGs composited after generation
│       ├── claude.png
│       ├── claude-code.png
│       ├── openai.png
│       ├── gemini.png
│       ├── copilot.png
│       └── perplexity.png
└── thumbnail_agent/
    ├── __init__.py               ← load_dotenv() so all submodules pick up API keys
    ├── state.py                  ← ThumbnailState TypedDict + history append reducer
    ├── prompts.py                ← STRATEGY_SYSTEM, PROMPT_WRITER_SYSTEM, CRITIC_SYSTEM
    ├── tools.py                  ← Tavily search wrapper
    ├── nodes.py                  ← 6 node functions + CritiqueOutput + should_continue
    ├── compositor.py             ← PIL logo compositing (bottom-right, stacked left)
    ├── graph.py                  ← build_graph() wires nodes + edges, returns compiled graph
    ├── main.py                   ← CLI entry point
    ├── make_diagram.py           ← writes graph.mmd + graph.png
    ├── graph.mmd                 ← Mermaid source with per-node colors
    ├── graph.png                 ← rendered architecture diagram
    └── outputs/                  ← (gitignored) timestamped run folders go here
        └── 20260524_113036_claude_code_replaced.../
            ├── iter_1.png
            ├── iter_2.png
            ├── iter_3.png
            ├── final.png
            └── report.md
```

---

## Setup

### 1. Prerequisites

- Python 3.11+
- [`uv`](https://docs.astral.sh/uv/) installed

### 2. Clone & create the virtual environment

```bash
git clone https://github.com/SQLicious/AgentBuilder_HW_Reflection-Agent-Thumbail-Generator.git
cd AgentBuilder_HW_Reflection-Agent-Thumbail-Generator

uv venv .venv --python 3.11
```

### 3. Install dependencies

```bash
# macOS / Linux
uv pip install -e . --python .venv/bin/python

# Windows PowerShell
uv pip install -e . --python .venv\Scripts\python.exe
```

### 4. Add your API keys

Create a `.env` file in the project root:

```env
OPENAI_API_KEY=sk-proj-...your-key...
TAVILY_API_KEY=tvly-...your-key...
```

> **OpenAI** — needs access to `gpt-4o` and `gpt-image-1`  
> **Tavily** — free tier is plenty (sign up at [tavily.com](https://tavily.com))

---

## Running the agent

Activate the venv first:

```bash
# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate
```

### Basic run

```bash
python -m thumbnail_agent.main "Why Python is the best language for AI"
```

### Streaming mode (see each node update live)

```bash
python -m thumbnail_agent.main "Why Python is the best language for AI" --stream
```

### Custom thresholds

```bash
# stop at score 7, allow up to 4 iterations
python -m thumbnail_agent.main "10x Productivity with VS Code" --target-rating 7 --max-iterations 4
```

### Regenerate the graph diagram

```bash
python -m thumbnail_agent.make_diagram
# writes thumbnail_agent/graph.mmd and thumbnail_agent/graph.png
```

---

## Output

Each run creates a timestamped folder under `outputs/`:

```
outputs/20260524_113036_claude_code_replaced_my_engineering_team/
├── iter_1.png      ← first generated thumbnail (brand logos composited)
├── iter_2.png      ← second attempt (loop fired)
├── iter_3.png      ← third attempt
├── final.png       ← copy of the highest-rated image
└── report.md       ← full history: prompts, scores, critiques
```

### Sample `report.md` excerpt

```markdown
# Thumbnail Report: Claude Code replaced my engineering team

**Best score:** 8/10
**Total iterations:** 3

| Iter | Score | Critique |
|------|-------|----------|
| 1    | 7/10  | The connection to "Claude Code" is missing, limiting specific intrigue... |
| 2    | 6/10  | The Claude logo isn't evident, losing potential clicks from those... |
| 3    | 8/10  | Clarity & Impact: The focal subject is clear, with an intense emotional... |

### Iteration 1 — Score 7/10

**Prompt:** A shocked engineer with a large, exaggerated expression...
**Critique:** STRENGTHS: Expression is dramatic. CRITICAL ISSUES: No Claude branding...
```

---

## Architecture decisions

| Decision | Reason |
|----------|--------|
| 6 nodes instead of 5 | Added a dedicated `strategy` node between `web_search` and `prompt_writer` — strategy uses `gpt-4o` to produce structured JSON; separating it keeps `prompt_writer` focused on prompt execution only |
| `history: Annotated[list, operator.add]` | LangGraph's append reducer keeps all iterations; default assignment would overwrite, losing earlier critiques needed for the final report |
| `with_structured_output(CritiqueOutput)` | Guarantees `rating` is always an `int` — the conditional edge (`should_continue`) depends on it for routing |
| Brand logos composited via PIL, never generated | `gpt-image-1` cannot reliably reproduce trademarked logos. `compositor.py` overlays official PNGs from `assets/logos/` post-generation so brand marks are always accurate |
| Strict critic with 10-dimension scoring + automatic score caps | Most thumbnails score 5–7 on first attempt, ensuring the loop actually fires. A 9+ is rare by design |
| `graph.compile()` plain (no checkpointer) | Keeps it simple; checkpointers are not required for this assignment |

---

## Environment variables reference

| Variable | Required | Description |
|----------|----------|-------------|
| `OPENAI_API_KEY` | Yes | OpenAI project API key (needs `gpt-4o` + `gpt-image-1`) |
| `TAVILY_API_KEY` | Yes | Tavily search API key |
