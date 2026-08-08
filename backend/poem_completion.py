"""云端古诗诗库记录补全。

本模块负责把端侧 ``poem_text`` 结果交给云端模型，补齐与 ``poems``
表一致的诗词字段。正式诗库检索、去重与写入仍由诗库模块负责。
"""

import json
import os
import re
import uuid
from typing import Any

import requests


VIVO_CHAT_COMPLETIONS_URL = "https://api-ai.vivo.com.cn/v1/chat/completions"
VIVO_POEM_COMPLETION_MODEL = os.getenv(
    "VIVO_POEM_COMPLETION_MODEL", "Volc-DeepSeek-V3.2"
)
REQUEST_TIMEOUT_SECONDS = 30
MAX_ATTEMPTS = 2

AGE_RANGES = {
    "age_3_4": "3-4岁",
    "age_5_7": "5-7岁",
}
KNOWLEDGE_TAGS = {
    "价值启蒙", "动态意象", "夸张修辞", "季节意象", "情感理解", "情绪感知",
    "想象能力", "意象理解", "文化常识", "方位认知", "比喻感知", "比喻理解",
    "生活常识", "生活画面", "生活观察", "画面理解", "简单哲理", "背诵积累",
    "自然意象", "自然认知", "节奏感知", "观察能力",
}
REQUIRED_FIELDS = {
    "title", "author", "dynasty", "content", "translation", "tags", "age_level",
    "age_range", "difficulty", "theme_tags", "knowledge_tags",
}


SYSTEM_COMPLETION_PROMPT = """你是儿童古诗诗库记录补全助手。只输出一个符合要求的 JSON 对象，不要输出解释、Markdown、status 字段或任何其他文字。"""

USER_COMPLETION_PROMPT_TEMPLATE = """【端侧已确认、必须原样保留的古诗内容】

诗名：{terminal_title}
作者：{terminal_author}
朝代：{terminal_dynasty}
正文：
{terminal_content_lines}

上方内容来自端侧识别。title、author、dynasty 中非空的值必须逐字保留。
如果正文已有两句及以上，则每一句及其顺序必须逐字保留，绝不能替换、删除、增加或改成另一首诗。
端侧为空或标记为“未识别”的字段，才允许根据其余线索补全。
你必须围绕上方这首诗完成记录，禁止输出另一首古诗。

【任务】

补全一条可直接写入儿童诗库的完整古诗记录。只输出以下 JSON：

{{
  "title": "诗名",
  "author": "作者",
  "dynasty": "唐",
  "content": ["原诗第一句", "原诗第二句"],
  "translation": "按原诗顺序完整解释全诗含义的一段儿童白话译文",
  "tags": ["标签一", "标签二"],
  "age_level": "age_3_4",
  "age_range": "3-4岁",
  "difficulty": 1,
  "theme_tags": ["主题一", "主题二"],
  "knowledge_tags": ["背诵积累", "画面理解"]
}}

【字段规则】

1. 所有字段必须输出且不能为空。
2. dynasty 只能写“唐、宋、元、明、清、汉、晋、隋、南北朝”等标准名称，不写“唐朝”“清朝”。
3. content 必须是数组，每项只放一句原诗正文，按原诗标点分句，不带句末标点；不得混入拼音、题目、作者、朝代、译文、脚注或提示词。
4. translation 必须是一个字符串，按原诗顺序，用一段连贯、儿童能懂的白话完整解释全诗；不得照抄原诗，不得添加“译文：”“用儿童能懂的白话解释”等前缀。
5. tags 输出 2 到 5 项，使用原子化的核心名词、动作或概念标签，提取全诗最重要的景物、行为、季节、节日、事件或情感线索。
   标签应使用现代汉语，具体、简洁、方便检索；不限制固定字数。以下二字和四字标签仅用于展示写法，不构成长度限制。
   人物主语不是必要信息时，不要加入。例如“孩子钓鱼”写“钓鱼”，“儿童划船”写“划船”，“草丛垂钓”写“垂钓”或“钓鱼”。
   不得直接照抄古文词组、诗句片段或人物称呼，例如不得写“蓬头稚子”“草映身”“小娃”“撑小艇”“偷采白莲”等。
   可以使用“月亮、莲花、钓鱼、划船、鸟鸣、风雨、思乡、童趣”等简洁标签；需要表达较完整含义时，也可以使用“自然观察、珍惜粮食、朋友送别、春天景象”等现代汉语标签。
   不要罗列所有细节，只输出最能代表整首诗的 2 到 5 项；不得臆造诗中没有的季节、节日、人物关系或场景。
6. theme_tags 输出 2 到 4 项。
   必须先直接复用 tags 中的 1 到 2 项，再补充 1 到 2 项与全诗相关的情感、意义、整体氛围或儿童学习方向标签。
   补充标签使用简洁现代汉语，不限制固定字数。二字标签可以是“童趣、专心、自然、观察、思乡、送别、劳动、珍惜”等；需要表达较完整主题时，也可以是“快乐童趣、自然观察、珍惜粮食、朋友送别、情感表达、生活观察、春天景象、专心做事”等。
   例如：tags 为“钓鱼、招手、鱼儿”时，theme_tags 可以为“钓鱼、鱼儿、童趣、专心”；tags 为“春天、鸟鸣、风雨”时，theme_tags 可以为“春天、鸟鸣、自然、观察”。
   不得使用“古诗、诗词、优美、传统文化、好诗”等空泛词；不得照抄原诗完整句子或片段。
7. age_level 只能是 age_3_4 或 age_5_7；age_range 必须分别对应 3-4岁 或 5-7岁；difficulty 只能是 1、2、3。
8. knowledge_tags 输出 1 到 3 项，且只能从以下词中选择：“价值启蒙、动态意象、夸张修辞、季节意象、情感理解、情绪感知、想象能力、意象理解、文化常识、方位认知、比喻感知、比喻理解、生活常识、生活画面、生活观察、画面理解、简单哲理、背诵积累、自然意象、自然认知、节奏感知、观察能力”。
【输出前自检】

输出前再次核对：JSON 中的 title、author、dynasty，以及端侧已有的每一句正文，必须与最上方“端侧已确认内容”完全一致。"""


class PoemCompletionError(RuntimeError):
    """云端补全不可用或返回记录不合格。"""


def _strip_think_tags(text: str) -> str:
    text = re.sub(r"<think[^>]*>.*?</think[^>]*>", "", text, flags=re.DOTALL)
    text = re.sub(r"^.*?</think[^>]*>\s*", "", text, flags=re.DOTALL)
    return text.strip()


def _extract_json_object(text: str) -> dict[str, Any]:
    cleaned = _strip_think_tags(str(text or ""))
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start < 0 or end < start:
        raise PoemCompletionError("云端补全未返回 JSON 对象")
    try:
        data = json.loads(cleaned[start : end + 1])
    except json.JSONDecodeError as error:
        raise PoemCompletionError("云端补全 JSON 解析失败") from error
    if not isinstance(data, dict):
        raise PoemCompletionError("云端补全结果必须是 JSON 对象")
    return data


def _normalize_dynasty(value: Any) -> str:
    dynasty = str(value or "").strip()
    aliases = {
        "汉朝": "汉", "汉代": "汉", "晋朝": "晋", "晋代": "晋",
        "隋朝": "隋", "隋代": "隋", "唐朝": "唐", "唐代": "唐",
        "宋朝": "宋", "宋代": "宋", "元朝": "元", "元代": "元",
        "明朝": "明", "明代": "明", "清朝": "清", "清代": "清",
    }
    return aliases.get(dynasty, dynasty)


def _clean_poem_line(value: Any) -> str:
    return re.sub(r"\s+", "", str(value or "")).rstrip("，。！？；、")


def _contains_non_poem_content(value: str) -> bool:
    return bool(
        re.search(r"[A-Za-z0-9]", value)
        or any(marker in value for marker in ("白话", "译文", "解释", "儿童能懂"))
    )


def _clean_string_list(value: Any, field_name: str) -> list[str]:
    if not isinstance(value, list):
        raise PoemCompletionError(f"云端补全 {field_name} 必须是数组")
    values = [str(item or "").strip() for item in value]
    if not values or any(not item for item in values):
        raise PoemCompletionError(f"云端补全 {field_name} 不能包含空值")
    if len(values) != len(set(values)):
        raise PoemCompletionError(f"云端补全 {field_name} 不能重复")
    return values


def _source_poem(terminal_analysis: dict[str, Any]) -> dict[str, Any]:
    poem = terminal_analysis.get("poem")
    return poem if isinstance(poem, dict) else {}


def _source_content(poem: dict[str, Any]) -> list[str]:
    raw_content = poem.get("content")
    if not isinstance(raw_content, list):
        return []
    return [line for line in (_clean_poem_line(item) for item in raw_content) if line]


def _has_cloud_completion_clues(terminal_analysis: dict[str, Any]) -> bool:
    if terminal_analysis.get("content_type") != "poem_text":
        return False
    poem = _source_poem(terminal_analysis)
    has_title_or_author = bool(str(poem.get("title") or "").strip()) or bool(
        str(poem.get("author") or "").strip()
    )
    return has_title_or_author or len(_source_content(poem)) >= 2


def _assert_terminal_fields_are_preserved(
    completed: dict[str, Any], terminal_analysis: dict[str, Any]
) -> None:
    source = _source_poem(terminal_analysis)
    for field_name in ("title", "author"):
        expected = str(source.get(field_name) or "").strip()
        if expected and completed[field_name] != expected:
            raise PoemCompletionError(f"云端补全改写了端侧已确认的 {field_name}")

    source_dynasty = _normalize_dynasty(source.get("dynasty"))
    if source_dynasty and completed["dynasty"] != source_dynasty:
        raise PoemCompletionError("云端补全改写了端侧已确认的 dynasty")

    source_content = _source_content(source)
    if len(source_content) >= 2 and completed["content"] != source_content:
        raise PoemCompletionError("云端补全改写了端侧已确认的 content")


def _validate_model_result(
    data: dict[str, Any], terminal_analysis: dict[str, Any]
) -> dict[str, Any]:
    unknown_fields = set(data) - REQUIRED_FIELDS
    missing_fields = REQUIRED_FIELDS - set(data)
    if unknown_fields or missing_fields:
        raise PoemCompletionError("云端补全字段必须与正式诗库记录完全一致")

    title = str(data.get("title") or "").strip()
    author = str(data.get("author") or "").strip()
    dynasty = _normalize_dynasty(data.get("dynasty"))
    translation = str(data.get("translation") or "").strip()
    if not all((title, author, dynasty, translation)):
        raise PoemCompletionError("云端补全的古诗核心字段不能为空")

    raw_content = data.get("content")
    if not isinstance(raw_content, list):
        raise PoemCompletionError("云端补全 content 必须是数组")
    content = [_clean_poem_line(line) for line in raw_content]
    content = [line for line in content if line]
    if len(content) < 2:
        raise PoemCompletionError("云端补全至少需要两句古诗正文")
    if any(_contains_non_poem_content(line) for line in content):
        raise PoemCompletionError("云端补全正文混入非诗文内容")

    normalized_content = "".join(content)
    normalized_translation = re.sub(r"[\s，。！？；、]", "", translation)
    if _contains_non_poem_content(translation) or normalized_content in normalized_translation:
        raise PoemCompletionError("云端补全译文不符合要求")

    tags = _clean_string_list(data.get("tags"), "tags")
    theme_tags = _clean_string_list(data.get("theme_tags"), "theme_tags")
    knowledge_tags = _clean_string_list(data.get("knowledge_tags"), "knowledge_tags")
    if not 2 <= len(tags) <= 5:
        raise PoemCompletionError("云端补全 tags 数量必须为 2 到 5 项")
    if not 2 <= len(theme_tags) <= 4:
        raise PoemCompletionError("云端补全 theme_tags 数量必须为 2 到 4 项")
    if not 1 <= len(knowledge_tags) <= 3 or not set(knowledge_tags) <= KNOWLEDGE_TAGS:
        raise PoemCompletionError("云端补全 knowledge_tags 不符合诗库词表")

    age_level = str(data.get("age_level") or "").strip()
    age_range = str(data.get("age_range") or "").strip()
    difficulty = data.get("difficulty")
    if AGE_RANGES.get(age_level) != age_range:
        raise PoemCompletionError("云端补全 age_level 与 age_range 不对应")
    if isinstance(difficulty, bool) or difficulty not in (1, 2, 3):
        raise PoemCompletionError("云端补全 difficulty 只能是 1、2、3")

    completed = {
        "title": title,
        "author": author,
        "dynasty": dynasty,
        "content": content,
        "translation": translation,
        "tags": tags,
        "age_level": age_level,
        "age_range": age_range,
        "difficulty": difficulty,
        "theme_tags": theme_tags,
        "knowledge_tags": knowledge_tags,
    }
    _assert_terminal_fields_are_preserved(completed, terminal_analysis)
    return completed


def build_completion_prompt(terminal_analysis: dict[str, Any]) -> str:
    """构造以端侧已确认诗文开头的用户消息。"""
    if not isinstance(terminal_analysis, dict):
        raise PoemCompletionError("端侧识别结果必须是 JSON 对象")
    if not _has_cloud_completion_clues(terminal_analysis):
        raise PoemCompletionError("端侧结果不具备云端古诗补全条件")

    poem = _source_poem(terminal_analysis)
    source_content = _source_content(poem)
    terminal_content_lines = (
        "\n".join(f"{index}. {line}" for index, line in enumerate(source_content, 1))
        if source_content
        else "（未识别）"
    )

    return USER_COMPLETION_PROMPT_TEMPLATE.format(
        terminal_title=str(poem.get("title") or "").strip() or "（未识别）",
        terminal_author=str(poem.get("author") or "").strip() or "（未识别）",
        terminal_dynasty=_normalize_dynasty(poem.get("dynasty")) or "（未识别）",
        terminal_content_lines=terminal_content_lines,
    )


def build_completion_messages(terminal_analysis: dict[str, Any]) -> list[dict[str, str]]:
    """使用与 generate.py 一致的 system + user 消息结构。"""
    return [
        {"role": "system", "content": SYSTEM_COMPLETION_PROMPT},
        {"role": "user", "content": build_completion_prompt(terminal_analysis)},
    ]


def complete_poem_from_terminal_analysis(
    terminal_analysis: dict[str, Any],
) -> dict[str, Any]:
    """调用 vivo 云端模型，返回校验后的完整诗库记录草稿。"""
    app_key = os.getenv("VIVO_APP_KEY")
    if not app_key:
        raise PoemCompletionError("未配置 VIVO_APP_KEY，无法调用云端古诗补全")

    payload = {
        "requestId": str(uuid.uuid4()),
        "model": VIVO_POEM_COMPLETION_MODEL,
        "messages": build_completion_messages(terminal_analysis),
    }
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {app_key}",
    }

    last_error: Exception | None = None
    for _ in range(MAX_ATTEMPTS):
        try:
            response = requests.post(
                VIVO_CHAT_COMPLETIONS_URL,
                json=payload,
                headers=headers,
                timeout=REQUEST_TIMEOUT_SECONDS,
            )
            response.raise_for_status()
            result = response.json()
            content = result["choices"][0]["message"]["content"]
            poem = _validate_model_result(
                _extract_json_object(content), terminal_analysis
            )
            return {"status": "complete", "poem": poem}
        except (requests.RequestException, KeyError, TypeError, ValueError, PoemCompletionError) as error:
            last_error = error

    raise PoemCompletionError(f"云端古诗补全失败：{last_error}")
