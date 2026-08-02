import asyncio
import base64
import hashlib
import json
import os
import re
import time
import uuid
from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Any
from urllib.parse import urlencode

import websocket
from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field


router = APIRouter()

VIVO_ASR_DOMAIN = "wss://api-ai.vivo.com.cn"
VIVO_ASR_PATH = "/asr/v2"
VIVO_ASR_ENGINE_ID = "shortasrinput"
VIVO_ASR_HOST = "api-ai.vivo.com.cn"
PCM_SAMPLE_RATE = 16000
PCM_SAMPLE_WIDTH = 2
PCM_CHANNELS = 1
PCM_FRAME_DURATION_MS = 40
PCM_FRAME_BYTES = (
    PCM_SAMPLE_RATE * PCM_SAMPLE_WIDTH * PCM_CHANNELS * PCM_FRAME_DURATION_MS // 1000
)
MAX_SHORT_AUDIO_SECONDS = 60
MAX_PCM_BYTES = PCM_SAMPLE_RATE * PCM_SAMPLE_WIDTH * PCM_CHANNELS * MAX_SHORT_AUDIO_SECONDS


class VivoASRError(RuntimeError):
    """vivo 实时短语音识别返回的可展示错误。"""

    def __init__(self, message: str, code: int | None = None):
        super().__init__(message)
        self.code = code


class ASRRequest(BaseModel):
    """一次性短语音识别请求：只接收 vivo 所需的原始 PCM。"""

    pcm_base64: str
    net_type: int = Field(1, ge=0, le=1, description="0 数据网络，1 Wi-Fi")
    user_id: str = "test_user"
    end_vad_time: int = Field(1400, ge=300, le=10000, description="静音判定时长，单位毫秒")


class ScoreRequest(ASRRequest):
    poem_content: str


class ASRStreamStart(BaseModel):
    """手机实时 PCM 会话建立报文。"""

    type: str = "start"
    net_type: int = Field(1, ge=0, le=1)
    user_id: str = "anonymous"
    end_vad_time: int = Field(1400, ge=300, le=10000)


@dataclass(frozen=True)
class VivoASRResult:
    text: str
    sid: str
    result_id: int | None


def clean_text(value: str) -> str:
    """去除标点、空格，只保留用于诗句对齐的内容。"""
    return re.sub(r'[\s，。！？、,\\.!?\'"；：""\'\'【】（）《》…—~`]', '', value or '')


def _build_user_id(user_id: str) -> str:
    """vivo 要求 32 位小写字母/数字；不向 vivo 发送原始儿童用户标识。"""
    raw = f"poetry-ai-app:asr:{str(user_id or 'anonymous').strip()}"
    return hashlib.md5(raw.encode("utf-8")).hexdigest()


def _decode_pcm(pcm_base64: str) -> bytes:
    value = str(pcm_base64 or "").strip()
    value = re.sub(r"^data:audio/[^;]+;base64,", "", value, flags=re.IGNORECASE)
    if not value:
        raise VivoASRError("pcm_base64 不能为空")
    try:
        pcm_bytes = base64.b64decode(value, validate=True)
    except Exception as error:
        raise VivoASRError("pcm_base64 不是合法的 Base64 数据") from error

    if not pcm_bytes:
        raise VivoASRError("PCM 音频不能为空")
    if len(pcm_bytes) % PCM_SAMPLE_WIDTH != 0:
        raise VivoASRError("PCM 音频不是 16bit 对齐数据")
    if len(pcm_bytes) > MAX_PCM_BYTES:
        raise VivoASRError("单轮语音不能超过 60 秒")
    return pcm_bytes


def _build_websocket_url(net_type: int, user_id: str) -> str:
    params = {
        "model": "unknown",
        "system_version": "unknown",
        "client_version": "1.0",
        "package": "poetry-ai-app",
        "sdk_version": "backend-1.0",
        "user_id": _build_user_id(user_id),
        "android_version": "unknown",
        "system_time": int(time.time() * 1000),
        "net_type": int(net_type),
        "engineid": VIVO_ASR_ENGINE_ID,
        "requestId": str(uuid.uuid4()),
    }
    return f"{VIVO_ASR_DOMAIN}{VIVO_ASR_PATH}?{urlencode(params)}"


def _build_started_packet(request_id: str, end_vad_time: int) -> dict[str, Any]:
    return {
        "type": "started",
        "request_id": request_id,
        "asr_info": {
            "end_vad_time": int(end_vad_time),
            "audio_type": "pcm",
            "chinese2digital": 0,
            "punctuation": 1,
        },
    }


def _with_vivo_no_proxy(existing_value: str) -> str:
    """在既有 NO_PROXY 配置中加入 vivo ASR 域名，不丢弃其他规则。"""
    hosts = [host.strip() for host in str(existing_value or "").split(",") if host.strip()]
    if not any(host.lower() == VIVO_ASR_HOST for host in hosts):
        hosts.append(VIVO_ASR_HOST)
    return ",".join(hosts)


def _ensure_vivo_no_proxy() -> None:
    """避免系统 HTTPS_PROXY 把 vivo WebSocket 转发到不可用代理。"""
    existing_value = os.getenv("NO_PROXY") or os.getenv("no_proxy", "")
    configured_value = _with_vivo_no_proxy(existing_value)
    os.environ["NO_PROXY"] = configured_value
    os.environ["no_proxy"] = configured_value


def _validate_pcm_stream_frame(pcm_frame: bytes, sent_pcm_bytes: int) -> int:
    """校验一帧实时 PCM，并返回累计音频字节数。"""
    if not pcm_frame:
        raise VivoASRError("实时 PCM 音频帧不能为空")
    if len(pcm_frame) % PCM_SAMPLE_WIDTH != 0:
        raise VivoASRError("实时 PCM 音频帧不是 16bit 对齐数据")
    total_bytes = sent_pcm_bytes + len(pcm_frame)
    if total_bytes > MAX_PCM_BYTES:
        raise VivoASRError("实时短语音单轮不能超过 60 秒", code=10008)
    return total_bytes


def _as_json_message(message: Any, stage: str) -> dict[str, Any]:
    if isinstance(message, bytes):
        message = message.decode("utf-8")
    try:
        payload = json.loads(message)
    except (TypeError, json.JSONDecodeError) as error:
        raise VivoASRError(f"vivo {stage}返回了无法解析的数据") from error
    if not isinstance(payload, dict):
        raise VivoASRError(f"vivo {stage}返回格式不正确")
    return payload


def _raise_if_vivo_error(payload: dict[str, Any]) -> None:
    code = int(payload.get("code", 0) or 0)
    if payload.get("action") == "error" or code not in {0}:
        message = str(payload.get("desc") or "vivo 语音识别失败")
        error_messages = {
            10000: "vivo 语音识别参数校验失败",
            10002: "vivo 识别引擎服务异常",
            10003: "vivo 获取中间识别结果失败",
            10004: "vivo 获取最终识别结果失败",
            10005: "vivo 解析识别数据异常",
            10006: "vivo 识别引擎内部错误",
            10007: "vivo 语义请求失败",
            10008: "vivo 音频超长",
        }
        raise VivoASRError(error_messages.get(code, message), code=code)


def recognize_pcm_with_vivo(request: ASRRequest) -> VivoASRResult:
    """将一轮 16k/16bit/单声道 PCM 发送给 vivo，并等待最终文本。"""
    app_key = os.getenv("VIVO_APP_KEY", "").strip()
    if not app_key:
        raise VivoASRError("后端缺少 VIVO_APP_KEY，无法调用 vivo 语音识别")

    pcm_bytes = _decode_pcm(request.pcm_base64)
    ws = None
    request_id = uuid.uuid4().hex
    latest_text = ""
    sid = ""
    latest_result_id: int | None = None

    try:
        _ensure_vivo_no_proxy()
        ws = websocket.create_connection(
            _build_websocket_url(request.net_type, request.user_id),
            header=[f"Authorization: Bearer {app_key}"],
            timeout=20,
        )
        ws.send(json.dumps(_build_started_packet(request_id, request.end_vad_time), ensure_ascii=False))
        for offset in range(0, len(pcm_bytes), PCM_FRAME_BYTES):
            ws.send_binary(pcm_bytes[offset: offset + PCM_FRAME_BYTES])
            if offset + PCM_FRAME_BYTES < len(pcm_bytes):
                time.sleep(PCM_FRAME_DURATION_MS / 1000)
        ws.send_binary(b"--end--")

        while True:
            payload = _as_json_message(ws.recv(), "识别")
            _raise_if_vivo_error(payload)
            if payload.get("action") == "started":
                sid = str(payload.get("sid") or sid)
                continue
            if payload.get("action") != "result" or payload.get("type") != "asr":
                continue

            data = payload.get("data") or {}
            if not isinstance(data, dict):
                continue
            sid = str(payload.get("sid") or sid)
            text = str(data.get("text") or "").strip()
            if text:
                latest_text = text
            result_id = data.get("result_id")
            if isinstance(result_id, int):
                latest_result_id = result_id

            if bool(data.get("is_last")):
                if not latest_text:
                    raise VivoASRError("vivo 未返回最终识别文本")
                return VivoASRResult(latest_text, sid, latest_result_id)
    except VivoASRError:
        raise
    except Exception as error:
        raise VivoASRError(f"vivo 语音识别连接异常：{error}") from error
    finally:
        if ws is not None:
            try:
                ws.send_binary(b"--close--")
            except Exception:
                pass
            try:
                ws.close()
            except Exception:
                pass


async def _send_stream_event(client: WebSocket, event: str, **data: Any) -> None:
    """向手机发送统一格式的实时 ASR 事件；断开后的发送失败可忽略。"""
    try:
        await client.send_json({"event": event, "provider": "vivo-short-asr", **data})
    except RuntimeError:
        pass


@router.websocket("/asr/stream")
async def stream_speech_to_text(client: WebSocket) -> None:
    """把手机持续上传的 PCM 帧转发给 vivo，并实时回传识别结果。"""
    await client.accept()
    vivo_ws = None
    receive_results_task: asyncio.Task[None] | None = None

    try:
        try:
            start_message = await asyncio.wait_for(client.receive_text(), timeout=10)
            start_data = json.loads(start_message)
            start = ASRStreamStart.model_validate(start_data)
        except (asyncio.TimeoutError, TypeError, json.JSONDecodeError, ValueError) as error:
            raise VivoASRError("实时识别连接的第一条消息必须是 start 配置") from error

        if start.type != "start":
            raise VivoASRError("实时识别连接的第一条消息 type 必须为 start")

        app_key = os.getenv("VIVO_APP_KEY", "").strip()
        if not app_key:
            raise VivoASRError("后端缺少 VIVO_APP_KEY，无法调用 vivo 语音识别")

        _ensure_vivo_no_proxy()
        request_id = uuid.uuid4().hex
        vivo_ws = await asyncio.to_thread(
            websocket.create_connection,
            _build_websocket_url(start.net_type, start.user_id),
            header=[f"Authorization: Bearer {app_key}"],
            timeout=20,
            enable_multithread=True,
        )
        await asyncio.to_thread(
            vivo_ws.send,
            json.dumps(_build_started_packet(request_id, start.end_vad_time), ensure_ascii=False),
        )

        result_finished = asyncio.Event()

        async def relay_vivo_results() -> None:
            try:
                while True:
                    payload = _as_json_message(await asyncio.to_thread(vivo_ws.recv), "实时识别")
                    _raise_if_vivo_error(payload)

                    if payload.get("action") == "started":
                        await _send_stream_event(client, "vivo_started", sid=str(payload.get("sid") or ""))
                        continue

                    if payload.get("action") != "result" or payload.get("type") != "asr":
                        continue

                    result_data = payload.get("data") or {}
                    if not isinstance(result_data, dict):
                        continue

                    text = str(result_data.get("text") or "").strip()
                    is_last = bool(result_data.get("is_last"))
                    await _send_stream_event(
                        client,
                        "final" if is_last else "partial",
                        text=text,
                        is_last=is_last,
                        sid=str(payload.get("sid") or ""),
                        result_id=result_data.get("result_id"),
                        reformation=result_data.get("reformation"),
                    )
                    if is_last:
                        return
            except VivoASRError as error:
                await _send_stream_event(client, "error", error=str(error), code=error.code)
            except Exception as error:
                await _send_stream_event(client, "error", error=f"vivo 实时识别连接异常：{error}")
            finally:
                result_finished.set()

        receive_results_task = asyncio.create_task(relay_vivo_results())
        await _send_stream_event(client, "ready", frame_bytes=PCM_FRAME_BYTES)

        sent_pcm_bytes = 0
        while True:
            message = await client.receive()
            if message["type"] == "websocket.disconnect":
                break

            pcm_frame = message.get("bytes")
            if pcm_frame is not None:
                sent_pcm_bytes = _validate_pcm_stream_frame(pcm_frame, sent_pcm_bytes)
                await asyncio.to_thread(vivo_ws.send_binary, pcm_frame)
                continue

            text_message = message.get("text")
            if text_message is None:
                raise VivoASRError("实时识别只接受二进制 PCM 帧或 end 控制消息")

            try:
                control = json.loads(text_message)
            except json.JSONDecodeError as error:
                raise VivoASRError("实时识别控制消息必须是 JSON") from error

            if control.get("type") == "end":
                await asyncio.to_thread(vivo_ws.send_binary, b"--end--")
                await asyncio.wait_for(result_finished.wait(), timeout=25)
                break
            if control.get("type") == "close":
                break
            raise VivoASRError("实时识别控制消息 type 仅支持 end 或 close")
    except WebSocketDisconnect:
        pass
    except VivoASRError as error:
        await _send_stream_event(client, "error", error=str(error), code=error.code)
    except asyncio.TimeoutError:
        await _send_stream_event(client, "error", error="等待 vivo 最终识别结果超时")
    except Exception as error:
        await _send_stream_event(client, "error", error=f"实时识别服务异常：{error}")
    finally:
        if receive_results_task is not None:
            receive_results_task.cancel()
            try:
                await receive_results_task
            except asyncio.CancelledError:
                pass
        if vivo_ws is not None:
            try:
                await asyncio.to_thread(vivo_ws.send_binary, b"--close--")
            except Exception:
                pass
            try:
                await asyncio.to_thread(vivo_ws.close)
            except Exception:
                pass


def calc_score(reference: str, hypothesis: str) -> int:
    """按原规则计算诗句文本完成度；本函数不再关心识别引擎。"""
    ref = clean_text(reference)
    hyp = clean_text(hypothesis)
    if not ref or not hyp:
        return 0

    hyp_chars = list(hyp)
    hit_count = 0
    for character in ref:
        if character in hyp_chars:
            hyp_chars.remove(character)
            hit_count += 1
    char_recall = hit_count / len(ref)
    seq_ratio = SequenceMatcher(None, ref, hyp).ratio()
    return int((char_recall * 0.6 + seq_ratio * 0.4) * 100)


def score_to_feedback(score: int) -> tuple[int, bool, str]:
    if score >= 90:
        return 3, True, "太棒了！读得非常准确！"
    if score >= 70:
        return 2, True, "读得很好，再练一遍更完美！"
    if score >= 50:
        return 1, False, "不错哦，继续加油！"
    return 0, False, "再来一次，你能行的！"


@router.post("/asr")
def speech_to_text(request: ASRRequest):
    """使用 vivo 实时短语音服务识别一段完整 PCM 音频。"""
    try:
        result = recognize_pcm_with_vivo(request)
        return {
            "success": True,
            "text": result.text,
            "sid": result.sid,
            "result_id": result.result_id,
            "provider": "vivo-short-asr",
        }
    except VivoASRError as error:
        return {
            "success": False,
            "text": "",
            "error": str(error),
            "code": error.code,
            "provider": "vivo-short-asr",
        }


@router.post("/asr/score")
def score_reading(request: ScoreRequest):
    """使用 vivo 识别朗读文本，再按原有文本规则计算完成度。"""
    current_line = clean_text(request.poem_content)
    if not current_line:
        raise HTTPException(status_code=400, detail="poem_content 不能为空")

    try:
        result = recognize_pcm_with_vivo(request)
        score = calc_score(current_line, result.text)
        stars, passed, feedback = score_to_feedback(score)
        return {
            "success": True,
            "recognized_text": result.text,
            "completion_score": score,
            "score": score,
            "stars": stars,
            "passed": passed,
            "feedback": feedback,
            "sid": result.sid,
            "result_id": result.result_id,
            "provider": "vivo-short-asr",
        }
    except VivoASRError as error:
        return {
            "success": False,
            "recognized_text": "",
            "completion_score": 0,
            "passed": False,
            "feedback": "暂时无法识别，请再试一次。",
            "error": str(error),
            "code": error.code,
            "provider": "vivo-short-asr",
        }
