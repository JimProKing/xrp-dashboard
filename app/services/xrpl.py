import os

import httpx

XRP_SCAN = "https://api.xrpscan.com/api/v1"
INITIAL_SUPPLY_XRP = 100_000_000_000
DROPS_PER_XRP = 1_000_000

BLOCKED_XRPL_HOSTS = ("xrplcluster.com",)
DEFAULT_XRPL_RPC_URLS = [
    "https://xrpl.ws",
    "https://s1.ripple.com:51234",
    "https://s2.ripple.com:51234",
]


def _sanitize_rpc_urls(urls: list[str]) -> list[str]:
    clean = []
    for url in urls:
        lowered = url.lower()
        if any(host in lowered for host in BLOCKED_XRPL_HOSTS):
            continue
        clean.append(url)
    return clean or DEFAULT_XRPL_RPC_URLS


XRPL_RPC_URLS = _sanitize_rpc_urls(
    [
        url.strip()
        for url in os.environ.get("XRPL_RPC_URL", "").split(",")
        if url.strip()
    ]
    or DEFAULT_XRPL_RPC_URLS
)
XRPL_RETRY_CODES = {402, 403, 429, 500, 502, 503, 504}


async def _xrpl_rpc(client: httpx.AsyncClient, method: str, params: list) -> dict:
    body = {"method": method, "params": params}
    errors: list[str] = []

    for url in XRPL_RPC_URLS:
        try:
            response = await client.post(url, json=body)
            if response.status_code in XRPL_RETRY_CODES:
                errors.append(f"{url}: HTTP {response.status_code}")
                continue
            response.raise_for_status()
            data = response.json()
            result = data.get("result", {})
            if result.get("status") == "error":
                errors.append(f"{url}: {result.get('error_message', result.get('error'))}")
                continue
            return result
        except httpx.HTTPStatusError as exc:
            errors.append(f"{url}: HTTP {exc.response.status_code}")
        except httpx.RequestError as exc:
            errors.append(f"{url}: {exc}")

    raise RuntimeError("XRPL RPC 요청 실패 — " + " | ".join(errors))


async def fetch_rich_list(limit: int = 100) -> list[dict]:
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(f"{XRP_SCAN}/balances")
        response.raise_for_status()
        data = response.json()

    accounts = sorted(data, key=lambda x: x.get("supply", x.get("balance", 0)), reverse=True)

    result = []
    for i, item in enumerate(accounts[:limit]):
        supply_drops = item.get("supply", item.get("balance", 0))
        balance_drops = item.get("balance", 0)
        name_info = item.get("name") or {}
        result.append(
            {
                "rank": i + 1,
                "account": item["account"],
                "balance_xrp": balance_drops / DROPS_PER_XRP,
                "supply_xrp": supply_drops / DROPS_PER_XRP,
                "escrow_xrp": item.get("escrow", 0) / DROPS_PER_XRP,
                "label": name_info.get("name") if isinstance(name_info, dict) else None,
                "domain": name_info.get("domain") if isinstance(name_info, dict) else None,
            }
        )
    return result


async def fetch_burn_stats() -> dict:
    async with httpx.AsyncClient(timeout=15.0) as client:
        result = await _xrpl_rpc(
            client,
            "ledger",
            [{"ledger_index": "validated", "transactions": False, "expand": False}],
        )

    ledger = result.get("ledger", result)
    total_coins_drops = int(ledger["total_coins"])
    current_supply = total_coins_drops / DROPS_PER_XRP
    burned = INITIAL_SUPPLY_XRP - current_supply
    burn_pct = (burned / INITIAL_SUPPLY_XRP) * 100

    return {
        "initial_supply": INITIAL_SUPPLY_XRP,
        "current_supply": current_supply,
        "burned": burned,
        "burn_percentage": burn_pct,
        "ledger_index": int(ledger["ledger_index"]),
        "updated_at": ledger.get("close_time_iso"),
    }


async def fetch_account_transactions(
    address: str, limit: int = 20, marker: dict | None = None
) -> dict:
    params: dict = {"account": address, "limit": limit, "binary": False}
    if marker:
        params["marker"] = marker

    async with httpx.AsyncClient(timeout=20.0) as client:
        result = await _xrpl_rpc(client, "account_tx", [params])

    transactions = []

    for entry in result.get("transactions", []):
        tx = entry.get("tx", {})
        meta = entry.get("meta", {})
        amount = tx.get("Amount")
        amount_xrp = None
        if isinstance(amount, str) and amount.isdigit():
            amount_xrp = int(amount) / DROPS_PER_XRP

        transactions.append(
            {
                "hash": tx.get("hash"),
                "type": tx.get("TransactionType"),
                "account": tx.get("Account"),
                "destination": tx.get("Destination"),
                "amount_xrp": amount_xrp,
                "fee_xrp": int(tx.get("Fee", 0)) / DROPS_PER_XRP,
                "ledger_index": tx.get("ledger_index"),
                "date": ripple_time_to_iso(tx.get("date")),
                "result": meta.get("TransactionResult"),
                "delivered_xrp": (
                    int(meta["delivered_amount"]) / DROPS_PER_XRP
                    if isinstance(meta.get("delivered_amount"), str)
                    else None
                ),
            }
        )

    return {
        "account": address,
        "transactions": transactions,
        "marker": result.get("marker"),
        "has_more": result.get("marker") is not None,
    }


def ripple_time_to_iso(ripple_time: int | None) -> str | None:
    if ripple_time is None:
        return None
    from datetime import datetime, timezone

    unix = ripple_time + 946684800
    return datetime.fromtimestamp(unix, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")