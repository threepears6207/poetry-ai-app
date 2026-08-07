from pathlib import Path


STATIC_DIR = Path(__file__).resolve().parent / "static"


def poem_cover_url(poem_id: str):
    """Return the first storyboard image when it has already been generated."""
    path = STATIC_DIR / "images" / "poems" / poem_id / "frame_0.jpg"
    return f"/static/images/poems/{poem_id}/frame_0.jpg" if path.exists() else None


def build_poem_card(poem, *, learned_state=None, extra=None):
    """Build the shared card contract used by search, recommendations and candidates."""
    poem_id = str(poem.get("poem_id") or poem.get("id") or "").strip()
    card = {
        "poem_id": poem_id,
        "id": poem_id,
        "title": poem.get("title", ""),
        "author": poem.get("author", ""),
        "dynasty": poem.get("dynasty", ""),
        "cover_url": poem.get("cover_url") or poem_cover_url(poem_id),
        "age_level": poem.get("age_level"),
        "difficulty": poem.get("difficulty"),
        "learned_state": learned_state if learned_state is not None else poem.get("learned_state"),
    }
    if extra:
        card.update(extra)
    return card
