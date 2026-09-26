import asyncio
import base64
import json
import os
import re
import time
import uuid
from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Any
from urllib.parse import urlparse

import websocket
from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field


router = APIRouter()

DASHSCOPE_ASR_WEBSOCKET_URL = os.getenv(
    "DASHSCOPE_ASR_WEBSOCKET_URL",
    "wss://dashscope.aliyuncs.com/api-ws/v1/inference",
).strip()
DASHSCOPE_ASR_MODEL = os.getenv("DASHSCOPE_ASR_MODEL", "fun-asr-realtime").strip()
DASHSCOPE_ASR_PROVIDER = "dashscope-fun-asr-realtime"
PCM_SAMPLE_RATE = 16000
PCM_SAMPLE_WIDTH = 2
PCM_CHANNELS = 1
PCM_FRAME_DURATION_MS = 40
PCM_FRAME_BYTES = (
    PCM_SAMPLE_RATE * PCM_SAMPLE_WIDTH * PCM_CHANNELS * PCM_FRAME_DURATION_MS // 1000
)
MAX_SHORT_AUDIO_SECONDS = 60
MAX_PCM_BYTES = PCM_SAMPLE_RATE * PCM_SAMPLE_WIDTH * PCM_CHANNELS * MAX_SHORT_AUDIO_SECONDS


class DashScopeASRError(RuntimeError):
    """百炼实时语音识别返回的可展示错误。"""

    def __init__(self, message: str, code: str | int | None = None):
        super().__init__(message)
        self.code = code


class ASRRequest(BaseModel):
    """一次性短语音识别请求：接收 16k/16bit/单声道 PCM。"""

    pcm_base64: str
    # 下面两个字段为兼容现有前端请求而保留，百炼鉴权不使用它们。
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
class DashScopeASRResult:
    text: str
    sid: str
    result_id: int | None


def clean_text(value: str) -> str:
    """去除标点、空格，只保留用于诗句对齐的内容。"""
    return re.sub(r'[\s，。！？、,\\.!?\'"；：“”‘’【】（）《》…—~`]', '', value or '')


def _decode_pcm(pcm_base64: str) -> bytes:
    value = str(pcm_base64 or "").strip()
    value = re.sub(r"^data:audio/[^;]+;base64,", "", value, flags=re.IGNORECASE)
    if not value:
        raise DashScopeASRError("pcm_base64 不能为空")
    try:
        pcm_bytes = base64.b64decode(value, validate=True)
    except Exception as error:
        raise DashScopeASRError("pcm_base64 不是合法的 Base64 数据") from error

    if not pcm_bytes:
        raise DashScopeASRError("PCM 音频不能为空")
    if len(pcm_bytes) % PCM_SAMPLE_WIDTH != 0:
        raise DashScopeASRError("PCM 音频不是 16bit 对齐数据")
    if len(pcm_bytes) > MAX_PCM_BYTES:
        raise DashScopeASRError("单轮语音不能超过 60 秒")
    return pcm_bytes


def _validate_pcm_stream_frame(pcm_frame: bytes, sent_pcm_bytes: int) -> int:
    """校验一帧实时 PCM，并返回累计音频字节数。"""
    if not pcm_frame:
        raise DashScopeASRError("实时 PCM 音频帧不能为空")
    if len(pcm_frame) % PCM_SAMPLE_WIDTH != 0:
        raise DashScopeASRError("实时 PCM 音频帧不是 16bit 对齐数据")
    total_bytes = sent_pcm_bytes + len(pcm_frame)
    if total_bytes > MAX_PCM_BYTES:
        raise DashScopeASRError("实时短语音单轮不能超过 60 秒", code="AUDIO_TOO_LONG")
    return total_bytes


def _build_run_task_packet(task_id: str, end_vad_time: int) -> dict[str, Any]:
    """构造百炼实时 ASR 的 run-task 指令。"""
    max_sentence_silence = max(200, min(int(end_vad_time), 6000))
    return {
        "header": {
            "action": "run-task",
            "task_id": task_id,
            "streaming": "duplex",
        },
        "payload": {
            "task_group": "audio",
            "task": "asr",
            "function": "recognition",
            "model": DASHSCOPE_ASR_MODEL,
            "parameters": {
                "format": "pcm",
                "sample_rate": PCM_SAMPLE_RATE,
                "language_hints": ["zh"],
                "semantic_punctuation_enabled": False,
                "max_sentence_silence": max_sentence_silence,
            },
            "input": {},
        },
    }


def _build_finish_task_packet(task_id: str) -> dict[str, Any]:
    return {
        "header": {
            "action": "finish-task",
            "task_id": task_id,
            "streaming": "duplex",
        },
        "payload": {"input": {}},
    }


def _as_json_message(message: Any, stage: str) -> dict[str, Any]:
    if isinstance(message, bytes):
        message = message.decode("utf-8")
    try:
        payload = json.loads(message)
    except (TypeError, json.JSONDecodeError) as error:
        raise DashScopeASRError(f"百炼{stage}返回了无法解析的数据") from error
    if not isinstance(payload, dict):
        raise DashScopeASRError(f"百炼{stage}返回格式不正确")
    return payload


def _event_name(payload: dict[str, Any]) -> str:
    header = payload.get("header") or {}
    return str(header.get("event") or "") if isinstance(header, dict) else ""


def _raise_if_task_failed(payload: dict[str, Any]) -> None:
    if _event_name(payload) != "task-failed":
        return
    header = payload.get("header") or {}
    code = header.get("error_code")
    message = str(header.get("error_message") or "百炼语音识别失败")
    raise DashScopeASRError(f"百炼语音识别失败：{message}", code=code)


def _sentence_from_result(payload: dict[str, Any]) -> dict[str, Any] | None:
    if _event_name(payload) != "result-generated":
        return None
    body = payload.get("payload") or {}
    output = body.get("output") or {}
    sentence = output.get("sentence") or {}
    if not isinstance(sentence, dict) or sentence.get("heartbeat") is True:
        return None
    return sentence


def _with_no_proxy(existing_value: str, host: str) -> str:
    hosts = [item.strip() for item in str(existing_value or "").split(",") if item.strip()]
    if host and not any(item.lower() == host.lower() for item in hosts):
        hosts.append(host)
    return ",".join(hosts)


def _ensure_dashscope_no_proxy() -> None:
    """避免系统代理把百炼 WebSocket 转发到不支持长连接的代理。"""
    host = urlparse(DASHSCOPE_ASR_WEBSOCKET_URL).hostname or "dashscope.aliyuncs.com"
    existing_value = os.getenv("NO_PROXY") or os.getenv("no_proxy", "")
    configured_value = _with_no_proxy(existing_value, host)
    os.environ["NO_PROXY"] = configured_value
    os.environ["no_proxy"] = configured_value


def _open_dashscope_socket(api_key: str):
    _ensure_dashscope_no_proxy()
    return websocket.create_connection(
        DASHSCOPE_ASR_WEBSOCKET_URL,
        header=[
            f"Authorization: Bearer {api_key}",
            "User-Agent: poetry-ai-app/1.0",
        ],
        timeout=20,
        enable_multithread=True,
    )


def _send_json(ws: Any, payload: dict[str, Any]) -> None:
    ws.send(json.dumps(payload, ensure_ascii=False))


def _wait_for_task_started(ws: Any, task_id: str) -> None:
    while True:
        payload = _as_json_message(ws.recv(), "任务启动")
        _raise_if_task_failed(payload)
        event = _event_name(payload)
        if event == "task-started":
            response_task_id = str((payload.get("header") or {}).get("task_id") or "")
            if response_task_id and response_task_id != task_id:
                raise DashScopeASRError("百炼语音识别返回了不匹配的任务 ID")
            return
        if event == "task-finished":
            raise DashScopeASRError("百炼语音识别任务未启动就已结束")


def recognize_pcm_with_dashscope(request: ASRRequest) -> DashScopeASRResult:
    """将一轮 16k PCM 发送给百炼 Fun-ASR，并等待完整最终文本。"""
    api_key = os.getenv("DASHSCOPE_API_KEY", "").strip()
    if not api_key:
        raise DashScopeASRError("后端缺少 DASHSCOPE_API_KEY，无法调用百炼语音识别")

    pcm_bytes = _decode_pcm(request.pcm_base64)
    ws = None
    task_id = uuid.uuid4().hex
    final_sentences: dict[int, str] = {}
    latest_text = ""
    latest_result_id: int | None = None

    try:
        ws = _open_dashscope_socket(api_key)
        _send_json(ws, _build_run_task_packet(task_id, request.end_vad_time))
        _wait_for_task_started(ws, task_id)

        for offset in range(0, len(pcm_bytes), PCM_FRAME_BYTES):
            ws.send_binary(pcm_bytes[offset: offset + PCM_FRAME_BYTES])
            if offset + PCM_FRAME_BYTES < len(pcm_bytes):
                time.sleep(PCM_FRAME_DURATION_MS / 1000)
        _send_json(ws, _build_finish_task_packet(task_id))

        while True:
            payload = _as_json_message(ws.recv(), "识别")
            _raise_if_task_failed(payload)
            event = _event_name(payload)
            sentence = _sentence_from_result(payload)
            if sentence is not None:
                text = str(sentence.get("text") or "").strip()
                sentence_id = sentence.get("sentence_id")
                if isinstance(sentence_id, int):
                    latest_result_id = sentence_id
                if text:
                    latest_text = text
                    if bool(sentence.get("sentence_end")):
                        key = sentence_id if isinstance(sentence_id, int) else len(final_sentences) + 1
                        final_sentences[key] = text
            if event == "task-finished":
                final_text = "".join(final_sentences[key] for key in sorted(final_sentences))
                final_text = final_text or latest_text
                if not final_text:
                    raise DashScopeASRError("百炼未返回最终识别文本")
                return DashScopeASRResult(final_text, task_id, latest_result_id)
    except DashScopeASRError:
        raise
    except Exception as error:
        raise DashScopeASRError(f"百炼语音识别连接异常：{error}") from error
    finally:
        if ws is not None:
            try:
                ws.close()
            except Exception:
                pass


async def _send_stream_event(client: WebSocket, event: str, **data: Any) -> None:
    """向手机发送统一格式的实时 ASR 事件；断开后的发送失败可忽略。"""
    try:
        await client.send_json({"event": event, "provider": DASHSCOPE_ASR_PROVIDER, **data})
    except RuntimeError:
        pass


@router.websocket("/asr/stream")
async def stream_speech_to_text(client: WebSocket) -> None:
    """把手机持续上传的 PCM 帧转发给百炼，并实时回传识别结果。"""
    await client.accept()
    dashscope_ws = None
    receive_results_task: asyncio.Task[None] | None = None

    try:
        try:
            start_message = await asyncio.wait_for(client.receive_text(), timeout=10)
            start_data = json.loads(start_message)
            start = ASRStreamStart.model_validate(start_data)
        except (asyncio.TimeoutError, TypeError, json.JSONDecodeError, ValueError) as error:
            raise DashScopeASRError("实时识别连接的第一条消息必须是 start 配置") from error

        if start.type != "start":
            raise DashScopeASRError("实时识别连接的第一条消息 type 必须为 start")

        api_key = os.getenv("DASHSCOPE_API_KEY", "").strip()
        if not api_key:
            raise DashScopeASRError("后端缺少 DASHSCOPE_API_KEY，无法调用百炼语音识别")

        task_id = uuid.uuid4().hex
        dashscope_ws = await asyncio.to_thread(_open_dashscope_socket, api_key)
        await asyncio.to_thread(
            _send_json,
            dashscope_ws,
            _build_run_task_packet(task_id, start.end_vad_time),
        )
        await asyncio.to_thread(_wait_for_task_started, dashscope_ws, task_id)

        result_finished = asyncio.Event()
        final_sentences: dict[int, str] = {}
        latest_text = ""
        latest_result_id: int | None = None

        async def relay_dashscope_results() -> None:
            nonlocal latest_text, latest_result_id
            try:
                while True:
                    payload = _as_json_message(
                        await asyncio.to_thread(dashscope_ws.recv), "实时识别"
                    )
                    _raise_if_task_failed(payload)
                    event = _event_name(payload)
                    sentence = _sentence_from_result(payload)
                    if sentence is not None:
                        text = str(sentence.get("text") or "").strip()
                        sentence_id = sentence.get("sentence_id")
                        if isinstance(sentence_id, int):
                            latest_result_id = sentence_id
                        if text:
                            latest_text = text
                            if bool(sentence.get("sentence_end")):
                                key = sentence_id if isinstance(sentence_id, int) else len(final_sentences) + 1
                                final_sentences[key] = text
                            committed = "".join(
                                final_sentences[key] for key in sorted(final_sentences)
                            )
                            displayed_text = committed
                            if not bool(sentence.get("sentence_end")):
                                displayed_text += text
                            await _send_stream_event(
                                client,
                                "partial",
                                text=displayed_text,
                                is_last=False,
                                sid=task_id,
                                result_id=latest_result_id,
                            )

                    if event == "task-finished":
                        final_text = "".join(
                            final_sentences[key] for key in sorted(final_sentences)
                        )
                        final_text = final_text or latest_text
                        if not final_text:
                            raise DashScopeASRError("百炼未返回最终识别文本")
                        await _send_stream_event(
                            client,
                            "final",
                            text=final_text,
                            is_last=True,
                            sid=task_id,
                            result_id=latest_result_id,
                        )
                        return
            except DashScopeASRError as error:
                await _send_stream_event(client, "error", error=str(error), code=error.code)
            except Exception as error:
                await _send_stream_event(client, "error", error=f"百炼实时识别连接异常：{error}")
            finally:
                result_finished.set()

        receive_results_task = asyncio.create_task(relay_dashscope_results())
        await _send_stream_event(client, "ready", frame_bytes=PCM_FRAME_BYTES)

        sent_pcm_bytes = 0
        while True:
            message = await client.receive()
            if message["type"] == "websocket.disconnect":
                break

            pcm_frame = message.get("bytes")
            if pcm_frame is not None:
                sent_pcm_bytes = _validate_pcm_stream_frame(pcm_frame, sent_pcm_bytes)
                await asyncio.to_thread(dashscope_ws.send_binary, pcm_frame)
                continue

            text_message = message.get("text")
            if text_message is None:
                raise DashScopeASRError("实时识别只接受二进制 PCM 帧或 end 控制消息")

            try:
                control = json.loads(text_message)
            except json.JSONDecodeError as error:
                raise DashScopeASRError("实时识别控制消息必须是 JSON") from error

            if control.get("type") == "end":
                await asyncio.to_thread(
                    _send_json,
                    dashscope_ws,
                    _build_finish_task_packet(task_id),
                )
                await asyncio.wait_for(result_finished.wait(), timeout=25)
                break
            if control.get("type") == "close":
                break
            raise DashScopeASRError("实时识别控制消息 type 仅支持 end 或 close")
    except WebSocketDisconnect:
        pass
    except DashScopeASRError as error:
        await _send_stream_event(client, "error", error=str(error), code=error.code)
    except asyncio.TimeoutError:
        await _send_stream_event(client, "error", error="等待百炼最终识别结果超时")
    except Exception as error:
        await _send_stream_event(client, "error", error=f"实时识别服务异常：{error}")
    finally:
        if receive_results_task is not None:
            receive_results_task.cancel()
            try:
                await receive_results_task
            except asyncio.CancelledError:
                pass
        if dashscope_ws is not None:
            try:
                await asyncio.to_thread(dashscope_ws.close)
            except Exception:
                pass


def calc_score(reference: str, hypothesis: str) -> int:
    """按原规则计算诗句文本完成度；本函数不关心识别引擎。"""
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
    """使用百炼 Fun-ASR 识别一段完整 PCM 音频。"""
    try:
        result = recognize_pcm_with_dashscope(request)
        return {
            "success": True,
            "text": result.text,
            "sid": result.sid,
            "result_id": result.result_id,
            "provider": DASHSCOPE_ASR_PROVIDER,
        }
    except DashScopeASRError as error:
        return {
            "success": False,
            "text": "",
            "error": str(error),
            "code": error.code,
            "provider": DASHSCOPE_ASR_PROVIDER,
        }


@router.post("/asr/score")
def score_reading(request: ScoreRequest):
    """使用百炼识别朗读文本，再按原有文本规则计算完成度。"""
    current_line = clean_text(request.poem_content)
    if not current_line:
        raise HTTPException(status_code=400, detail="poem_content 不能为空")

    try:
        result = recognize_pcm_with_dashscope(request)
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
            "provider": DASHSCOPE_ASR_PROVIDER,
        }
    except DashScopeASRError as error:
        return {
            "success": False,
            "recognized_text": "",
            "completion_score": 0,
            "passed": False,
            "feedback": "暂时无法识别，请再试一次。",
            "error": str(error),
            "code": error.code,
            "provider": DASHSCOPE_ASR_PROVIDER,
        }
