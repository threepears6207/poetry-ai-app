"""HTTP handoff for completing a confirmed terminal poem."""

from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel, Field

from poem_completion import PoemCompletionError, complete_poem_from_terminal_analysis


router = APIRouter()


class TerminalPoemRequest(BaseModel):
    title: str = ""
    author: str = ""
    dynasty: str = ""
    content: list[str] = Field(default_factory=list)
    translation: str = ""


class TerminalAnalysisRequest(BaseModel):
    content_type: Literal["poem_text", "scene"]
    poem: TerminalPoemRequest | None = None
    objects: list[str] = Field(default_factory=list)
    confidence: float = 0.0


@router.post("/poem/complete")
def complete_terminal_poem(request: TerminalAnalysisRequest):
    """Complete one terminal-confirmed poem without querying or writing the poem library."""
    if request.content_type != "poem_text":
        return {
            "success": False,
            "status": "not_poem",
            "message": "端侧识别为风景，请调用 /poems/candidates 获取候选古诗",
        }

    try:
        result = complete_poem_from_terminal_analysis(request.model_dump())
    except PoemCompletionError as error:
        return {
            "success": False,
            "status": "not_completed",
            "message": str(error),
        }

    return {
        "success": True,
        "status": result["status"],
        "poem": result["poem"],
    }
