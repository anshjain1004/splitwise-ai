from __future__ import annotations
import os
from pathlib import Path
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from .ai import extract_bill
from .models import SplitRequest
from .splitter import calculate_split

load_dotenv()

app = FastAPI(title="SplitWise AI", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

STATIC = Path(__file__).parent / "static"
ALLOWED = {"image/jpeg", "image/png", "image/webp", "image/heic", "image/heif"}

# Serve the frontend assets (CSS + JavaScript + images).
app.mount("/static", StaticFiles(directory=STATIC), name="static")


@app.get("/")
def index():
    return FileResponse(STATIC / "index.html")


@app.post("/api/extract")
async def extract(files: list[UploadFile] = File(...)):
    if not 1 <= len(files) <= 2:
        raise HTTPException(400, "Upload one or two bill images.")

    images = []
    for f in files:
        if f.content_type not in ALLOWED:
            raise HTTPException(400, f"Unsupported image type: {f.content_type}")
        data = await f.read()
        if len(data) > 15 * 1024 * 1024:
            raise HTTPException(400, "Each image must be under 15 MB.")
        images.append((data, f.content_type))

    try:
        bill = extract_bill(images)
        return bill.model_dump()
    except Exception as exc:
        raise HTTPException(500, str(exc))


@app.post("/api/split")
def split(req: SplitRequest):
    try:
        return calculate_split(req).model_dump()
    except Exception as exc:
        raise HTTPException(400, str(exc))
