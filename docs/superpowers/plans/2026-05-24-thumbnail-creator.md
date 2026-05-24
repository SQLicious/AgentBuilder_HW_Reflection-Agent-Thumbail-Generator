# Thumbnail Creator — Reflexion Agent Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a LangGraph reflexion agent that generates YouTube thumbnails via gpt-image-1, critiques them with GPT-4o vision, and loops until quality meets a target score or iteration cap is hit.

**Architecture:** 5-node LangGraph state machine (`web_search → prompt_writer → generator → critic → [loop/save]`) driven by a `TypedDict` state with an append-reducer on `history`. All prompt strings live in `prompts.py`; all business logic lives in `nodes.py`. `should_continue` is the conditional edge function.

**Tech Stack:** LangGraph 0.2+, LangChain OpenAI, OpenAI gpt-image-1 + GPT-4o vision, Tavily, Pydantic v2, python-dotenv, rich, pytest, pytest-mock

---

## File Map

| File | Responsibility |
|---|---|
| `thumbnail_agent/__init__.py` | `load_dotenv()` — runs on every package import |
| `thumbnail_agent/state.py` | `ThumbnailState` TypedDict with `Annotated[list[dict], operator.add]` reducer on `history` |
| `thumbnail_agent/prompts.py` | `PROMPT_WRITER_SYSTEM`, `CRITIC_SYSTEM` strings only — zero logic |
| `thumbnail_agent/tools.py` | `search_topic(topic)` Tavily wrapper |
| `thumbnail_agent/nodes.py` | `CritiqueOutput` Pydantic model, 5 node functions, `should_continue` |
| `thumbnail_agent/graph.py` | `build_graph()` — wires all nodes/edges, returns compiled graph |
| `thumbnail_agent/main.py` | CLI: `python -m thumbnail_agent.main "topic" [--stream]` |
| `thumbnail_agent/make_diagram.py` | `python -m thumbnail_agent.make_diagram` → writes `graph.png` |
| `tests/__init__.py` | Empty |
| `tests/test_state.py` | Reducer behavior |
| `tests/test_prompts.py` | Prompt strings contain required elements |
| `tests/test_tools.py` | Tavily wrapper with mock |
| `tests/test_should_continue.py` | All 3 branches of conditional edge |
| `tests/test_nodes.py` | Each node with mocked API calls |
| `tests/test_graph.py` | Graph compiles, correct nodes/edges present |

---

## Task 1: Dev deps + `__init__.py` + `state.py`

**Files:**
- Modify: `pyproject.toml`
- Create: `thumbnail_agent/__init__.py`
- Create: `thumbnail_agent/state.py`
- Create: `tests/__init__.py`
- Create: `tests/test_state.py`

- [ ] **Step 1: Add dev dependencies to `pyproject.toml`**

```toml
[dependency-groups]
dev = [
    "pytest>=8.0.0",
    "pytest-mock>=3.0.0",
]
```

- [ ] **Step 2: Sync**

```bash
uv sync
```

Expected: Resolves successfully, `pytest` and `pytest-mock` available.

- [ ] **Step 3: Write failing test**

`tests/__init__.py` — empty file.

```python
# tests/test_state.py
import operator
from thumbnail_agent.state import ThumbnailState


def test_history_reducer_accumulates():
    h1 = [{"iteration": 1, "rating": 5}]
    h2 = [{"iteration": 2, "rating": 7}]
    assert operator.add(h1, h2) == [
        {"iteration": 1, "rating": 5},
        {"iteration": 2, "rating": 7},
    ]


def test_state_fields_exist():
    state: ThumbnailState = {
        "topic": "test",
        "search_summary": "",
        "current_prompt": "",
        "image_path": "",
        "rating": 0,
        "critique": "",
        "iteration": 0,
        "history": [],
        "target_rating": 8,
        "max_iterations": 3,
        "output_dir": "outputs/test",
    }
    assert state["topic"] == "test"
    assert state["history"] == []
```

- [ ] **Step 4: Run — expect ImportError**

```bash
uv run pytest tests/test_state.py -v
```

Expected: `ImportError: cannot import name 'ThumbnailState'`

- [ ] **Step 5: Create `thumbnail_agent/__init__.py`**

```python
from dotenv import load_dotenv

load_dotenv()
```

- [ ] **Step 6: Create `thumbnail_agent/state.py`**

```python
import operator
from typing import Annotated

from typing_extensions import TypedDict


class ThumbnailState(TypedDict):
    topic: str
    search_summary: str
    current_prompt: str
    image_path: str
    rating: int
    critique: str
    iteration: int
    history: Annotated[list[dict], operator.add]
    target_rating: int
    max_iterations: int
    output_dir: str
```

- [ ] **Step 7: Run — expect 2 passed**

```bash
uv run pytest tests/test_state.py -v
```

- [ ] **Step 8: Commit**

```bash
git add pyproject.toml uv.lock thumbnail_agent/__init__.py thumbnail_agent/state.py tests/__init__.py tests/test_state.py
git commit -m "feat: add state schema and dev deps"
```

---

## Task 2: `prompts.py`

**Files:**
- Create: `thumbnail_agent/prompts.py`
- Create: `tests/test_prompts.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_prompts.py
from thumbnail_agent.prompts import CRITIC_SYSTEM, PROMPT_WRITER_SYSTEM


def test_prompt_writer_forbids_cliches_and_requires_visual_elements():
    text = PROMPT_WRITER_SYSTEM.lower()
    assert "delve" not in text
    assert "focal subject" in text
    assert "text overlay" in text
    assert "color palette" in text


def test_critic_enforces_strict_scoring():
    assert "5" in CRITIC_SYSTEM
    assert "9" in CRITIC_SYSTEM
    assert "actionable" in CRITIC_SYSTEM.lower()
```

- [ ] **Step 2: Run — expect ImportError**

```bash
uv run pytest tests/test_prompts.py -v
```

- [ ] **Step 3: Create `thumbnail_agent/prompts.py`**

```python
PROMPT_WRITER_SYSTEM = """\
You are a YouTube thumbnail art director. Write a single precise image-generation \
prompt for a 1536x1024 YouTube thumbnail.

Rules:
- NEVER use vague AI filler: no "delve", "in today's world", "unleash", \
"game-changer", "cutting-edge", "revolutionize"
- ALWAYS specify ALL of these visual elements:
  1. Focal subject — the main visual focus, described precisely
  2. Text overlay — exact text, position (top-left/center/bottom-right/etc), \
font style (bold/clean/handwritten/etc)
  3. Color palette — 2-3 dominant colors
  4. Lighting — e.g. dramatic side-lighting, soft studio light, neon glow
  5. Mood/emotion — e.g. urgency, curiosity, excitement, authority
  6. Background — e.g. simple dark gradient, blurred cityscape, solid color
- Output ONLY the prompt text. No preamble, no explanation.

When revising based on critique: address EVERY critique point explicitly. \
If the critique says "text is hard to read", specify white bold text with a dark drop shadow.\
"""

CRITIC_SYSTEM = """\
You are a brutally honest YouTube thumbnail critic. Your ratings are strict.

Scoring guide:
- 1-4: Severely flawed (illegible, irrelevant, ugly)
- 5-7: Average. Most thumbnails land here. Something is off — cluttered layout, \
weak text contrast, unclear focal subject, or poor composition.
- 8: Good. Click-worthy, clear, visually compelling. Genuinely rare.
- 9-10: Exceptional. Only for thumbnails that are outstanding in every dimension. Very rare.

Evaluate on:
1. Visual clarity — is the focal subject immediately obvious?
2. Text readability — can the text overlay be read in 1 second at thumbnail size?
3. Click-worthiness — does it create curiosity or compel a click?
4. Topic relevance — does it accurately represent the video topic?
5. Composition — is the layout balanced and professional?

Your critique must be actionable: specify exact changes \
(e.g. "move text to top-left and increase font size", \
"add dark vignette behind subject to separate from background", \
"replace sentence with a single bold keyword"). \
No vague feedback like "improve the design".\
"""
```

- [ ] **Step 4: Run — expect 2 passed**

```bash
uv run pytest tests/test_prompts.py -v
```

- [ ] **Step 5: Commit**

```bash
git add thumbnail_agent/prompts.py tests/test_prompts.py
git commit -m "feat: add prompt strings for writer and critic nodes"
```

---

## Task 3: `tools.py`

**Files:**
- Create: `thumbnail_agent/tools.py`
- Create: `tests/test_tools.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_tools.py
from unittest.mock import MagicMock, patch


def test_search_topic_returns_joined_snippets():
    mock_results = {
        "results": [
            {"content": "Python is widely used for AI."},
            {"content": "Libraries like PyTorch are popular."},
        ]
    }
    with patch("thumbnail_agent.tools.TavilyClient") as MockClient:
        instance = MockClient.return_value
        instance.search.return_value = mock_results

        from thumbnail_agent.tools import search_topic
        result = search_topic("Python AI")

    assert "Python is widely used for AI." in result
    assert "Libraries like PyTorch are popular." in result
    instance.search.assert_called_once_with("Python AI", max_results=5)


def test_search_topic_handles_empty_results():
    with patch("thumbnail_agent.tools.TavilyClient") as MockClient:
        MockClient.return_value.search.return_value = {"results": []}
        from thumbnail_agent.tools import search_topic
        result = search_topic("obscure topic")
    assert result == ""
```

- [ ] **Step 2: Run — expect ImportError**

```bash
uv run pytest tests/test_tools.py -v
```

- [ ] **Step 3: Create `thumbnail_agent/tools.py`**

```python
from tavily import TavilyClient


def search_topic(topic: str) -> str:
    client = TavilyClient()
    results = client.search(topic, max_results=5)
    snippets = [r["content"] for r in results.get("results", [])]
    return "\n\n".join(snippets)
```

- [ ] **Step 4: Run — expect 2 passed**

```bash
uv run pytest tests/test_tools.py -v
```

- [ ] **Step 5: Commit**

```bash
git add thumbnail_agent/tools.py tests/test_tools.py
git commit -m "feat: add Tavily search wrapper"
```

---

## Task 4: `nodes.py` — skeleton + `should_continue` + `CritiqueOutput`

**Files:**
- Create: `thumbnail_agent/nodes.py`
- Create: `tests/test_should_continue.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_should_continue.py
from thumbnail_agent.nodes import should_continue


def _state(rating, iteration, target=8, max_iter=3):
    return {
        "rating": rating,
        "iteration": iteration,
        "target_rating": target,
        "max_iterations": max_iter,
    }


def test_routes_to_saver_when_rating_meets_target():
    assert should_continue(_state(rating=8, iteration=1)) == "saver"


def test_routes_to_saver_when_rating_exceeds_target():
    assert should_continue(_state(rating=9, iteration=1)) == "saver"


def test_routes_to_saver_when_iteration_cap_hit():
    assert should_continue(_state(rating=5, iteration=3)) == "saver"


def test_routes_to_prompt_writer_when_below_target_and_under_cap():
    assert should_continue(_state(rating=6, iteration=2)) == "prompt_writer"
```

- [ ] **Step 2: Run — expect ImportError**

```bash
uv run pytest tests/test_should_continue.py -v
```

- [ ] **Step 3: Create `thumbnail_agent/nodes.py` skeleton**

```python
import base64
import shutil
from pathlib import Path

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from openai import OpenAI
from pydantic import BaseModel

from .prompts import CRITIC_SYSTEM, PROMPT_WRITER_SYSTEM
from .state import ThumbnailState
from .tools import search_topic


class CritiqueOutput(BaseModel):
    rating: int
    critique: str


def should_continue(state: ThumbnailState) -> str:
    if state["rating"] >= state["target_rating"]:
        return "saver"
    if state["iteration"] >= state["max_iterations"]:
        return "saver"
    return "prompt_writer"


def web_search(state: ThumbnailState) -> dict:
    raise NotImplementedError


def prompt_writer(state: ThumbnailState) -> dict:
    raise NotImplementedError


def generator(state: ThumbnailState) -> dict:
    raise NotImplementedError


def critic(state: ThumbnailState) -> dict:
    raise NotImplementedError


def saver(state: ThumbnailState) -> dict:
    raise NotImplementedError
```

- [ ] **Step 4: Run — expect 4 passed**

```bash
uv run pytest tests/test_should_continue.py -v
```

- [ ] **Step 5: Commit**

```bash
git add thumbnail_agent/nodes.py tests/test_should_continue.py
git commit -m "feat: add nodes skeleton, CritiqueOutput model, should_continue logic"
```

---

## Task 5: `nodes.py` — `web_search` + `prompt_writer`

**Files:**
- Modify: `thumbnail_agent/nodes.py`
- Create: `tests/test_nodes.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_nodes.py
from unittest.mock import MagicMock, patch


def _base_state(**kwargs):
    return {
        "topic": "Python AI",
        "search_summary": "",
        "current_prompt": "",
        "image_path": "",
        "rating": 0,
        "critique": "",
        "iteration": 0,
        "history": [],
        "target_rating": 8,
        "max_iterations": 3,
        "output_dir": "outputs/test",
        **kwargs,
    }


def test_web_search_writes_summary():
    with patch("thumbnail_agent.nodes.search_topic", return_value="Python is great for AI."):
        from thumbnail_agent.nodes import web_search
        result = web_search(_base_state())
    assert result == {"search_summary": "Python is great for AI."}


def test_prompt_writer_first_iteration():
    mock_llm = MagicMock()
    mock_llm.invoke.return_value = MagicMock(content="A bold thumbnail prompt.")
    with patch("thumbnail_agent.nodes.ChatOpenAI", return_value=mock_llm):
        from thumbnail_agent.nodes import prompt_writer
        result = prompt_writer(_base_state(search_summary="Python is great."))
    assert result == {"current_prompt": "A bold thumbnail prompt."}


def test_prompt_writer_includes_critique_on_revision():
    mock_llm = MagicMock()
    mock_llm.invoke.return_value = MagicMock(content="Revised prompt.")
    with patch("thumbnail_agent.nodes.ChatOpenAI", return_value=mock_llm):
        from thumbnail_agent.nodes import prompt_writer
        state = _base_state(
            search_summary="Python is great.",
            critique="Text too small, no focal subject.",
            iteration=1,
        )
        result = prompt_writer(state)

    messages = mock_llm.invoke.call_args[0][0]
    human_content = messages[1].content
    assert "Text too small" in human_content
    assert result == {"current_prompt": "Revised prompt."}
```

- [ ] **Step 2: Run — expect NotImplementedError**

```bash
uv run pytest tests/test_nodes.py::test_web_search_writes_summary tests/test_nodes.py::test_prompt_writer_first_iteration tests/test_nodes.py::test_prompt_writer_includes_critique_on_revision -v
```

- [ ] **Step 3: Implement `web_search` and `prompt_writer` in `nodes.py`**

Replace the `web_search` and `prompt_writer` stubs:

```python
def web_search(state: ThumbnailState) -> dict:
    summary = search_topic(state["topic"])
    return {"search_summary": summary}


def prompt_writer(state: ThumbnailState) -> dict:
    llm = ChatOpenAI(model="gpt-4o")
    user_content = f"Topic: {state['topic']}\n\nWeb research:\n{state['search_summary']}"
    if state.get("critique"):
        user_content += (
            f"\n\nPrevious critique (address every point):\n{state['critique']}"
        )
    response = llm.invoke([
        SystemMessage(content=PROMPT_WRITER_SYSTEM),
        HumanMessage(content=user_content),
    ])
    return {"current_prompt": response.content}
```

- [ ] **Step 4: Run — expect 3 passed**

```bash
uv run pytest tests/test_nodes.py::test_web_search_writes_summary tests/test_nodes.py::test_prompt_writer_first_iteration tests/test_nodes.py::test_prompt_writer_includes_critique_on_revision -v
```

- [ ] **Step 5: Commit**

```bash
git add thumbnail_agent/nodes.py tests/test_nodes.py
git commit -m "feat: implement web_search and prompt_writer nodes"
```

---

## Task 6: `nodes.py` — `generator`

**Files:**
- Modify: `thumbnail_agent/nodes.py`
- Modify: `tests/test_nodes.py`

- [ ] **Step 1: Add failing test to `tests/test_nodes.py`**

Add `import base64` at the top of the file, then append:

```python
def test_generator_saves_png_and_increments_iteration(tmp_path):
    import base64 as b64
    fake_b64 = b64.b64encode(b"fakepngbytes").decode()
    mock_response = MagicMock()
    mock_response.data = [MagicMock(b64_json=fake_b64)]

    mock_client = MagicMock()
    mock_client.images.generate.return_value = mock_response

    with patch("thumbnail_agent.nodes.OpenAI", return_value=mock_client):
        from thumbnail_agent.nodes import generator
        from pathlib import Path
        state = _base_state(
            current_prompt="A great thumbnail prompt.",
            iteration=0,
            output_dir=str(tmp_path),
        )
        result = generator(state)

    assert result["iteration"] == 1
    saved = Path(result["image_path"])
    assert saved.exists()
    assert saved.name == "iter_1.png"
    assert saved.read_bytes() == b"fakepngbytes"
    mock_client.images.generate.assert_called_once_with(
        model="gpt-image-1",
        prompt="A great thumbnail prompt.",
        size="1536x1024",
        n=1,
    )
```

- [ ] **Step 2: Run — expect NotImplementedError**

```bash
uv run pytest tests/test_nodes.py::test_generator_saves_png_and_increments_iteration -v
```

- [ ] **Step 3: Implement `generator` in `nodes.py`**

Replace the `generator` stub:

```python
def generator(state: ThumbnailState) -> dict:
    client = OpenAI()
    iteration = state["iteration"] + 1
    output_dir = Path(state["output_dir"])
    output_dir.mkdir(parents=True, exist_ok=True)

    response = client.images.generate(
        model="gpt-image-1",
        prompt=state["current_prompt"],
        size="1536x1024",
        n=1,
    )
    img_bytes = base64.b64decode(response.data[0].b64_json)
    image_path = output_dir / f"iter_{iteration}.png"
    image_path.write_bytes(img_bytes)

    return {"iteration": iteration, "image_path": str(image_path)}
```

- [ ] **Step 4: Run — expect pass**

```bash
uv run pytest tests/test_nodes.py::test_generator_saves_png_and_increments_iteration -v
```

- [ ] **Step 5: Commit**

```bash
git add thumbnail_agent/nodes.py tests/test_nodes.py
git commit -m "feat: implement generator node (gpt-image-1, 1536x1024)"
```

---

## Task 7: `nodes.py` — `critic`

**Files:**
- Modify: `thumbnail_agent/nodes.py`
- Modify: `tests/test_nodes.py`

- [ ] **Step 1: Add failing test**

Append to `tests/test_nodes.py`:

```python
def test_critic_returns_rating_critique_and_appends_history(tmp_path):
    fake_png = tmp_path / "iter_1.png"
    fake_png.write_bytes(b"fakepng")

    mock_structured = MagicMock()
    mock_structured.invoke.return_value = MagicMock(rating=6, critique="Text too small.")

    mock_llm = MagicMock()
    mock_llm.with_structured_output.return_value = mock_structured

    with patch("thumbnail_agent.nodes.ChatOpenAI", return_value=mock_llm):
        from thumbnail_agent.nodes import critic, CritiqueOutput
        state = _base_state(
            topic="Python AI",
            current_prompt="Bold Python thumbnail.",
            image_path=str(fake_png),
            iteration=1,
        )
        result = critic(state)

    assert result["rating"] == 6
    assert result["critique"] == "Text too small."
    assert len(result["history"]) == 1
    entry = result["history"][0]
    assert entry["iteration"] == 1
    assert entry["rating"] == 6
    assert entry["prompt"] == "Bold Python thumbnail."
    assert entry["image_path"] == str(fake_png)
    mock_llm.with_structured_output.assert_called_once_with(CritiqueOutput)
```

- [ ] **Step 2: Run — expect NotImplementedError**

```bash
uv run pytest tests/test_nodes.py::test_critic_returns_rating_critique_and_appends_history -v
```

- [ ] **Step 3: Implement `critic` in `nodes.py`**

Replace the `critic` stub:

```python
def critic(state: ThumbnailState) -> dict:
    llm = ChatOpenAI(model="gpt-4o").with_structured_output(CritiqueOutput)
    img_b64 = base64.b64encode(Path(state["image_path"]).read_bytes()).decode()
    response = llm.invoke([
        SystemMessage(content=CRITIC_SYSTEM),
        HumanMessage(content=[
            {
                "type": "text",
                "text": f"Rate this YouTube thumbnail for the topic: {state['topic']}",
            },
            {
                "type": "image_url",
                "image_url": {"url": f"data:image/png;base64,{img_b64}"},
            },
        ]),
    ])
    entry = {
        "iteration": state["iteration"],
        "prompt": state["current_prompt"],
        "image_path": state["image_path"],
        "rating": response.rating,
        "critique": response.critique,
    }
    return {
        "rating": response.rating,
        "critique": response.critique,
        "history": [entry],
    }
```

- [ ] **Step 4: Run — expect pass**

```bash
uv run pytest tests/test_nodes.py::test_critic_returns_rating_critique_and_appends_history -v
```

- [ ] **Step 5: Commit**

```bash
git add thumbnail_agent/nodes.py tests/test_nodes.py
git commit -m "feat: implement critic node with GPT-4o vision and structured output"
```

---

## Task 8: `nodes.py` — `saver`

**Files:**
- Modify: `thumbnail_agent/nodes.py`
- Modify: `tests/test_nodes.py`

- [ ] **Step 1: Add failing test**

Append to `tests/test_nodes.py`:

```python
def test_saver_picks_best_rating_and_writes_final_and_report(tmp_path):
    iter1 = tmp_path / "iter_1.png"
    iter2 = tmp_path / "iter_2.png"
    iter1.write_bytes(b"img1")
    iter2.write_bytes(b"img2")

    history = [
        {
            "iteration": 1,
            "prompt": "First prompt",
            "image_path": str(iter1),
            "rating": 5,
            "critique": "Too cluttered.",
        },
        {
            "iteration": 2,
            "prompt": "Revised prompt",
            "image_path": str(iter2),
            "rating": 8,
            "critique": "Great clarity now.",
        },
    ]

    from thumbnail_agent.nodes import saver
    state = _base_state(
        topic="Python AI",
        output_dir=str(tmp_path),
        history=history,
    )
    saver(state)

    final = tmp_path / "final.png"
    assert final.exists()
    assert final.read_bytes() == b"img2"  # iter2 has rating 8

    report = tmp_path / "report.md"
    assert report.exists()
    content = report.read_text()
    assert "First prompt" in content
    assert "Revised prompt" in content
    assert "5/10" in content
    assert "8/10" in content
    assert "Too cluttered" in content
```

- [ ] **Step 2: Run — expect NotImplementedError**

```bash
uv run pytest tests/test_nodes.py::test_saver_picks_best_rating_and_writes_final_and_report -v
```

- [ ] **Step 3: Implement `saver` in `nodes.py`**

Replace the `saver` stub:

```python
def saver(state: ThumbnailState) -> dict:
    history = state["history"]
    best = max(history, key=lambda x: x["rating"])
    output_dir = Path(state["output_dir"])

    shutil.copy(best["image_path"], output_dir / "final.png")

    lines = [
        f"# Thumbnail Report: {state['topic']}\n\n",
        f"**Best score:** {best['rating']}/10  \n",
        f"**Total iterations:** {len(history)}\n\n",
        "## Summary\n\n",
        "| Iter | Score | Critique |\n",
        "|------|-------|----------|\n",
    ]
    for h in history:
        short = h["critique"][:120].replace("|", "\\|")
        lines.append(f"| {h['iteration']} | {h['rating']}/10 | {short} |\n")

    lines.append("\n## Full Iteration Details\n")
    for h in history:
        lines.append(f"\n### Iteration {h['iteration']} — Score {h['rating']}/10\n\n")
        lines.append(f"**Prompt:**\n\n{h['prompt']}\n\n")
        lines.append(f"**Critique:** {h['critique']}\n")

    (output_dir / "report.md").write_text("".join(lines), encoding="utf-8")
    return {}
```

- [ ] **Step 4: Run — expect pass**

```bash
uv run pytest tests/test_nodes.py::test_saver_picks_best_rating_and_writes_final_and_report -v
```

- [ ] **Step 5: Run full test suite**

```bash
uv run pytest tests/ -v
```

Expected: All tests pass.

- [ ] **Step 6: Commit**

```bash
git add thumbnail_agent/nodes.py tests/test_nodes.py
git commit -m "feat: implement saver node — final.png + report.md"
```

---

## Task 9: `graph.py`

**Files:**
- Create: `thumbnail_agent/graph.py`
- Create: `tests/test_graph.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_graph.py
from thumbnail_agent.graph import build_graph


def test_graph_compiles():
    graph = build_graph()
    assert graph is not None


def test_graph_has_all_five_nodes():
    graph = build_graph()
    node_names = set(graph.get_graph().nodes.keys())
    assert {"web_search", "prompt_writer", "generator", "critic", "saver"}.issubset(node_names)


def test_graph_has_conditional_edge_from_critic():
    graph = build_graph()
    edges = graph.get_graph().edges
    source_nodes = {e[0] for e in edges}
    assert "critic" in source_nodes
```

- [ ] **Step 2: Run — expect ImportError**

```bash
uv run pytest tests/test_graph.py -v
```

- [ ] **Step 3: Create `thumbnail_agent/graph.py`**

```python
from langgraph.graph import END, START, StateGraph

from .nodes import critic, generator, prompt_writer, saver, should_continue, web_search
from .state import ThumbnailState


def build_graph():
    builder = StateGraph(ThumbnailState)

    builder.add_node("web_search", web_search)
    builder.add_node("prompt_writer", prompt_writer)
    builder.add_node("generator", generator)
    builder.add_node("critic", critic)
    builder.add_node("saver", saver)

    builder.add_edge(START, "web_search")
    builder.add_edge("web_search", "prompt_writer")
    builder.add_edge("prompt_writer", "generator")
    builder.add_edge("generator", "critic")
    builder.add_conditional_edges(
        "critic",
        should_continue,
        {"prompt_writer": "prompt_writer", "saver": "saver"},
    )
    builder.add_edge("saver", END)

    return builder.compile()
```

- [ ] **Step 4: Run — expect 3 passed**

```bash
uv run pytest tests/test_graph.py -v
```

- [ ] **Step 5: Run full suite**

```bash
uv run pytest tests/ -v
```

Expected: All tests pass.

- [ ] **Step 6: Commit**

```bash
git add thumbnail_agent/graph.py tests/test_graph.py
git commit -m "feat: wire LangGraph state machine with conditional loop edge"
```

---

## Task 10: `main.py` + `make_diagram.py`

**Files:**
- Create: `thumbnail_agent/main.py`
- Create: `thumbnail_agent/make_diagram.py`

- [ ] **Step 1: Create `thumbnail_agent/main.py`**

```python
import argparse
from datetime import datetime
from pathlib import Path

from .graph import build_graph


def _slugify(text: str) -> str:
    return "".join(c if c.isalnum() else "_" for c in text.lower())[:40]


def run(topic: str, stream: bool, target_rating: int, max_iterations: int) -> None:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = str(Path("outputs") / f"{ts}_{_slugify(topic)}")

    initial_state = {
        "topic": topic,
        "search_summary": "",
        "current_prompt": "",
        "image_path": "",
        "rating": 0,
        "critique": "",
        "iteration": 0,
        "history": [],
        "target_rating": target_rating,
        "max_iterations": max_iterations,
        "output_dir": output_dir,
    }

    graph = build_graph()

    if stream:
        from rich.console import Console
        console = Console()
        for chunk in graph.stream(initial_state):
            node_name = next(iter(chunk))
            console.print(f"[bold green]→ {node_name}[/bold green]")
    else:
        graph.invoke(initial_state)

    print(f"\nDone. Output: {output_dir}/")


def main() -> None:
    parser = argparse.ArgumentParser(description="YouTube Thumbnail Designer Agent")
    parser.add_argument("topic", help="Video topic")
    parser.add_argument("--stream", action="store_true", help="Stream node updates live")
    parser.add_argument("--target-rating", type=int, default=8)
    parser.add_argument("--max-iterations", type=int, default=3)
    args = parser.parse_args()
    run(args.topic, args.stream, args.target_rating, args.max_iterations)


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Create `thumbnail_agent/make_diagram.py`**

```python
from pathlib import Path

from .graph import build_graph


def main() -> None:
    graph = build_graph()
    png_data = graph.get_graph().draw_mermaid_png()
    Path("graph.png").write_bytes(png_data)
    print("graph.png written")


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: Smoke test imports**

```bash
uv run python -c "from thumbnail_agent.main import run; print('main OK')"
uv run python -c "from thumbnail_agent.make_diagram import main; print('make_diagram OK')"
```

Expected: `main OK` and `make_diagram OK`

- [ ] **Step 4: Run full test suite**

```bash
uv run pytest tests/ -v
```

Expected: All tests pass.

- [ ] **Step 5: Commit**

```bash
git add thumbnail_agent/main.py thumbnail_agent/make_diagram.py
git commit -m "feat: add CLI entry point and diagram generator"
```

---

## Task 11: Generate `graph.png` + end-to-end run

- [ ] **Generate `graph.png`**

```bash
uv run python -m thumbnail_agent.make_diagram
```

Expected: `graph.png` written in project root.

- [ ] **Commit `graph.png`**

```bash
git add graph.png
git commit -m "chore: add LangGraph architecture diagram"
```

- [ ] **Run end-to-end**

```bash
uv run python -m thumbnail_agent.main "Why Python is the best language for AI" --stream
```

Expected: Node updates printed live, `outputs/<timestamp>/` created with `iter_1.png`, optionally `iter_2.png+`, `final.png`, `report.md`.

- [ ] **Commit sample run output for grading**

Temporarily un-gitignore one run folder by adding an exception to `.gitignore`:
```
# In .gitignore, add:
!outputs/20260524_*/
```

Then:
```bash
git add outputs/<your_run_folder>/
git commit -m "chore: add sample run output for grading (loop fired)"
```
