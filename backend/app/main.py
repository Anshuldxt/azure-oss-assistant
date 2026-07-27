"""
OSS Assistant backend.

Endpoints:
  POST /api/ingest/zip         multipart-upload the daily report.zip
  POST /api/ingest/csv         multipart-upload a single CSV
  GET  /api/vendors            list configured vendor profiles
  GET  /api/stats              current index totals
  GET  /api/search?q=          NE name / alias autocomplete
  GET  /api/ne/{name}          full dashboard payload for one NE
  POST /api/reset              clear the in-memory index

Run with:  uvicorn app.main:app --reload --port 8000
"""

import shutil
import tempfile
import zipfile
from pathlib import Path

from fastapi import FastAPI, UploadFile, File, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .config import VENDOR_PROFILES
from .parsers import ingest_csv_path
from .store import store

app = FastAPI(title="OSS Assistant API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten this to a specific origin if you ever split frontend/backend again
    allow_methods=["*"],
    allow_headers=["*"],
)

# backend/app/main.py -> backend/app -> backend -> repo root -> frontend
FRONTEND_DIR = Path(__file__).resolve().parent.parent.parent / "frontend"


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/vendors")
def vendors():
    return [
        {"key": k, "label": v["label"], "configured": bool(v["datasets"])}
        for k, v in VENDOR_PROFILES.items()
    ]


@app.get("/api/stats")
def stats():
    return store.stats()


@app.post("/api/reset")
def reset():
    store.reset()
    return {"status": "ok"}


@app.post("/api/ingest/csv")
async def ingest_csv(file: UploadFile = File(...), vendor: str = Query("huawei")):
    if vendor not in VENDOR_PROFILES:
        raise HTTPException(400, f"unknown vendor '{vendor}'")
    suffix = Path(file.filename).suffix or ".csv"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = tmp.name
    try:
        result = ingest_csv_path(vendor, tmp_path, file.filename)
    finally:
        Path(tmp_path).unlink(missing_ok=True)
    return {"vendor": vendor, "results": [result], "stats": store.stats()}


@app.post("/api/ingest/zip")
async def ingest_zip(file: UploadFile = File(...), vendor: str = Query("huawei")):
    if vendor not in VENDOR_PROFILES:
        raise HTTPException(400, f"unknown vendor '{vendor}'")

    with tempfile.TemporaryDirectory() as tmp_dir:
        zip_path = Path(tmp_dir) / "upload.zip"
        with open(zip_path, "wb") as f:
            shutil.copyfileobj(file.file, f)

        results = []
        try:
            with zipfile.ZipFile(zip_path) as z:
                exts = (".csv", ".txt", ".xlsx", ".xls")
                csv_members = [m for m in z.infolist() if m.filename.lower().endswith(exts)]
                if not csv_members:
                    raise HTTPException(400, "zip contains no .csv/.txt/.xlsx files")
                for member in csv_members:
                    extracted_path = z.extract(member, path=tmp_dir)
                    result = ingest_csv_path(vendor, extracted_path, Path(member.filename).name)
                    results.append(result)
        except zipfile.BadZipFile:
            raise HTTPException(400, "uploaded file is not a valid .zip")

    return {"vendor": vendor, "results": results, "stats": store.stats()}


@app.get("/api/search")
def search(q: str = Query(..., min_length=1), limit: int = 12):
    ne_matches, alias_matches = store.search(q, limit=limit)
    return {"ne": ne_matches, "aliases": alias_matches}


@app.get("/api/ne/{name}")
def get_ne(name: str):
    rec = store.get_ne(name)
    if rec is None:
        raise HTTPException(404, f"no NE found matching '{name}'")
    resolved_name = store.resolve_name(name) or name

    controllers = set()
    for r in rec["gsm"]:
        if r.get("bsc"):
            controllers.add(f"BSC {r['bsc']}")
    for r in rec["umts"]:
        if r.get("rnc"):
            controllers.add(f"RNC {r['rnc']}")

    return {
        "name": resolved_name,
        "neReport": rec["neReport"],
        "controllers": sorted(controllers),
        "devip": rec["devip"],
        "vlan": rec["vlan"],
        "s1": rec["s1"],
        "gsm": rec["gsm"],
        "umts": rec["umts"],
        "lte": rec["lte"],
        "nr": rec["nr"],
        "counts": {
            "devip": len(rec["devip"]), "vlan": len(rec["vlan"]), "s1": len(rec["s1"]),
            "gsm": len(rec["gsm"]), "umts": len(rec["umts"]), "lte": len(rec["lte"]), "nr": len(rec["nr"]),
        },
    }


# Serve the frontend from the same container/process as the API.
# Must come last: routes registered above take priority over this
# catch-all mount, so /api/* keeps working normally.
if FRONTEND_DIR.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")
