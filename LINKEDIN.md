# LinkedIn 게시글 (복사용)

---

XRP 온체인 데이터를 한 화면에서 볼 수 있는 대시보드를 직접 만들어 배포했습니다.

리플(XRP) 관련 정보가 여러 사이트에 흩어져 있어서, 부자 순위·소각량·거래소 거래량·김치 프리미엄·실시간 차트·주소별 트랜잭션 조회를 하나로 모았습니다.

주요 기능
→ XRPL 부자 순위 & 소각량 / 유통량
→ CoinGecko 기준 거래소별 24h 거래량
→ 업비트 기준 김치 프리미엄
→ Binance·Upbit 실시간 캔들 차트
→ XRP 주소 트랜잭션 탐색

기술 스택: Python, FastAPI, Lightweight Charts
배포: Railway

라이브 데모: https://web-production-7a41a.up.railway.app/
GitHub: https://github.com/JimProKing/xrp-dashboard

클라우드 배포 환경에서 외부 API 지역 제한(451, 402 등)이 발생해 Kraken·Ripple 공용 RPC로 폴백하는 것까지 경험했습니다. 실서비스에 가까운 사이드 프로젝트로 꽤 배울 점이 많았습니다.

피드백이나 개선 아이디어 있으시면 댓글로 편하게 남겨주세요.

#XRP #Ripple #Python #FastAPI #DataDashboard #SideProject #Railway #Crypto #Blockchain #WebDevelopment

---

## English version (optional)

Built and deployed an XRP On-Chain Dashboard — rich list, burn stats, exchange volumes, kimchi premium, live charts, and address lookup in one place.

Live demo: https://web-production-7a41a.up.railway.app/
GitHub: https://github.com/JimProKing/xrp-dashboard

Stack: Python · FastAPI · Lightweight Charts · Railway

Handled real-world API constraints (geo-blocks, paid endpoints) with fallback providers — great learning experience shipping something end-to-end.

Feedback welcome in the comments.

#XRP #Ripple #Python #FastAPI #WebDevelopment #SideProject #Railway #Crypto #Blockchain