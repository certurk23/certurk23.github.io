
/* ============================================================
   THEME
   ============================================================ */
const saved = localStorage.getItem('qm-theme') || 'dark';
document.documentElement.setAttribute('data-theme', saved);

function nlSubmit(e){e.preventDefault();var f=document.getElementById('nlForm'),b=document.getElementById('nlBtn');b.textContent='Sending…';b.disabled=true;fetch(f.action,{method:'POST',body:new FormData(f),headers:{'Accept':'application/json'}}).then(function(r){if(r.ok){f.style.display='none';document.getElementById('nlSuccess').style.display='block';}else{b.textContent='Try again';b.disabled=false;}}).catch(function(){b.textContent='Try again';b.disabled=false;});}
// Auto-show success if redirected back
if(new URLSearchParams(location.search).get('subscribed')==='1'){var nf=document.getElementById('nlForm');if(nf){nf.style.display='none';document.getElementById('nlSuccess').style.display='block';}}
function toggleMenu(){var h=document.getElementById('hamburger'),m=document.getElementById('mobileNav');h.classList.toggle('open');m.classList.toggle('open');document.body.style.overflow=m.classList.contains('open')?'hidden':'';}
document.querySelectorAll('.mobile-nav a').forEach(function(a){a.addEventListener('click',function(){document.getElementById('hamburger').classList.remove('open');document.getElementById('mobileNav').classList.remove('open');document.body.style.overflow='';});});
function toggleTheme() {
  const cur = document.documentElement.getAttribute('data-theme');
  const next = cur === 'dark' ? 'light' : 'dark';
  document.documentElement.setAttribute('data-theme', next);
  localStorage.setItem('qm-theme', next);
}

/* ============================================================
   MARKET DATA — FMP Batch (primary) + CoinGecko + open.er-api
   ============================================================ */
/* No API keys in client source. Everything below reads snapshots from
   /data/*.json written by scripts/daily_update.py. The previous version
   shipped live FMP and Finnhub tokens in this file, which are public the
   moment the page loads. */

const fmt  = (n, d=2) => n == null || isNaN(n) ? '--' : n.toLocaleString('en-US', {minimumFractionDigits:d, maximumFractionDigits:d});
const pct  = v => v == null ? '--' : (v > 0 ? '+' : '') + fmt(v) + '%';
const cls  = v => v > 0 ? 'up' : v < 0 ? 'dn' : 'nt';
const sgn  = v => v > 0 ? '+' : '';
const now  = () => new Date().toLocaleTimeString('en-US', {hour12:false, hour:'2-digit', minute:'2-digit'});

/* --- Market data: one snapshot read, shared by the bar and the sidebar ---
   data/markets_bar.json is written nightly with real instruments pulled
   server-side. The previous client version proxied gold with the PAX-Gold
   token and WTI with a CoinGecko id, which are not those markets. */
let _barPromise = null;
function barRows() {
  if (!_barPromise) _barPromise = QM.get('markets_bar');
  return _barPromise;
}

function rowFor(feed, sym) {
  const rows = feed && feed.data;
  if (!rows) return null;
  return rows.find(r => r.s === sym) || null;
}

/* --- Market Bar --- */
const MBAR = [
  {s:'^GSPC',    l:'S&P 500'},
  {s:'^IXIC',    l:'Nasdaq'},
  {s:'^VIX',     l:'VIX'},
  {s:'GC=F',     l:'Gold'},
  {s:'EURUSD=X', l:'EUR/USD'},
  {s:'BTC-USD',  l:'BTC'},
];
async function loadMarketBar() {
  const feed = await barRows();
  const host = document.getElementById('marketBar');
  if (!host) return;
  const cells = MBAR.map(m => {
    const r = rowFor(feed, m.s);
    if (!r) return '';
    return `<div class="mbar-item">
      <span class="mbar-sym">${m.l}</span>
      <span class="mbar-val">${fmt(r.p, Math.abs(r.p) > 100 ? 2 : 4)}</span>
      <span class="mbar-chg ${cls(r.c)}">${pct(r.c)}</span>
    </div>`;
  }).filter(Boolean);
  // An empty bar is hidden rather than left as a row of dashes.
  if (!cells.length) { const w = host.closest('.market-bar') || host; w.style.display = 'none'; return; }
  host.innerHTML = cells.join('');
}

/* --- Snapshot Sidebar --- */
const SNAP = [
  {s:'^GSPC',    l:'S&P 500', sub:'US large cap'},
  {s:'^VIX',     l:'VIX',     sub:'Implied volatility'},
  {s:'GC=F',     l:'Gold',    sub:'Spot $/oz'},
  {s:'CL=F',     l:'WTI',     sub:'Crude $/bbl'},
  {s:'EURUSD=X', l:'EUR/USD', sub:'Forex'},
  {s:'BTC-USD',  l:'Bitcoin', sub:'Crypto'},
];
async function loadSnapshot() {
  const feed = await barRows();
  const host = document.getElementById('snapRows');
  if (!host) return;
  const rows = SNAP.map(s => {
    const r = rowFor(feed, s.s);
    if (!r) return '';
    const dp = Math.abs(r.p) > 100 ? 2 : 4;
    return `<div class="snap-row">
      <div><div class="snap-sym">${s.l}</div><div class="snap-name">${s.sub}</div></div>
      <div style="text-align:right">
        <div class="snap-price">${fmt(r.p, dp)}</div>
        <div class="snap-chg ${cls(r.c)}">${pct(r.c)}</div>
      </div>
    </div>`;
  }).filter(Boolean);
  const ts = document.getElementById('snapTs');
  if (!rows.length) {
    host.innerHTML = '<div class="snap-row" style="color:var(--muted);font-size:12px">' +
                     'Next snapshot publishes after the US close.</div>';
    if (ts) { ts.textContent = 'pending'; }
    return;
  }
  host.innerHTML = rows.join('');
  // Timestamp reflects the snapshot, not the visitor's clock.
  if (ts && feed) QM.stamp(ts, feed.fetched_utc, 'Close');
}

/* --- Movers: top and bottom performers from the 180-name scan universe --- */
/* Display names for the tickers most likely to surface in the movers list.
   Anything not listed falls back to its symbol. */
const NAMES = {
  NVDA:'NVIDIA',AAPL:'Apple',MSFT:'Microsoft',TSLA:'Tesla',AMD:'Advanced Micro',
  META:'Meta Platforms',AMZN:'Amazon',GOOGL:'Alphabet',AVGO:'Broadcom',
  JPM:'JPMorgan Chase',NFLX:'Netflix',BA:'Boeing',INTC:'Intel',PFE:'Pfizer',
  COIN:'Coinbase',HOOD:'Robinhood',PLTR:'Palantir',MU:'Micron',MRVL:'Marvell',
  SMCI:'Super Micro',CRWD:'CrowdStrike',SNOW:'Snowflake',DDOG:'Datadog',
  NET:'Cloudflare',ZS:'Zscaler',PANW:'Palo Alto',ENPH:'Enphase',FSLR:'First Solar',
  OXY:'Occidental',SLB:'SLB',HAL:'Halliburton',FCX:'Freeport-McMoRan',
  NEM:'Newmont',GOLD:'Barrick',AEM:'Agnico Eagle',UNH:'UnitedHealth',
  LLY:'Eli Lilly',XOM:'Exxon Mobil',CVX:'Chevron',WMT:'Walmart',COST:'Costco',
  ORCL:'Oracle',CRM:'Salesforce',ADBE:'Adobe',NOW:'ServiceNow',UBER:'Uber',
  SOFI:'SoFi',NU:'Nu Holdings',AFRM:'Affirm',UPST:'Upstart',AI:'C3.ai',
};
let GAINERS_LIVE = [], LOSERS_LIVE = [];
let moversMode = 'gain';

/* Movers come from the same 180-name scan universe as the signal engine,
   so the homepage and quantum-signals.html can never disagree. */
async function loadMovers() {
  const data = await QM.get('quantum_signals');
  const rows = data && data.signals;
  if (!rows || !rows.length) return;
  const pairs = rows.filter(r => typeof r.chg === 'number' && r.chg !== 0)
                    .map(r => ({s: r.s, n: NAMES[r.s] || r.s, p: r.chg}));
  if (!pairs.length) return;
  pairs.sort((a, b) => b.p - a.p);
  GAINERS_LIVE = pairs.slice(0, 6);
  LOSERS_LIVE  = pairs.slice(-6).reverse();
  const lbl = document.getElementById('moversStamp');
  if (lbl) QM.stamp(lbl, data.updated, 'Session close');
  showMovers(moversMode);
}

function showMovers(mode) {
  moversMode = mode;
  document.getElementById('tabGain').className = 'mover-tab ' + (mode==='gain' ? 'gain-active' : 'inactive');
  document.getElementById('tabLose').className = 'mover-tab ' + (mode==='lose' ? 'lose-active' : 'inactive');
  const data = mode === 'gain' ? GAINERS_LIVE : LOSERS_LIVE;
  if (data.length === 0) {
    document.getElementById('moversPanel').innerHTML = '<div style="padding:14px;font-size:12px;color:var(--muted);text-align:center;line-height:1.7">Movers publish with the next post-close scan.<br><a href="quantum-signals.html" style="color:var(--green)">See the signal dashboard</a></div>';
    return;
  }
  document.getElementById('moversPanel').innerHTML = data.map((m, i) => {
    const c = cls(m.p);
    return `<div class="mover-row">
      <div class="mover-rank">${i+1}</div>
      <div class="mover-sym">${m.s}</div>
      <div class="mover-name">${m.n}</div>
      <div class="mover-chg ${c}">${sgn(m.p)+fmt(m.p)}%</div>
    </div>`;
  }).join('');
}


/* --- Init --- */
async function init() {
  showMovers(moversMode);
  await Promise.all([loadMarketBar(), loadSnapshot()]);
  loadMovers(); /* runs staggered, don't await */
}
init();

/* ============================================================
   NEWS FEED — reads data/news.json (no API key)
   ============================================================ */

function nAgo(ts) {
  if (!ts) return '';
  const m = Math.floor((Date.now()/1000 - ts) / 60);
  return m < 1 ? 'just now' : m < 60 ? m+'m ago' : m < 1440 ? Math.floor(m/60)+'h ago' : Math.floor(m/1440)+'d ago';
}
/* The pipeline already assigns a category with word-boundary matching; trust
   it. The old client-side regex used bare substrings and filed anything
   containing the letters "ai" (gain, against, remain) under Tech. */
function nCat(n) {
  if (n.category) return n.category;
  const h = (n.headline||'').toLowerCase();
  if (/fed|fomc|rate|yield|treasury|powell/.test(h)) return 'Fed · Rates';
  if (/nvidia|nvda|\bai\b|artificial|chip|semi/.test(h)) return 'Tech · AI';
  if (/vix|volatil|option|hedge/.test(h)) return 'Volatility';
  if (/oil|energy|crude|opec/.test(h)) return 'Energy';
  if (/bitcoin|crypto|btc|eth/.test(h)) return 'Crypto';
  if (/earning|profit|revenue|eps/.test(h)) return 'Earnings';
  if (/dark.pool|ats|microstruc|vpin/.test(h)) return 'Microstructure';
  return 'Markets';
}
function nImg(n, fallback) {
  return n.image ? `style="background-image:url('${n.image}');background-size:cover;background-position:center"` : fallback;
}
const GRADIENTS = [
  'style="background:linear-gradient(160deg,#0d1a2e,#1a2e4a)"',
  'style="background:linear-gradient(160deg,#051a14,#0d3326)"',
  'style="background:linear-gradient(160deg,#200d0d,#3d1515)"',
  'style="background:linear-gradient(160deg,#1a1a0d,#332d0d)"',
  'style="background:linear-gradient(160deg,#0d0d2e,#1a1a4a)"',
  'style="background:linear-gradient(160deg,#1a0d2e,#2d1545)"',
];

let _newsItems = [];

async function loadNews() {
  try {
    const feed = await QM.get('news');
    const raw = feed && feed.data;
    if (!raw || !raw.length) return;   // keep the static fallback markup
    _newsItems = raw.filter(n => n.headline && n.url).slice(0, 20);
    const items = _newsItems.slice(0, 7);
    if (items.length < 3) return;

    const [f, a, b, c, d, e, g] = items;
    const svgChart = `<svg class="nc-chart-svg" viewBox="0 0 600 190" xmlns="http://www.w3.org/2000/svg" preserveAspectRatio="none"><polyline points="0,140 60,130 120,145 180,110 240,95 300,105 360,80 420,62 480,55 540,48 600,38" fill="none" stroke="#00a651" stroke-width="2.5"/><polyline points="0,140 60,130 120,145 180,110 240,95 300,105 360,80 420,62 480,55 540,48 600,38 600,190 0,190" fill="#00a651" fill-opacity="0.06"/></svg>`;

    document.getElementById('newsGrid').innerHTML = `
    <div class="news-grid">
      <a href="${f.url}" target="_blank" rel="noopener" class="nc-featured">
        <div class="nc-featured-img nc-fi-macro" ${nImg(f,'')}>
          ${!f.image ? svgChart : ''}
        </div>
        <div class="nc-featured-body">
          <div>
            <div class="nc-cat">${nCat(f)}</div>
            <div class="nc-featured-title">${f.headline}</div>
            <div class="nc-featured-exrp">${(f.summary||'').slice(0,240)}</div>
          </div>
          <div class="nc-meta"><span class="nc-src">${f.source}</span><span class="nc-time">${nAgo(f.datetime)}</span></div>
        </div>
      </a>
      <div class="nc-col">
        ${[a,b,c].map((n,i) => !n ? '' : `
        <a href="${n.url}" target="_blank" rel="noopener" class="nc-item">
          <div class="nc-item-img" ${nImg(n, GRADIENTS[i])}></div>
          <div class="nc-item-body">
            <div>
              <div class="nc-cat">${nCat(n)}</div>
              <div class="nc-item-title">${n.headline}</div>
            </div>
            <div class="nc-meta"><span class="nc-src">${n.source}</span><span class="nc-time">${nAgo(n.datetime)}</span></div>
          </div>
        </a>`).join('')}
      </div>
    </div>
    <div class="news-row2">
      ${[d,e,g].map((n,i) => !n ? '' : `
      <a href="${n.url}" target="_blank" rel="noopener" class="nc-card">
        <div class="nc-cat">${nCat(n)}</div>
        <div class="nc-card-title">${n.headline}</div>
        <div class="nc-card-exrp">${(n.summary||'').slice(0,170)}</div>
        <div class="nc-meta"><span class="nc-src">${n.source}</span><span class="nc-time">${nAgo(n.datetime)}</span></div>
      </a>`).join('')}
    </div>`;

    // Update date label
    const ts = items[0]?.datetime;
    if (ts) {
      const d2 = new Date(ts*1000);
      const label = d2.toLocaleDateString('en-US',{month:'long',day:'numeric',year:'numeric'});
      const sub = document.querySelector('.news-wrap .sec-sub');
      if (sub) sub.textContent = label;
    }
  } catch(e) { /* keep static fallback */ }
}

// The snapshots refresh once per weekday, so polling them adds nothing.
loadNews();

/* ============================================================
   SITE SEARCH
   ============================================================ */
const SEARCH_INDEX = [
  {t:'page', title:'Free PSR Calculator', sub:'Calculate the Probabilistic Sharpe Ratio', url:'tools/probabilistic-sharpe-ratio-calculator.html', kw:'psr calculator sharpe tool hesaplayıcı'},
  {t:'page', title:'Tools & Code', sub:'Runnable Python examples and GitHub source', url:'reproducibility.html', kw:'github code python tools vpin hrp'},
  {t:'page', title:'Worked Examples', sub:'VPIN, HRP and PSR results with reproduction steps', url:'reports/', kw:'examples reports verification vpin hrp psr'},
  {t:'page', title:'Home', sub:'Homepage — market data, news, analysis', url:'index.html', kw:'home homepage ana sayfa'},
  {t:'page', title:'Live Data', sub:'US market data: indices, forex and crypto snapshots', url:'markets.html', kw:'markets live data piyasa veri indices forex commodities crypto'},
  {t:'page', title:'News', sub:'Financial news feed with category filters', url:'news.html', kw:'news haber haberler fed tech energy crypto earnings'},
  {t:'page', title:'Equities', sub:'US stocks, sectors, gainers & losers', url:'stocks.html', kw:'stocks equities hisse senet sectors gainers losers'},
  {t:'page', title:'Analysis', sub:'Research papers & quantitative studies', url:'papers.html', kw:'analysis papers makaleler research araştırma'},
  {t:'page', title:'Research', sub:'Research overview & deep analysis', url:'research.html', kw:'research araştırma quant quantitative'},
  {t:'page', title:'About', sub:'About QuantMedia & QuantMedia', url:'about.html', kw:'about hakkında quantmedia'},
  {t:'page', title:'Methodology', sub:'Data sources, editorial standards', url:'methodology.html', kw:'methodology metodoloji data sources kaynaklar'},
  {t:'page', title:'Infrastructure', sub:'Trading stack & GPU infrastructure', url:'infrastructure.html', kw:'infrastructure altyapı gpu rtx cpu server'},
  {t:'paper', title:'VPIN & Order Flow Toxicity', sub:'Paper 01 — Microstructure', url:'paper-vpin-order-flow-toxicity.html', kw:'vpin order flow toxicity microstructure dark pool'},
  {t:'paper', title:'Low-Latency Stack: RTX 5090 & CPU', sub:'Paper 02 — Infrastructure', url:'paper-gpu-cpu-trading-infrastructure.html', kw:'gpu cpu rtx 5090 latency trading stack'},
  {t:'paper', title:'Hierarchical Risk Parity (HRP)', sub:'Paper 03 — Portfolio', url:'paper-hierarchical-risk-parity.html', kw:'hrp risk parity portfolio clustering'},
  {t:'paper', title:'Probabilistic Sharpe Ratio', sub:'Paper 04 — Statistics', url:'paper-probabilistic-sharpe-ratio.html', kw:'psr sharpe ratio backtest overfitting'},
  {t:'paper', title:'Bid-Ask Spread Dynamics', sub:'Paper 05 — Microstructure', url:'paper-bid-ask-spread-dynamics.html', kw:'spread bid ask microstructure execution'},
  {t:'paper', title:'BIST Sentiment Analysis', sub:'Paper 06 — NLP / Turkish Market', url:'paper-bist-sentiment-analysis.html', kw:'bist sentiment nlp turkish borsa istanbul qwen llama'},
  {t:'paper', title:'Sovereign AI: Local LLMs', sub:'Paper 07 — AI', url:'paper-sovereign-ai-local-llms.html', kw:'sovereign ai llm local privacy bastion'},
  {t:'paper', title:'Genetic Algorithm Alpha Discovery', sub:'Paper 08 — Optimization', url:'paper-genetic-algorithm-alpha.html', kw:'genetic algorithm alpha optimization evolution'},
  {t:'paper', title:'Slippage & Latency Modeling', sub:'Paper 09 — Execution', url:'paper-slippage-latency-modeling.html', kw:'slippage latency backtest execution market impact'},
  {t:'paper', title:'Alternate Data in Quant Finance', sub:'Paper 10 — Alt Data', url:'paper-alternative-data-quant-finance.html', kw:'alternate data satellite nowcasting'},
  {t:'paper', title:'HF Analytical Operations', sub:'Paper 11 — Analytics', url:'paper-hf-analytical-operations.html', kw:'vectorization gpu analytics rolling window feature engineering'},
  {t:'page', title:'Claude AI Trading', sub:'How LLMs are reshaping financial markets', url:'claude-ai-trading.html', kw:'claude ai trading bot llm finance agentic polymarket goldman sachs anthropic'},
  {t:'topic', title:'S&P 500', sub:'US Large Cap Index', url:'markets.html', kw:'spy spx sp500 s&p'},
  {t:'topic', title:'NASDAQ', sub:'Tech-Heavy Composite', url:'markets.html', kw:'nasdaq qqq tech'},
  {t:'topic', title:'Bitcoin & Crypto', sub:'Digital asset prices', url:'markets.html', kw:'bitcoin btc ethereum crypto kripto'},
  {t:'topic', title:'Gold & Commodities', sub:'Precious metals, oil, gas', url:'markets.html', kw:'gold altın oil petrol commodity emtia wti'},
  {t:'topic', title:'Forex', sub:'Currency exchange rates', url:'markets.html', kw:'forex döviz eur usd gbp currency'},
  {t:'topic', title:'VIX & Volatility', sub:'Fear index & volatility', url:'markets.html', kw:'vix volatility volatilite korku'},
];

let _searchActive = -1;
if(new URLSearchParams(location.search).has('search')) openSearch();
function openSearch(){
  document.getElementById('searchOverlay').classList.add('open');
  const inp = document.getElementById('searchInput');
  inp.value = '';
  inp.focus();
  document.getElementById('searchResults').innerHTML = '';
  document.getElementById('searchResults').className = 'search-results';
  _searchActive = -1;
}
function closeSearch(){
  document.getElementById('searchOverlay').classList.remove('open');
}
document.addEventListener('keydown', e => {
  if((e.key === 'k' && (e.metaKey || e.ctrlKey)) || (e.key === '/' && !['INPUT','TEXTAREA'].includes(document.activeElement?.tagName))){
    e.preventDefault(); openSearch();
  }
  if(e.key === 'Escape') closeSearch();
  if(!document.getElementById('searchOverlay').classList.contains('open')) return;
  const items = document.querySelectorAll('.sr-item');
  if(e.key === 'ArrowDown'){e.preventDefault();_searchActive=Math.min(_searchActive+1,items.length-1);items.forEach((el,i)=>el.classList.toggle('active',i===_searchActive));}
  if(e.key === 'ArrowUp'){e.preventDefault();_searchActive=Math.max(_searchActive-1,0);items.forEach((el,i)=>el.classList.toggle('active',i===_searchActive));}
  if(e.key === 'Enter' && _searchActive >= 0 && items[_searchActive]){items[_searchActive].click();}
});
document.getElementById('searchInput').addEventListener('input', function(){
  const q = this.value.trim().toLowerCase();
  const box = document.getElementById('searchResults');
  box.className = 'search-results' + (q ? ' has-query' : '');
  if(!q){box.innerHTML='';_searchActive=-1;return;}
  const matches = SEARCH_INDEX.filter(item => {
    const hay = (item.title + ' ' + item.sub + ' ' + item.kw).toLowerCase();
    return q.split(/\s+/).every(word => hay.includes(word));
  }).slice(0, 8);
  _searchActive = -1;
  box.innerHTML = matches.map(m =>
    `<a href="${m.url}" class="sr-item">
      <span class="sr-tag ${m.t}">${m.t}</span>
      <div><div class="sr-title">${m.title}</div><div class="sr-sub">${m.sub}</div></div>
    </a>`
  ).join('');
});

/* Deferred TradingView ticker — loads after LCP */
window.addEventListener('load', function(){
  setTimeout(function(){
    var w=document.getElementById('tickerWrap');
    if(!w)return;
    var c=document.createElement('div');c.className='tradingview-widget-container';
    var d=document.createElement('div');d.className='tradingview-widget-container__widget';
    c.appendChild(d);
    var s=document.createElement('script');s.type='text/javascript';s.async=true;
    s.src='https://s3.tradingview.com/external-embedding/embed-widget-ticker-tape.js';
    s.textContent=JSON.stringify({"symbols":[{"proName":"FOREXCOM:SPXUSD","title":"S&P 500"},{"proName":"FOREXCOM:NSXUSD","title":"Nasdaq 100"},{"description":"VIX","proName":"CBOE:VIX"},{"description":"AAPL","proName":"NASDAQ:AAPL"},{"description":"MSFT","proName":"NASDAQ:MSFT"},{"description":"NVDA","proName":"NASDAQ:NVDA"},{"description":"AMZN","proName":"NASDAQ:AMZN"},{"description":"META","proName":"NASDAQ:META"},{"description":"TSLA","proName":"NASDAQ:TSLA"},{"description":"GOOGL","proName":"NASDAQ:GOOGL"},{"description":"JPM","proName":"NYSE:JPM"},{"description":"V","proName":"NYSE:V"},{"description":"Gold","proName":"OANDA:XAUUSD"},{"description":"WTI","proName":"NYMEX:CL1!"},{"description":"BTC","proName":"BITSTAMP:BTCUSD"}],"showSymbolLogo":false,"colorTheme":"dark","isTransparent":true,"displayMode":"compact","locale":"en"});
    c.appendChild(s);w.appendChild(c);
  }, 2000);
});
