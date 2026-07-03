# XRP On-Chain Dashboard

XRPL 온체인 데이터, 거래소 거래량, 프리미엄, 실시간 캔들 차트를 한곳에서 보는 대시보드입니다.

## 기능

- XRP 부자 순위 (XRPSCAN)
- 소각량 / 유통량 (XRPL)
- 거래소별 24h 거래량 (CoinGecko)
- 업비트 기준 프리미엄
- Binance / Upbit 실시간 캔들 차트
- 주소별 트랜잭션 조회

## 로컬 실행

```bash
pip install -r requirements.txt
python run.py
```

브라우저에서 http://127.0.0.1:8000 접속

## Railway 배포

1. GitHub 저장소를 Railway에 연결
2. **New Project → Deploy from GitHub repo** 선택
3. Railway가 `requirements.txt`와 `railway.toml`을 자동 인식
4. `PORT` 환경 변수는 Railway가 자동 주입 (별도 설정 불필요)
5. 배포 후 생성된 URL로 접속

### 수동 설정 시

- **Start Command:** `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- **Health Check:** `/`

## API

| Endpoint | 설명 |
|----------|------|
| `GET /api/richlist` | 부자 순위 |
| `GET /api/burn` | 소각량 |
| `GET /api/exchanges` | 거래소 거래량 |
| `GET /api/premium` | 프리미엄 |
| `GET /api/chart/klines` | 캔들 차트 |
| `GET /api/transactions` | 주소 트랜잭션 |