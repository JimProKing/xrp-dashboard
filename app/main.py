import json
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.services.chart import VALID_INTERVALS, fetch_chart_data
from app.services.exchanges import fetch_exchange_volumes
from app.services.premium import fetch_premium_data
from app.services.xrpl import (
    fetch_account_transactions,
    fetch_burn_stats,
    fetch_rich_list,
)

BASE_DIR = Path(__file__).resolve().parent
HOST = os.environ.get("HOST", "0.0.0.0")
PORT = int(os.environ.get("PORT", "8000"))


@asynccontextmanager
async def lifespan(_: FastAPI):
    print(f"\n  XRP Dashboard running on {HOST}:{PORT}\n")
    yield


app = FastAPI(title="XRP On-Chain Dashboard", version="1.0.0", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=BASE_DIR / "templates")


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/api/richlist")
async def richlist(limit: int = Query(default=50, ge=1, le=200)):
    try:
        return {"accounts": await fetch_rich_list(limit)}
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@app.get("/api/burn")
async def burn():
    try:
        return await fetch_burn_stats()
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@app.get("/api/exchanges")
async def exchanges():
    try:
        return await fetch_exchange_volumes()
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@app.get("/api/chart/klines")
async def chart_klines(
    exchange: str = Query(default="binance", pattern="^(binance|upbit)$"),
    interval: str = Query(default="1h"),
    limit: int | None = Query(default=None, ge=10, le=1000),
):
    if interval not in VALID_INTERVALS:
        raise HTTPException(status_code=400, detail=f"지원 interval: {', '.join(VALID_INTERVALS)}")
    try:
        return await fetch_chart_data(exchange, interval, limit)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@app.get("/api/premium")
async def premium():
    try:
        return await fetch_premium_data()
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@app.get("/api/transactions")
async def transactions(
    address: str = Query(..., min_length=25, max_length=64),
    limit: int = Query(default=20, ge=1, le=100),
    marker: str | None = None,
):
    try:
        parsed_marker = json.loads(marker) if marker else None
        return await fetch_account_transactions(address, limit, parsed_marker)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc