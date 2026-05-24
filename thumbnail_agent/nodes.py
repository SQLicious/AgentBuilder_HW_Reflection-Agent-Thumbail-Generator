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
    raise NotImplementedError


def saver(state: ThumbnailState) -> dict:
    raise NotImplementedError
