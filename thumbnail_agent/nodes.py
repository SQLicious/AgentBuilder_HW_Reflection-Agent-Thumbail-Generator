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
