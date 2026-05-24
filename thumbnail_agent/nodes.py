import base64
import shutil
from pathlib import Path

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from openai import OpenAI
from pydantic import BaseModel

from .prompts import CRITIC_SYSTEM, PROMPT_WRITER_SYSTEM, STRATEGY_SYSTEM
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
    hooks = search_topic(f"{state['topic']} viral YouTube hooks most clicked")
    visuals = search_topic(f"{state['topic']} YouTube thumbnail visual trends")
    summary = f"HOOKS & ANGLES:\n{hooks}\n\nVISUAL TRENDS:\n{visuals}"
    return {"search_summary": summary}


def strategy(state: ThumbnailState) -> dict:
    llm = ChatOpenAI(model="gpt-4o")
    response = llm.invoke([
        SystemMessage(content=STRATEGY_SYSTEM),
        HumanMessage(content=f"Topic: {state['topic']}\n\nResearch:\n{state['search_summary']}"),
    ])
    return {"strategy": response.content}


def prompt_writer(state: ThumbnailState) -> dict:
    llm = ChatOpenAI(model="gpt-4o")
    user_content = f"Topic: {state['topic']}\n\nThumbnail Strategy:\n{state['strategy']}"
    history = state.get("history", [])
    if history:
        history_text = "\n\n".join(
            f"Iteration {h['iteration']} (score {h['rating']}/10):\n{h['critique']}"
            for h in history
        )
        user_content += (
            f"\n\nCritique history — address ALL issues from the latest entry:\n{history_text}"
        )
    elif state.get("critique"):
        user_content += f"\n\nPrevious critique (address every point):\n{state['critique']}"
    response = llm.invoke([
        SystemMessage(content=PROMPT_WRITER_SYSTEM),
        HumanMessage(content=user_content),
    ])
    return {"current_prompt": response.content}


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
