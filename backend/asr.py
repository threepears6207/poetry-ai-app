import base64
import os
import re
import tempfile
from difflib import SequenceMatcher
from typing import List, Union

from fastapi import APIRouter
from funasr import AutoModel
from pydantic import BaseModel

router = APIRouter()

# ── 启动时立即加载模型，避免第一次请求时的冷启动延迟 ──────────────────────────
print("正在加载 FunASR 模型，请稍候...")
_model = AutoModel(model="paraformer-zh", disable_update=True)
print("FunASR 模型加载完成 ✓")


# ── 请求模型 ──────────────────────────────────────────────────────────────────

class ASRRequest(BaseModel):
    audio_base64: str
    audio_format: str = "mp3"


class ScoreRequest(BaseModel):
    audio_base64: str
    poem_content: Union[List[str], str]  # 兼容数组["鹅鹅鹅","曲项向天歌"]和字符串"鹅鹅鹅曲项向天歌"两种格式
    audio_format: str = "mp3"


# ── 工具函数 ──────────────────────────────────────────────────────────────────

def clean_text(s: str) -> str:
    """去除所有标点、空格，只保留汉字和字母数字"""
    return re.sub(r'[\s，。！？、,\.!?\'"；：""''【】（）《》…—~`]', '', s)


def recognize_audio(audio_base64: str, audio_format: str) -> str:
    """识别音频，返回识别文本"""
    audio_bytes = base64.b64decode(audio_base64)
    print(f"[ASR调试] 收到音频，格式: {audio_format}，大小: {len(audio_bytes)} 字节")

    suffix = f".{audio_format}"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as f:
        f.write(audio_bytes)
        tmp_path = f.name
    try:
        result = _model.generate(input=tmp_path)
        text = result[0]["text"] if result else ""
        print(f"[ASR调试] FunASR 原始识别结果: 「{text}」")
    finally:
        os.unlink(tmp_path)
    return text


def calc_score(reference: str, hypothesis: str) -> int:
    """
    计算两段文本的相似度分数（0-100）。

    古诗每句只有4到7个字，纯靠 SequenceMatcher 的 ratio 在短文本上区分度很差
    （字数差1个就会大幅跳动，容易卡在固定区间）。
    这里改成两种指标加权：
      1. 字符级召回率：参考文本里的字，识别结果命中了多少个（顺序无关，容忍轻微错位）
      2. 序列相似度：SequenceMatcher 的 ratio（兼顾顺序和连续性）
    取两者的平均值，让短句评分更稳定、更有区分度。
    """
    ref = clean_text(reference)
    hyp = clean_text(hypothesis)

    print(f"[评分调试] 参考文本: 「{ref}」（{len(ref)}字）  识别文本: 「{hyp}」（{len(hyp)}字）")

    if not ref:
        return 0
    if not hyp:
        print("[评分调试] 识别结果为空，判定0分")
        return 0

    # 指标一：字符级命中率（计算参考文本中每个字是否出现在识别结果里，重复字分别计数）
    hyp_chars = list(hyp)
    hit_count = 0
    for ch in ref:
        if ch in hyp_chars:
            hyp_chars.remove(ch)  # 命中后移除，避免重复计数
            hit_count += 1
    char_recall = hit_count / len(ref)

    # 指标二：序列相似度（兼顾顺序）
    seq_ratio = SequenceMatcher(None, ref, hyp).ratio()

    # 两者加权平均，字符命中率权重更高（对短句更宽容，避免顺序轻微错位导致分数骤降）
    final_ratio = char_recall * 0.6 + seq_ratio * 0.4
    score = int(final_ratio * 100)

    print(f"[评分调试] 字符命中率: {char_recall:.2f}  序列相似度: {seq_ratio:.2f}  最终得分: {score}")

    return score


def score_to_feedback(score: int):
    """根据分数返回星级、是否通过、鼓励语"""
    if score >= 90:
        return 3, True, "太棒了！读得非常准确！🌟"
    elif score >= 70:
        return 2, True, "读得很好，再练一遍更完美！👍"
    elif score >= 50:
        return 1, False, "不错哦，继续加油！💪"
    else:
        return 0, False, "再来一次，你能行的！🎵"


# ── 语音识别接口 ──────────────────────────────────────────────────────────────

@router.post("/asr")
def speech_to_text(req: ASRRequest):
    """
    语音转文字。

    请求示例：
    {
      "audio_base64": "...",
      "audio_format": "mp3"
    }
    """
    try:
        text = recognize_audio(req.audio_base64, req.audio_format)
        return {"success": True, "text": text}
    except Exception as e:
        return {"success": False, "text": "", "error": str(e)}


# ── 跟读评分接口 ──────────────────────────────────────────────────────────────

@router.post("/asr/score")
def score_reading(req: ScoreRequest):
    """
    跟读评分。支持逐句评分 + 整体评分。

    请求示例：
    {
      "audio_base64": "...",
      "audio_format": "mp3",
      "poem_content": ["鹅鹅鹅", "曲项向天歌", "白毛浮绿水", "红掌拨清波"]
    }

    返回示例：
    {
      "success": true,
      "score": 85,
      "stars": 2,
      "passed": true,
      "message": "读得很好，再练一遍更完美！👍",
      "recognized": "鹅鹅鹅曲项向天歌...",
      "sentence_scores": [
        {"line": "鹅鹅鹅", "score": 100},
        {"line": "曲项向天歌", "score": 80},
        ...
      ]
    }
    """
    try:
        # ── poem_content 兼容字符串和数组两种格式 ─────────────────────────────
        if isinstance(req.poem_content, str):
            # 旧格式：整首诗拼成一个字符串，无法逐句评分，作为单句处理
            lines = [req.poem_content]
        else:
            lines = req.poem_content

        # ── 识别录音 ──────────────────────────────────────────────────────────
        recognized = recognize_audio(req.audio_base64, req.audio_format)
        recognized_clean = clean_text(recognized)

        # ── 整首诗标准文本 ─────────────────────────────────────────────────────
        full_poem = "".join(lines)
        overall_score = calc_score(full_poem, recognized_clean)

        # ── 逐句评分 ──────────────────────────────────────────────────────────
        sentence_scores = []
        remaining = recognized_clean
        for line in lines:
            line_clean = clean_text(line)
            line_len = len(line_clean)
            # 取对应长度的片段
            chunk = remaining[:line_len]
            remaining = remaining[line_len:]
            s = calc_score(line_clean, chunk)
            sentence_scores.append({"line": line, "score": s})

        stars, passed, message = score_to_feedback(overall_score)

        return {
            "success":         True,
            "score":           overall_score,
            "stars":           stars,
            "passed":          passed,
            "message":         message,
            "recognized":      recognized,
            "sentence_scores": sentence_scores,
        }

    except Exception as e:
        return {"success": False, "error": str(e)}
