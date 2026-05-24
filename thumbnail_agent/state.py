import operator
from typing import Annotated

from typing_extensions import TypedDict


class ThumbnailState(TypedDict):
    topic: str
    search_summary: str
    strategy: str
    current_prompt: str
    image_path: str
    rating: int
    critique: str
    iteration: int
    history: Annotated[list[dict], operator.add]
    target_rating: int
    max_iterations: int
    output_dir: str
