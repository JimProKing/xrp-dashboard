const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => document.querySelectorAll(sel);

let txMarker = null;
let txAddress = "";

function formatNum(n, decimals = 2) {
  if (n == null || Number.isNaN(n)) return "-";
  return Number(n).toLocaleString("ko-KR", {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  });
}

function formatXrp(n) {
  if (n == null) return "-";
  if (n >= 1_000_000) return formatNum(n, 0) + " XRP";
  if (n >= 1) return formatNum(n, 2) + " XRP";
  return formatNum(n, 6) + " XRP";
}

function shorten(addr) {
  if (!addr || addr.length < 12) return addr;
  return `${addr.slice(0, 8)}...${addr.slice(-6)}`;
}

function premiumClass(pct) {
  if (pct > 0.5) return "positive";
  if (pct < -0.5) return "negative";
  return "neutral";
}

async function fetchJSON(url) {
  const res = await fetch(url);
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || "요청 실패");
  return data;
}

function setLoading(panelId, msg = "데이터 로딩 중...") {
  const panel = $(`#${panelId}`);
  panel.innerHTML = `<div class="loading">${msg}</div>`;
}

function showError(panelId, msg) {
  const panel = $(`#${panelId}`);
  panel.innerHTML = `<div class="error">${msg}</div>`;
}

async function loadOverview() {
  try {
    const [burn, premium] = await Promise.all([
      fetchJSON("/api/burn"),
      fetchJSON("/api/premium"),
    ]);

    $("#burned-xrp").textContent = formatXrp(burn.burned);
    $("#burn-pct").textContent = `${formatNum(burn.burn_percentage, 4)}% 소각`;
    $("#supply-xrp").textContent = formatXrp(burn.current_supply);
    $("#upbit-price").textContent = `₩${formatNum(premium.upbit.price_krw, 0)}`;
    $("#global-price").textContent = `$${formatNum(premium.global_avg_usd, 4)}`;

    const prem = premium.upbit_premium.premium_pct;
    const el = $("#kimchi-premium");
    el.textContent = `${prem >= 0 ? "+" : ""}${formatNum(prem, 3)}%`;
    el.className = `stat-value ${premiumClass(prem)}`;
  } catch (e) {
    console.error(e);
  }
}

async function loadRichList() {
  setLoading("richlist-content");
  try {
    const data = await fetchJSON("/api/richlist?limit=50");
    const rows = data.accounts
      .map(
        (a) => `
      <tr>
        <td class="rank-cell">${a.rank}</td>
        <td>
          <span class="mono">${shorten(a.account)}</span>
          ${a.label ? `<span class="badge">${a.label}</span>` : ""}
        </td>
        <td class="num">${formatXrp(a.supply_xrp)}</td>
        <td class="num">${a.escrow_xrp > 0 ? formatXrp(a.escrow_xrp) : "-"}</td>
        <td><a class="link" href="#" data-address="${a.account}">조회</a></td>
      </tr>`
      )
      .join("");

    $("#richlist-content").innerHTML = `
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>#</th>
              <th>주소</th>
              <th class="num">보유량</th>
              <th class="num">에스크로</th>
              <th></th>
            </tr>
          </thead>
          <tbody>${rows}</tbody>
        </table>
      </div>
      <p class="footnote">* XRPSCAN 기준, 일 1회 갱신</p>`;

    $$("#richlist-content [data-address]").forEach((link) => {
      link.addEventListener("click", (e) => {
        e.preventDefault();
        openAddressSearch(link.dataset.address);
      });
    });
  } catch (e) {
    showError("richlist-content", e.message);
  }
}

async function loadBurn() {
  setLoading("burn-content");
  try {
    const data = await fetchJSON("/api/burn");
    $("#burn-content").innerHTML = `
      <div class="stats-grid">
        <div class="stat-card">
          <div class="stat-label">초기 공급량</div>
          <div class="stat-value">${formatXrp(data.initial_supply)}</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">현재 유통량</div>
          <div class="stat-value">${formatXrp(data.current_supply)}</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">총 소각량</div>
          <div class="stat-value positive">${formatXrp(data.burned)}</div>
          <div class="stat-sub">${formatNum(data.burn_percentage, 4)}% 소각</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">최신 레저</div>
          <div class="stat-value">#${formatNum(data.ledger_index, 0)}</div>
          <div class="stat-sub">${data.updated_at || ""}</div>
        </div>
      </div>
      <p class="footnote">XRP Ledger 트랜잭션 수수료로 인해 영구 소각됩니다.</p>`;
  } catch (e) {
    showError("burn-content", e.message);
  }
}

async function loadExchanges() {
  setLoading("exchanges-content");
  try {
    const data = await fetchJSON("/api/exchanges");

    const rows = data.exchanges
      .slice(0, 30)
      .map(
        (ex, i) => `
      <tr>
        <td class="rank-cell">${i + 1}</td>
        <td><span class="exchange-name">${ex.exchange}</span></td>
        <td>${ex.pairs.slice(0, 4).join(", ")}</td>
        <td class="num">$${formatNum(ex.volume_usd, 0)}</td>
        <td class="num">${formatNum(ex.share_pct, 2)}%</td>
      </tr>`
      )
      .join("");

    $("#exchanges-content").innerHTML = `
      <div class="summary-row">
        <div><span>총 24h 거래량</span> <strong>$${formatNum(data.total_volume_usd, 0)}</strong></div>
        <div><span>거래소 수</span> <strong>${data.exchange_count}개</strong></div>
      </div>
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>#</th>
              <th>거래소</th>
              <th>거래쌍</th>
              <th class="num">24h 거래량</th>
              <th class="num">거래대금 %</th>
            </tr>
          </thead>
          <tbody>${rows}</tbody>
        </table>
      </div>`;
  } catch (e) {
    showError("exchanges-content", e.message);
  }
}

async function loadPremium() {
  setLoading("premium-content");
  try {
    const data = await fetchJSON("/api/premium");
    const prem = data.upbit_premium;

    const koreanRows = data.korean_exchanges
      .map(
        (k) => `
      <tr>
        <td><span class="exchange-name">${k.exchange}</span></td>
        <td class="num">₩${formatNum(k.price_krw, 0)}</td>
        <td class="num ${premiumClass(k.premium_vs_global.premium_pct)}">${k.premium_vs_global.premium_pct >= 0 ? "+" : ""}${formatNum(k.premium_vs_global.premium_pct, 3)}%</td>
        <td class="num">${formatNum(k.volume_24h, 0)} XRP</td>
        <td class="num ${k.change_rate >= 0 ? "positive" : "negative"}">${k.change_rate >= 0 ? "+" : ""}${formatNum(k.change_rate, 2)}%</td>
      </tr>`
      )
      .join("");

    const compRows = data.comparisons
      .map(
        (c) => `
      <tr>
        <td><span class="exchange-name">${c.reference_exchange}</span></td>
        <td class="num">$${formatNum(c.reference_price_usd, 4)}</td>
        <td class="num">₩${formatNum(c.reference_price_krw, 0)}</td>
        <td class="num ${premiumClass(c.premium_pct)}">${c.premium_pct >= 0 ? "+" : ""}${formatNum(c.premium_pct, 3)}%</td>
        <td class="num">${c.premium_krw >= 0 ? "+" : ""}₩${formatNum(c.premium_krw, 0)}</td>
      </tr>`
      )
      .join("");

    $("#premium-content").innerHTML = `
      <div class="premium-highlight">
        <div class="stat-label">업비트 기준 김치 프리미엄 (글로벌 평균 대비)</div>
        <div class="big ${premiumClass(prem.premium_pct)}">${prem.premium_pct >= 0 ? "+" : ""}${formatNum(prem.premium_pct, 3)}%</div>
        <div class="stat-sub">업비트 ₩${formatNum(prem.price_krw, 0)} · 적정가 ₩${formatNum(prem.fair_price_krw, 0)} · USD/KRW ${formatNum(data.usd_krw_rate, 2)}</div>
      </div>
      <div class="section-title">국내 거래소</div>
      <div class="table-wrap" style="margin-bottom:8px">
        <table>
          <thead><tr><th>거래소</th><th class="num">가격</th><th class="num">프리미엄</th><th class="num">24h 거래량</th><th class="num">변동률</th></tr></thead>
          <tbody>${koreanRows}</tbody>
        </table>
      </div>
      <div class="section-title">거래소별 프리미엄 (업비트 vs 글로벌)</div>
      <div class="table-wrap">
        <table>
          <thead><tr><th>기준 거래소</th><th class="num">USD</th><th class="num">KRW 환산</th><th class="num">프리미엄</th><th class="num">차이</th></tr></thead>
          <tbody>${compRows}</tbody>
        </table>
      </div>`;
  } catch (e) {
    showError("premium-content", e.message);
  }
}

async function loadTransactions(address, append = false) {
  if (!append) {
    setLoading("tx-content");
    txMarker = null;
    txAddress = address;
  }

  try {
    let url = `/api/transactions?address=${encodeURIComponent(address)}&limit=20`;
    if (txMarker) url += `&marker=${encodeURIComponent(JSON.stringify(txMarker))}`;

    const data = await fetchJSON(url);
    txMarker = data.marker;

    const rows = data.transactions
      .map(
        (tx) => `
      <tr>
        <td class="mono">${shorten(tx.hash)}</td>
        <td><span class="badge badge-type">${tx.type}</span></td>
        <td class="mono">${shorten(tx.account)}</td>
        <td class="mono">${tx.destination ? shorten(tx.destination) : "-"}</td>
        <td class="num">${tx.amount_xrp != null ? formatXrp(tx.amount_xrp) : "-"}</td>
        <td class="num">${formatXrp(tx.fee_xrp)}</td>
        <td class="num">#${tx.ledger_index}</td>
        <td>${tx.date || "-"}</td>
        <td class="${tx.result === "tesSUCCESS" ? "positive" : "negative"}">${tx.result}</td>
      </tr>`
      )
      .join("");

    if (!append) {
      $("#tx-content").innerHTML = `
        <div class="summary-row">
          <div><span>조회 주소</span> <strong class="mono">${address}</strong></div>
        </div>
        <div class="table-wrap">
          <table>
            <thead>
              <tr>
                <th>해시</th><th>유형</th><th>발신</th><th>수신</th>
                <th class="num">금액</th><th class="num">수수료</th><th class="num">레저</th><th>시간</th><th>결과</th>
              </tr>
            </thead>
            <tbody id="tx-tbody">${rows}</tbody>
          </table>
        </div>
        <div class="load-more" id="tx-load-more"></div>`;
    } else {
      $("#tx-tbody").insertAdjacentHTML("beforeend", rows);
    }

    const loadMoreEl = $("#tx-load-more");
    if (data.has_more) {
      loadMoreEl.innerHTML = `<button id="tx-more-btn">더 불러오기</button>`;
      $("#tx-more-btn").addEventListener("click", () => loadTransactions(txAddress, true));
    } else {
      loadMoreEl.innerHTML = "";
    }
  } catch (e) {
    if (!append) showError("tx-content", e.message);
  }
}

function openAddressSearch(address) {
  switchTab("explorer");
  $("#address-input").value = address;
  loadTransactions(address);
}

let chartActive = false;

function switchTab(tabId) {
  $$(".tab").forEach((t) => t.classList.toggle("active", t.dataset.tab === tabId));
  $$(".panel").forEach((p) => p.classList.toggle("active", p.id === `panel-${tabId}`));

  if (tabId === "chart") {
    if (!chartActive && window.initChart) {
      window.initChart();
      chartActive = true;
    }
    return;
  }

  if (chartActive && window.destroyChart) {
    window.destroyChart();
    chartActive = false;
  }

  const loaders = {
    richlist: loadRichList,
    burn: loadBurn,
    exchanges: loadExchanges,
    premium: loadPremium,
  };
  if (loaders[tabId]) loaders[tabId]();
}

function openKakaoFriendAdd(id) {
  const encoded = encodeURIComponent(id);
  const isAndroid = /Android/i.test(navigator.userAgent);

  if (isAndroid) {
    window.location.href =
      `intent://search?query=${encoded}#Intent;scheme=kakaotalk;package=com.kakao.talk;end`;
    return;
  }

  window.location.href = `kakaotalk://friend/search?id=${encoded}`;
}

function initKakaoLinks() {
  $$(".kakao-link").forEach((link) => {
    link.addEventListener("click", (e) => {
      e.preventDefault();
      const id = link.dataset.kakaoId;
      if (id) openKakaoFriendAdd(id);
    });
  });
}

function init() {
  initKakaoLinks();

  $$(".tab").forEach((tab) => {
    tab.addEventListener("click", () => switchTab(tab.dataset.tab));
  });

  $("#refresh-btn").addEventListener("click", () => {
    loadOverview();
    const active = $(".tab.active")?.dataset.tab;
    if (active && active !== "explorer") switchTab(active);
  });

  $("#search-btn").addEventListener("click", () => {
    const addr = $("#address-input").value.trim();
    if (!addr.startsWith("r") || addr.length < 25) {
      showError("tx-content", "유효한 XRP 주소를 입력하세요 (r로 시작)");
      return;
    }
    loadTransactions(addr);
  });

  $("#address-input").addEventListener("keydown", (e) => {
    if (e.key === "Enter") $("#search-btn").click();
  });

  loadOverview();

  if ($(".tab.active")?.dataset.tab === "chart" && window.initChart) {
    window.initChart();
    chartActive = true;
  } else {
    loadRichList();
  }
}

document.addEventListener("DOMContentLoaded", init);