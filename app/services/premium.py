import httpx

UPBIT_TICKER = "https://api.upbit.com/v1/ticker"
BITHUMB_TICKER = "https://api.bithumb.com/public/ticker/XRP_KRW"
FX_RATE = "https://api.exchangerate-api.com/v4/latest/USD"

GLOBAL_SOURCES = [
    {"id": "kraken", "name": "Kraken", "url": "https://api.kraken.com/0/public/Ticker?pair=XRPUSD"},
    {"id": "coinbase", "name": "Coinbase", "url": "https://api.coinbase.com/v2/prices/XRP-USD/spot"},
    {"id": "okx", "name": "OKX", "url": "https://www.okx.com/api/v5/market/ticker?instId=XRP-USDT"},
    {"id": "bybit", "name": "Bybit", "url": "https://api.bybit.com/v5/market/tickers?category=spot&symbol=XRPUSDT"},
    {"id": "binance", "name": "Binance", "url": "https://api.binance.com/api/v3/ticker/price?symbol=XRPUSDT"},
]


async def _fetch_usd_krw(client: httpx.AsyncClient) -> float:
    response = await client.get(FX_RATE)
    response.raise_for_status()
    return float(response.json()["rates"]["KRW"])


async def _fetch_upbit_price(client: httpx.AsyncClient) -> dict:
    response = await client.get(UPBIT_TICKER, params={"markets": "KRW-XRP"})
    response.raise_for_status()
    data = response.json()[0]
    return {
        "exchange": "Upbit",
        "price_krw": data["trade_price"],
        "volume_24h": data["acc_trade_volume_24h"],
        "change_rate": data["signed_change_rate"] * 100,
    }


async def _fetch_bithumb_price(client: httpx.AsyncClient) -> dict | None:
    try:
        response = await client.get(BITHUMB_TICKER)
        response.raise_for_status()
        data = response.json()["data"]
        return {
            "exchange": "Bithumb",
            "price_krw": float(data["closing_price"]),
            "volume_24h": float(data["acc_trade_value_24H"]) / float(data["closing_price"]),
            "change_rate": float(data["fluctate_rate_24H"]),
        }
    except Exception:
        return None


async def _fetch_global_price(client: httpx.AsyncClient, source: dict) -> dict | None:
    try:
        response = await client.get(source["url"])
        response.raise_for_status()
        data = response.json()

        price_usd = None
        if source["id"] == "binance":
            price_usd = float(data["price"])
        elif source["id"] == "coinbase":
            price_usd = float(data["data"]["amount"])
        elif source["id"] == "kraken":
            pair = list(data["result"].keys())[0]
            price_usd = float(data["result"][pair]["c"][0])
        elif source["id"] == "okx":
            price_usd = float(data["data"][0]["last"])
        elif source["id"] == "bybit":
            price_usd = float(data["result"]["list"][0]["lastPrice"])

        if price_usd:
            return {"exchange": source["name"], "price_usd": price_usd}
    except Exception:
        pass
    return None


def calc_premium(price_krw: float, global_usd: float, usd_krw: float) -> dict:
    fair_krw = global_usd * usd_krw
    premium_pct = ((price_krw - fair_krw) / fair_krw) * 100 if fair_krw else 0
    return {
        "price_krw": price_krw,
        "fair_price_krw": round(fair_krw, 5),
        "premium_pct": round(premium_pct, 3),
        "premium_krw": round(price_krw - fair_krw, 4),
    }


async def fetch_premium_data() -> dict:
    async with httpx.AsyncClient(timeout=15.0) as client:
        usd_krw = await _fetch_usd_krw(client)
        upbit = await _fetch_upbit_price(client)
        bithumb = await _fetch_bithumb_price(client)

        global_prices = []
        for source in GLOBAL_SOURCES:
            price = await _fetch_global_price(client, source)
            if price:
                global_prices.append(price)

    if not global_prices:
        raise RuntimeError("글로벌 거래소 시세를 가져올 수 없습니다.")

    avg_global_usd = sum(p["price_usd"] for p in global_prices) / len(global_prices)

    upbit_premium = calc_premium(upbit["price_krw"], avg_global_usd, usd_krw)

    comparisons = []
    for gp in global_prices:
        premium = calc_premium(upbit["price_krw"], gp["price_usd"], usd_krw)
        comparisons.append(
            {
                "reference_exchange": gp["exchange"],
                "reference_price_usd": gp["price_usd"],
                "reference_price_krw": round(gp["price_usd"] * usd_krw, 5),
                **premium,
            }
        )

    comparisons.sort(key=lambda x: abs(x["premium_pct"]), reverse=True)

    korean_exchanges = [
        {
            "exchange": upbit["exchange"],
            "price_krw": upbit["price_krw"],
            "volume_24h": upbit["volume_24h"],
            "change_rate": upbit["change_rate"],
            "premium_vs_global": upbit_premium,
        }
    ]
    if bithumb:
        bithumb_premium = calc_premium(bithumb["price_krw"], avg_global_usd, usd_krw)
        korean_exchanges.append(
            {
                "exchange": bithumb["exchange"],
                "price_krw": bithumb["price_krw"],
                "volume_24h": bithumb["volume_24h"],
                "change_rate": bithumb["change_rate"],
                "premium_vs_global": bithumb_premium,
            }
        )

    return {
        "base_exchange": "Upbit",
        "usd_krw_rate": usd_krw,
        "global_avg_usd": round(avg_global_usd, 6),
        "global_prices": global_prices,
        "upbit": upbit,
        "upbit_premium": upbit_premium,
        "korean_exchanges": korean_exchanges,
        "comparisons": comparisons,
    }