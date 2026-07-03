import httpx

COINGECKO_TICKERS = "https://api.coingecko.com/api/v3/coins/ripple/tickers"


async def fetch_exchange_volumes() -> dict:
    async with httpx.AsyncClient(timeout=20.0) as client:
        all_tickers: list[dict] = []
        page = 1
        while page <= 5:
            response = await client.get(
                COINGECKO_TICKERS,
                params={"include_exchange_logo": "false", "page": page, "depth": "true"},
            )
            if response.status_code == 429:
                break
            response.raise_for_status()
            data = response.json()
            tickers = data.get("tickers", [])
            if not tickers:
                break
            all_tickers.extend(tickers)
            page += 1

    exchange_map: dict[str, dict] = {}
    for ticker in all_tickers:
        if ticker.get("target", "").upper() not in ("USDT", "USD", "USDC", "KRW", "BTC", "EUR"):
            continue

        name = ticker.get("market", {}).get("name", "Unknown")
        volume = ticker.get("converted_volume", {}).get("usd") or ticker.get("volume", 0) or 0

        if name not in exchange_map:
            exchange_map[name] = {
                "exchange": name,
                "volume_usd": 0.0,
                "pairs": [],
                "trust_score": ticker.get("trust_score"),
            }

        exchange_map[name]["volume_usd"] += float(volume)
        pair = f"{ticker.get('base', 'XRP')}/{ticker.get('target', '')}"
        if pair not in exchange_map[name]["pairs"]:
            exchange_map[name]["pairs"].append(pair)

    exchanges = sorted(exchange_map.values(), key=lambda x: x["volume_usd"], reverse=True)
    total_volume = sum(e["volume_usd"] for e in exchanges)

    for ex in exchanges:
        ex["volume_usd"] = round(ex["volume_usd"], 2)
        ex["share_pct"] = round((ex["volume_usd"] / total_volume * 100) if total_volume else 0, 2)

    return {
        "exchanges": exchanges,
        "total_volume_usd": round(total_volume, 2),
        "exchange_count": len(exchanges),
    }