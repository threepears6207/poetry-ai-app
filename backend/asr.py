from funasr import AutoModel
from fastapi import APIRouter
from pydantic import BaseModel
import base64, tempfile, os, re
from difflib import SequenceMatcher

router = APIRouter()
_model = None

def get_model():
    global _model
    if _model is None:
        _model = AutoModel(model="paraformer-zh", disable_update=True)
    return _model

class ASRRequest(BaseModel):
    audio_base64: str
    audio_format: str = "mp3"   # 前端录音格式，默认mp3

class ScoreRequest(BaseModel):
    audio_base64: str
    poem_content: str           # 完整诗文，如"鹅鹅鹅曲项向天歌白毛浮绿水红掌拨清波"
    audio_format: str = "mp3"

# ── 语音识别 ──────────────────────────────────────────────────────────────
@router.post("/asr")
def speech_to_text(req: ASRRequest):
    try:
        audio_bytes = base64.b64decode(req.audio_base64)
        suffix = f".{req.audio_format}"
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as f:
            f.write(audio_bytes)
            tmp_path = f.name
        result = get_model().generate(input=tmp_path)
        os.unlink(tmp_path)
        text = result[0]["text"] if result else ""
        return {"success": True, "text": text}
    except Exception as e:
        return {"success": False, "text": "", "error": str(e)}

# ── 跟读评分 ──────────────────────────────────────────────────────────────
@router.post("/asr/score")
def score_reading(req: ScoreRequest):
    try:
        # 第一步：识别录音
        audio_bytes = base64.b64decode(req.audio_base64)
        suffix = f".{req.audio_format}"
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as f:
            f.write(audio_bytes)
            tmp_path = f.name
        result = get_model().generate(input=tmp_path)
        os.unlink(tmp_path)
        recognized = result[0]["text"] if result else ""

        # 第二步：去标点空格，比较相似度
        clean = lambda s: re.sub(r'[\s，。！？、,\.!?]', '', s)
        orig = clean(req.poem_content)
        recog = clean(recognized)
        ratio = SequenceMatcher(None, orig, recog).ratio()
        score = int(ratio * 100)

        # 第三步：算星级和鼓励语
        if score >= 90:
            stars, passed, message = 3, True,  "太棒了！读得非常准确！🌟"
        elif score >= 70:
            stars, passed, message = 2, True,  "读得很好，再练一遍更完美！👍"
        elif score >= 50:
            stars, passed, message = 1, False, "不错哦，继续加油！💪"
        else:
            stars, passed, message = 0, False, "再来一次，你能行的！🎵"

        return {
            "success":    True,
            "score":      score,
            "stars":      stars,
            "passed":     passed,   # 前端拿这个去调 /consolidation/result
            "message":    message,
            "recognized": recognized,  # 调试用，可以看识别出了什么
        }
    except Exception as e:
        return {"success": False, "error": str(e)}