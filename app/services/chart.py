import httpx

BINANCE_KLINES = "https://api.binance.com/api/v3/klines"
BINANCE_TICKER = "https://api.binance.com/api/v3/ticker/24hr"
UPBIT_CANDLES_MIN = "https://api.upbit.com/v1/candles/minutes"
UPBIT_CANDLES_DAY = "https://api.upbit.com/v1/candles/days"
UPBIT_TICKER = "https://api.upbit.com/v1/ticker"

VALID_INTERVALS = ("1m", "5m", "15m", "1h", "4h", "1d")
CHART_LIMITS = {"1m": 480, "5m": 480, "15m": 480, "1h": 720, "4h": 540, "1d": 365}

UPBIT_UNIT_MAP = {"1m": 1, "5m": 5, "15m": 15, "1h": 60, "4h": 240}


def _to_candle(time_sec: int, o: float, h: float, l: float, c: float, v: float) -> dict:
    return {"time": time_sec, "open": o, "high": h, "low": l, "close": c, "volume": v}


async def _fetch_upbit_paginated(
    client: httpx.AsyncClient, market: str, interval: str, target: int
) -> list[dict]:
    collected: list[dict] = []
    to_time: str | None = None

    while len(collected) < target:
        count = min(200, target - len(collected))
        if interval == "1d":
            url = UPBIT_CANDLES_DAY
            params: dict = {"market": market, "count": count}
        else:
            unit = UPBIT_UNIT_MAP[interval]
            url = f"{UPBIT_CANDLES_MIN}/{unit}"
            params = {"market": market, "count": count}
        if to_time:
            params["to"] = to_time

        response = await client.get(url, params=params)
        response.raise_for_status()
        batch = response.json()
        if not batch:
            break
        collected.extend(batch)
        to_time = batch[-1]["candle_date_time_utc"]
        if len(batch) < count:
            break

    seen: set[int] = set()
    unique = []
    for c in collected:
        if c["timestamp"] not in seen:
            seen.add(c["timestamp"])
            unique.append(c)
    unique.sort(key=lambda x: x["timestamp"])
    return unique[-target:]


async def _fetch_binance_paginated(
    client: httpx.AsyncClient, interval: str, target: int
) -> list[list]:
    collected: list[list] = []
    end_time: int | None = None

    while len(collected) < target:
        limit = min(1000, target - len(collected))
        params: dict = {"symbol": "XRPUSDT", "interval": interval, "limit": limit}
        if end_time is not None:
            params["endTime"] = end_time

        response = await client.get(BINANCE_KLINES, params=params)
        response.raise_for_status()
        batch = response.json()
        if not batch:
            break
        collected = batch + collected
        end_time = int(batch[0][0]) - 1
        if len(batch) < limit:
            break

    return collected[-target:]


async def fetch_binance_klines(interval: str, limit: int | None = None) -> dict:
    target = limit or CHART_LIMITS.get(interval, 300)
    async with httpx.AsyncClient(timeout=30.0) as client:
        raw, ticker_res = await _fetch_binance_paginated(client, interval, target), await client.get(
            BINANCE_TICKER, params={"symbol": "XRPUSDT"}
        )
        ticker_res.raise_for_status()
        ticker = ticker_res.json()

    candles = [
        _to_candle(int(k[0]) // 1000, float(k[1]), float(k[2]), float(k[3]), float(k[4]), float(k[5]))
        for k in raw
    ]

    return {
        "exchange": "binance",
        "symbol": "XRP/USDT",
        "interval": interval,
        "count": len(candles),
        "candles": candles,
        "ticker": {
            "price": float(ticker["lastPrice"]),
            "change_pct": float(ticker["priceChangePercent"]),
            "high": float(ticker["highPrice"]),
            "low": float(ticker["lowPrice"]),
            "volume": float(ticker["volume"]),
        },
        "ws_stream": f"xrpusdt@kline_{interval}",
    }


async def fetch_upbit_klines(interval: str, limit: int | None = None) -> dict:
    target = limit or CHART_LIMITS.get(interval, 200)
    async with httpx.AsyncClient(timeout=30.0) as client:
        raw = await _fetch_upbit_paginated(client, "KRW-XRP", interval, target)
        ticker_res = await client.get(UPBIT_TICKER, params={"markets": "KRW-XRP"})
        ticker_res.raise_for_status()
        ticker = ticker_res.json()[0]

    candles = [
        _to_candle(
            c["timestamp"] // 1000,
            float(c["opening_price"]),
            float(c["high_price"]),
            float(c["low_price"]),
            float(c["trade_price"]),
            float(c["candle_acc_trade_volume"]),
        )
        for c in raw
    ]

    return {
        "exchange": "upbit",
        "symbol": "KRW-XRP",
        "interval": interval,
        "count": len(candles),
        "candles": candles,
        "ticker": {
            "price": float(ticker["trade_price"]),
            "change_pct": float(ticker["signed_change_rate"]) * 100,
            "high": float(ticker["high_price"]),
            "low": float(ticker["low_price"]),
            "volume": float(ticker["acc_trade_volume_24h"]),
        },
        "ws_unit": UPBIT_UNIT_MAP.get(interval, 0),
    }


async def fetch_chart_data(exchange: str, interval: str, limit: int | None = None) -> dict:
    if interval not in VALID_INTERVALS:
        raise ValueError(f"지원하지 않는 interval: {interval}")

    if exchange == "binance":
        return await fetch_binance_klines(interval, limit)
    if exchange == "upbit":
        return await fetch_upbit_klines(interval, limit)
    raise ValueError(f"지원하지 않는 exchange: {exchange}")