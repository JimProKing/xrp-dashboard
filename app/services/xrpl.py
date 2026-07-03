import httpx

XRPL_CLUSTER = "https://xrplcluster.com"
XRP_SCAN = "https://api.xrpscan.com/api/v1"
INITIAL_SUPPLY_XRP = 100_000_000_000
DROPS_PER_XRP = 1_000_000


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
    body = {
        "method": "ledger",
        "params": [{"ledger_index": "validated", "transactions": False, "expand": False}],
    }
    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.post(XRPL_CLUSTER, json=body)
        response.raise_for_status()
        ledger = response.json()["result"]["ledger"]

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

    body = {"method": "account_tx", "params": [params]}
    async with httpx.AsyncClient(timeout=20.0) as client:
        response = await client.post(XRPL_CLUSTER, json=body)
        data = response.json()

    if data.get("result", {}).get("status") == "error":
        error = data["result"].get("error_message", data["result"].get("error", "Unknown error"))
        raise ValueError(error)

    result = data["result"]
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