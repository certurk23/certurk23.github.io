"""
Fix v3: Same as v2 + add stale-on-429 fallback in yf()
        If Finnhub rate-limits (429), return last cached value instead of null
"""
import re, os

BASE = r'C:\Users\AI\Documents\github.io'

# ── New header block (replaces old Finnhub-based header) ─────────────────────
NEW_HEADER = """const FINNHUB_KEY='d6o5n7hr01qu09ci6v60d6o5n7hr01qu09ci6v6g';
const SYM_MAP={'GC=F':'GLD','SI=F':'SLV','CL=F':'USO','BZ=F':'BNO','NG=F':'UNG','HG=F':'CPER','DX-Y.NYB':'UUP','EURUSD=X':'__EUR','GBPUSD=X':'__GBP','BTC-USD':'__BTC'};
let _fx=null,_fxT=0,_yfc={},_yfp={};
async function loadFx(){if(_fx&&Date.now()-_fxT<60000)return _fx;try{const r=await fetch('https://open.er-api.com/v6/latest/USD',{signal:AbortSignal.timeout(8000)});const d=await r.json();_fx=d.rates;_fxT=Date.now();return _fx;}catch{return null;}}
"""

# ── New yf() with caching + deduplication ────────────────────────────────────
NEW_YF = """async function yf(sym){
  if(_yfc[sym]&&Date.now()-_yfc[sym].ts<55000)return _yfc[sym].v;
  if(_yfp[sym])return _yfp[sym];
  const p=(async()=>{
    const m=SYM_MAP[sym];let v=null;
    try{
      if(m==='__EUR'){const f=await loadFx();v=f?.EUR?{price:+(1/f.EUR).toFixed(5),chg:0,pts:0}:null;}
      else if(m==='__GBP'){const f=await loadFx();v=f?.GBP?{price:+(1/f.GBP).toFixed(5),chg:0,pts:0}:null;}
      else if(m==='__BTC'){const r=await fetch('https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd&include_24hr_change=true',{signal:AbortSignal.timeout(8000)});const d=await r.json();if(d.bitcoin){const p=d.bitcoin.usd,c=d.bitcoin.usd_24h_change||0;v={price:p,chg:c,pts:p*c/100};}}
      else{const fhSym=m||sym;const r=await fetch(`https://finnhub.io/api/v1/quote?symbol=${encodeURIComponent(fhSym)}&token=${FINNHUB_KEY}`,{signal:AbortSignal.timeout(8000)});if(r.status===429){delete _yfp[sym];return _yfc[sym]?.v??null;}if(r.ok){const d=await r.json();if(d.c&&d.c!==0)v={price:d.c,chg:d.dp||0,pts:d.d||0};}}
    }catch{}
    _yfc[sym]={v,ts:Date.now()};delete _yfp[sym];return v;
  })();
  return(_yfp[sym]=p);
}"""

def fix_page(filename):
    path = os.path.join(BASE, filename)
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    original = content
    changed = False

    # 1. Replace the entire header block (FINNHUB_KEY + SYM_MAP + vars + loadFx)
    #    Pattern: from FINNHUB_KEY line to end of loadFx function
    header_pattern = re.compile(
        r"const FINNHUB_KEY=.*?async function loadFx\(\)\{.*?\}\}",
        re.DOTALL
    )
    if header_pattern.search(content):
        content = header_pattern.sub(NEW_HEADER.strip(), content, count=1)
        changed = True
        print(f"  [OK] Replaced header+loadFx in {filename}")
    else:
        print(f"  [!!] Header pattern not found in {filename}")

    # 2. Replace yf() function
    yf_pattern = re.compile(
        r'async function yf\(sym\)\{.*?return null;\n\}',
        re.DOTALL
    )
    yf_pattern2 = re.compile(
        r'async function yf\(sym\)\{.*?return v;\s*\}\)\);\s*return\(_yfp\[sym\]=p\);\s*\}',
        re.DOTALL
    )
    yf_pattern_inline = re.compile(
        r'async function yf\(sym\)\{.*?return null;\}',
        re.DOTALL
    )

    if yf_pattern.search(content):
        content = yf_pattern.sub(NEW_YF, content, count=1)
        changed = True
        print(f"  [OK] Replaced yf() (multi-line) in {filename}")
    elif yf_pattern2.search(content):
        content = yf_pattern2.sub(NEW_YF, content, count=1)
        changed = True
        print(f"  [OK] Replaced yf() (already new format) in {filename}")
    elif yf_pattern_inline.search(content):
        content = yf_pattern_inline.sub(NEW_YF, content, count=1)
        changed = True
        print(f"  [OK] Replaced yf() (inline) in {filename}")
    else:
        print(f"  [!!] yf() not found in {filename}")

    if changed and content != original:
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"  [SAVED] {filename}")
    else:
        print(f"  [SKIP] No changes for {filename}")

pages = ['markets.html','stocks.html','research.html','papers.html','infrastructure.html','about.html']

print("=== Fix v3: stale-on-429 fallback ===\n")
for page in pages:
    print(f"Processing {page}...")
    fix_page(page)
    print()
print("=== Done ===")
