# XRP On-Chain Dashboard

XRPL 온체인 데이터, 거래소 거래량, 김치 프리미엄, 실시간 캔들 차트를 한곳에서 볼 수 있는 대시보드입니다.

## Links

| | |
|---|---|
| **Live** | https://web-production-7a41a.up.railway.app/ |
| **GitHub** | https://github.com/JimProKing/xrp-dashboard |

## Features

- **부자 순위** — XRPSCAN 기준 상위 지갑 보유량
- **소각량** — XRPL 유통량·소각 통계
- **거래소 거래량** — CoinGecko 24h 현물 거래량
- **프리미엄** — 업비트 KRW vs 글로벌 거래소
- **실시간 차트** — Binance/Kraken(USD), Upbit(KRW) 캔들
- **주소 조회** — XRP Ledger 트랜잭션 탐색

## Tech Stack

- Python · FastAPI · Jinja2
- Lightweight Charts (프론트엔드 차트)
- Railway 배포

## Local Setup

```bash
pip install -r requirements.txt
python run.py
```

http://127.0.0.1:8000 에서 확인

## Railway Deploy

1. Railway에서 **Deploy from GitHub** → `xrp-dashboard` 선택
2. `railway.toml` · `requirements.txt` 자동 인식
3. `PORT`는 Railway가 자동 설정

**Start Command** (수동 설정 시)

```
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

### Environment Variables (optional)

| Variable | Default | Description |
|----------|---------|-------------|
| `GLOBAL_CHART_SOURCE` | `auto` | `auto` · `kraken` · `binance` |
| `XRPL_RPC_URL` | `xrpl.ws, s1/s2.ripple.com` | XRPL JSON-RPC (쉼표 구분) |

> 클라우드 환경에서는 Binance 451 · xrplcluster 402 등 지역/유료 제한이 있어 Kraken·Ripple 공용 RPC로 자동 폴백합니다.

## API

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/richlist` | 부자 순위 |
| `GET` | `/api/burn` | 소각량 |
| `GET` | `/api/exchanges` | 거래소 거래량 |
| `GET` | `/api/premium` | 프리미엄 |
| `GET` | `/api/chart/klines` | 캔들 차트 |
| `GET` | `/api/transactions` | 주소 트랜잭션 |

## Contact

- Email: caramel2516@naver.com
- KakaoTalk ID: caramel112