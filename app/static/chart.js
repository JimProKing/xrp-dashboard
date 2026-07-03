(function () {
  const CHART_LIMITS = { "1m": 480, "5m": 480, "15m": 480, "1h": 720, "4h": 540, "1d": 365 };
  let chart = null;
  let candleSeries = null;
  let volumeSeries = null;
  let ws = null;
  let state = { exchange: "binance", interval: "1h" };
  let initialized = false;
  let controlsBound = false;

  function $(id) {
    return document.getElementById(id);
  }

  const PRICE_DECIMALS = { min: 4, max: 5 };

  function formatPrice(price, exchange) {
    if (price == null) return "-";
    const opts = {
      minimumFractionDigits: PRICE_DECIMALS.min,
      maximumFractionDigits: PRICE_DECIMALS.max,
    };
    if (exchange === "upbit") {
      return "₩" + Number(price).toLocaleString("ko-KR", opts);
    }
    return "$" + Number(price).toLocaleString("en-US", opts);
  }

  function applyPriceFormat() {
    if (!candleSeries) return;
    candleSeries.applyOptions({
      priceFormat: {
        type: "price",
        precision: PRICE_DECIMALS.max,
        minMove: state.exchange === "upbit" ? 0.0001 : 0.00001,
      },
    });
  }

  function formatVol(vol) {
    if (vol >= 1_000_000) return (vol / 1_000_000).toFixed(2) + "M";
    if (vol >= 1_000) return (vol / 1_000).toFixed(2) + "K";
    return vol.toFixed(2);
  }

  function closeWs() {
    if (ws) {
      ws.onclose = null;
      ws.onerror = null;
      ws.onmessage = null;
      ws.close();
      ws = null;
    }
  }

  function updateTicker(ticker) {
    const priceEl = $("chart-price");
    const changeEl = $("chart-change");
    const highEl = $("chart-high");
    const lowEl = $("chart-low");
    const volEl = $("chart-volume");
    if (!priceEl) return;

    priceEl.textContent = formatPrice(ticker.price, state.exchange);
    const pct = ticker.change_pct;
    changeEl.textContent = `${pct >= 0 ? "+" : ""}${pct.toFixed(2)}%`;
    changeEl.className = "chart-change " + (pct >= 0 ? "positive" : "negative");
    highEl.textContent = formatPrice(ticker.high, state.exchange);
    lowEl.textContent = formatPrice(ticker.low, state.exchange);
    volEl.textContent = formatVol(ticker.volume) + " XRP";
  }

  function setStatus(text, live) {
    const el = $("chart-status");
    if (!el) return;
    el.textContent = text;
    el.className = "chart-status" + (live ? " live" : "");
  }

  function lockVisibleRange(candles) {
    if (!chart || candles.length < 2) return;
    chart.timeScale().setVisibleRange({
      from: candles[0].time,
      to: candles[candles.length - 1].time,
    });
  }

  function buildChart() {
    const container = $("chart-container");
    if (!container || typeof LightweightCharts === "undefined") return;

    container.innerHTML = "";
    chart = LightweightCharts.createChart(container, {
      width: container.clientWidth,
      height: 460,
      layout: {
        background: { type: "solid", color: "#ffffff" },
        textColor: "#616e85",
        fontFamily: "'Segoe UI', sans-serif",
      },
      grid: {
        vertLines: { color: "#eff2f5" },
        horzLines: { color: "#eff2f5" },
      },
      crosshair: { mode: LightweightCharts.CrosshairMode.Normal },
      rightPriceScale: { borderColor: "#eff2f5" },
      handleScroll: { mouseWheel: true, pressedMouseMove: true, horzTouchDrag: true },
      handleScale: { mouseWheel: true, pinch: true, axisPressedMouseMove: true },
      timeScale: {
        borderColor: "#eff2f5",
        timeVisible: true,
        secondsVisible: state.interval === "1m",
        fixLeftEdge: true,
        fixRightEdge: true,
        rightOffset: 2,
      },
    });

    candleSeries = chart.addCandlestickSeries({
      upColor: "#16c784",
      downColor: "#ea3943",
      borderVisible: false,
      wickUpColor: "#16c784",
      wickDownColor: "#ea3943",
      priceFormat: {
        type: "price",
        precision: PRICE_DECIMALS.max,
        minMove: state.exchange === "upbit" ? 0.0001 : 0.00001,
      },
    });

    volumeSeries = chart.addHistogramSeries({
      priceFormat: { type: "volume" },
      priceScaleId: "",
    });
    volumeSeries.priceScale().applyOptions({ scaleMargins: { top: 0.82, bottom: 0 } });

    new ResizeObserver(() => {
      if (chart && container) chart.applyOptions({ width: container.clientWidth });
    }).observe(container);
  }

  function applyCandles(candles) {
    if (!candleSeries || !volumeSeries) return;

    candleSeries.setData(
      candles.map((c) => ({
        time: c.time,
        open: c.open,
        high: c.high,
        low: c.low,
        close: c.close,
      }))
    );

    volumeSeries.setData(
      candles.map((c) => ({
        time: c.time,
        value: c.volume,
        color: c.close >= c.open ? "rgba(22,199,132,0.5)" : "rgba(234,57,67,0.5)",
      }))
    );

    lockVisibleRange(candles);
  }

  function updateLastCandle(candle) {
    if (!candleSeries || !volumeSeries) return;
    candleSeries.update({
      time: candle.time,
      open: candle.open,
      high: candle.high,
      low: candle.low,
      close: candle.close,
    });
    volumeSeries.update({
      time: candle.time,
      value: candle.volume,
      color: candle.close >= candle.open ? "rgba(22,199,132,0.5)" : "rgba(234,57,67,0.5)",
    });
  }

  function connectBinanceWs(stream) {
    closeWs();
    ws = new WebSocket(`wss://stream.binance.com:9443/ws/${stream}`);
    ws.onopen = () => setStatus(`실시간 · ${stream}`, true);
    ws.onclose = () => setStatus("연결 끊김", false);
    ws.onerror = () => setStatus("연결 오류", false);
    ws.onmessage = (ev) => {
      const k = JSON.parse(ev.data).k;
      if (!k) return;
      updateLastCandle({
        time: Math.floor(k.t / 1000),
        open: parseFloat(k.o),
        high: parseFloat(k.h),
        low: parseFloat(k.l),
        close: parseFloat(k.c),
        volume: parseFloat(k.v),
      });
      const priceEl = $("chart-price");
      if (priceEl) priceEl.textContent = formatPrice(parseFloat(k.c), "binance");
    };
  }

  function connectUpbitWs(unit) {
    closeWs();
    ws = new WebSocket("wss://api.upbit.com/websocket/v1");
    ws.onopen = () => {
      ws.send(
        JSON.stringify([
          { ticket: "xrp-dashboard" },
          { type: "ticker", codes: ["KRW-XRP"] },
          ...(unit > 0 ? [{ type: "candle", codes: ["KRW-XRP"], unit }] : []),
        ])
      );
      setStatus("실시간 · Upbit", true);
    };
    ws.onclose = () => setStatus("연결 끊김", false);
    ws.onerror = () => setStatus("연결 오류", false);
    ws.onmessage = (ev) => {
      ev.data.text().then((text) => {
        const msg = JSON.parse(text);
        if (msg.type === "ticker") {
          const priceEl = $("chart-price");
          if (priceEl) priceEl.textContent = formatPrice(msg.trade_price, "upbit");
          return;
        }
        if (msg.type === "candle") {
          updateLastCandle({
            time: Math.floor(msg.timestamp / 1000),
            open: msg.opening_price,
            high: msg.high_price,
            low: msg.low_price,
            close: msg.trade_price,
            volume: msg.candle_acc_trade_volume,
          });
        }
      });
    };
  }

  async function loadChart() {
    setStatus("로딩 중...", false);
    $("chart-symbol-label").textContent = state.exchange === "upbit" ? "KRW-XRP" : "XRP/USDT";

    const limit = CHART_LIMITS[state.interval] || 300;

    try {
      const res = await fetch(
        `/api/chart/klines?exchange=${state.exchange}&interval=${state.interval}&limit=${limit}`
      );
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "차트 로딩 실패");

      if (!initialized) {
        buildChart();
        initialized = true;
      } else {
        applyPriceFormat();
      }

      applyCandles(data.candles);
      updateTicker(data.ticker);
      setStatus(`캔들 ${data.count}개`, true);

      if (state.exchange === "binance") connectBinanceWs(data.ws_stream);
      else connectUpbitWs(data.ws_unit);
    } catch (e) {
      setStatus(e.message, false);
      if ($("chart-container") && !initialized) {
        $("chart-container").innerHTML = `<div class="chart-error">${e.message}</div>`;
      }
    }
  }

  function bindControls() {
    if (controlsBound) return;
    controlsBound = true;

    document.querySelectorAll("[data-exchange]").forEach((btn) => {
      btn.addEventListener("click", () => {
        document.querySelectorAll("[data-exchange]").forEach((b) => b.classList.remove("active"));
        btn.classList.add("active");
        state.exchange = btn.dataset.exchange;
        loadChart();
      });
    });

    document.querySelectorAll("[data-interval]").forEach((btn) => {
      btn.addEventListener("click", () => {
        document.querySelectorAll("[data-interval]").forEach((b) => b.classList.remove("active"));
        btn.classList.add("active");
        state.interval = btn.dataset.interval;
        if (chart) chart.applyOptions({ timeScale: { secondsVisible: state.interval === "1m" } });
        loadChart();
      });
    });
  }

  window.initChart = function () {
    if ($("chart-container")) {
      bindControls();
      loadChart();
      if (window.initPremiumChart) window.initPremiumChart();
    }
  };

  window.destroyChart = function () {
    closeWs();
    if (chart) {
      chart.remove();
      chart = null;
      candleSeries = null;
      volumeSeries = null;
    }
    initialized = false;
    controlsBound = false;
    if ($("chart-container")) $("chart-container").innerHTML = "";
    if (window.destroyPremiumChart) window.destroyPremiumChart();
  };
})();