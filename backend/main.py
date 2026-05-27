from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from fastapi.staticfiles import StaticFiles

load_dotenv()

app = FastAPI(title="诗芽小学堂App API")

STATIC_DIR = Path(__file__).parent / "static"
STATIC_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 导入各模块路由
from chat import router as chat_router
from poems import router as poems_router
from record import router as record_router
from recommend import router as recommend_router
from generate import router as generate_router
from tts import router as tts_router
from ocr import router as ocr_router

app.include_router(chat_router)
app.include_router(poems_router)
app.include_router(record_router)
app.include_router(recommend_router)
app.include_router(generate_router)
app.include_router(tts_router)
app.include_router(ocr_router)


@app.get("/")
def read_root():
    return {"message": "诗芽小学堂App API 正在运行", "status": "ok", "api_version": "v1.0"}


@app.get("/ping")
def ping():
    import os
    app_id = os.getenv("VIVO_APP_ID")
    has_key = bool(os.getenv("VIVO_APP_KEY"))
    return {"message": "pong", "vivo_app_id": app_id, "has_api_key": has_key}
