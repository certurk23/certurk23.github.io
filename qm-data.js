/* ===========================================================================
   QuantMedia shared data layer
   ---------------------------------------------------------------------------
   Every page reads pre-rendered snapshots from /data/*.json, written by the
   nightly pipeline (scripts/daily_update.py). Two hard rules live here:

   1. No API keys in the browser. This file calls the site's own origin only.
   2. Freshness is DERIVED from the snapshot timestamp, never asserted. If the
      pipeline stops, pages degrade to "Data feed paused - last snapshot ..."
      instead of continuing to claim they are live.
   =========================================================================== */
window.QM = (function () {
  'use strict';

  var cache = {};

  function get(name) {
    if (cache[name]) return cache[name];
    cache[name] = fetch('data/' + name + '.json', { cache: 'no-cache' })
      .then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); })
      .catch(function () { return null; });
    return cache[name];
  }

  /* Hours elapsed since an ISO-8601 Z timestamp. */
  function hoursSince(iso) {
    if (!iso) return Infinity;
    var t = Date.parse(iso);
    return isNaN(t) ? Infinity : (Date.now() - t) / 36e5;
  }

  /* Both halves must be UTC. Formatting the date in the viewer's local zone
     while labelling the clock "UTC" printed things like "Apr 14 ... 22:33 UTC"
     for a timestamp that was actually 22:33 on Apr 13. */
  function fmtDate(iso) {
    var d = new Date(iso);
    if (isNaN(d)) return 'unknown';
    return d.toLocaleDateString('en-US', {
      timeZone: 'UTC', month: 'short', day: 'numeric', year: 'numeric'
    }) + ', ' + d.toISOString().slice(11, 16) + ' UTC';
  }

  /* The single place that decides how fresh a feed is allowed to look.
     Returns {state, label, cls} where state is fresh | recent | delayed | paused. */
  function freshness(iso, prefix) {
    var h = hoursSince(iso);
    prefix = prefix || 'Data snapshot';
    if (h === Infinity) {
      return { state: 'paused', cls: 'qm-stale',
               label: 'Snapshot date unavailable' };
    }
    if (h < 20) {
      return { state: 'fresh', cls: 'qm-fresh',
               label: prefix + ': ' + fmtDate(iso) };
    }
    if (h < 96) {
      return { state: 'recent', cls: 'qm-fresh',
               label: prefix + ': ' + fmtDate(iso) };
    }
    if (h < 24 * 14) {
      return { state: 'delayed', cls: 'qm-warn',
               label: 'Delayed - last snapshot ' + fmtDate(iso) };
    }
    return { state: 'paused', cls: 'qm-stale',
             label: 'Data feed paused - last snapshot ' + fmtDate(iso) +
                    '. Reference content below remains accurate.' };
  }

  /* Writes the freshness line into an element and tags it for styling. */
  function stamp(el, iso, prefix) {
    if (typeof el === 'string') el = document.getElementById(el);
    if (!el) return null;
    var f = freshness(iso, prefix);
    el.textContent = f.label;
    el.classList.remove('qm-fresh', 'qm-warn', 'qm-stale');
    el.classList.add(f.cls);
    el.setAttribute('data-state', f.state);
    return f;
  }

  var fmtNum = function (n, d) {
    if (n == null || isNaN(n)) return '--';
    d = d == null ? 2 : d;
    return n.toLocaleString('en-US',
      { minimumFractionDigits: d, maximumFractionDigits: d });
  };

  /* Site-wide freshness banner.
     Reads /data/status.json (written by the pipeline) and, if the data feed
     has stalled, states that once at the top of the page. This is the safety
     net that stops the site implying currency when the pipeline is down:
     even if an individual widget forgets to degrade, this does not. */
  function freshnessBanner() {
    if (document.getElementById('qm-freshness-banner')) return;   // idempotent
    // Only speak up on pages that actually display market data. Warning about
    // a stalled feed on a page with no feed on it is just noise, and noise
    // trains people to ignore the banner when it matters.
    var showsData = document.getElementById('mbarItems') ||
                    document.getElementById('marketBar') ||
                    document.getElementById('lastUp') ||
                    document.getElementById('newsStatus') ||
                    document.getElementById('signalTableWrap');
    if (!showsData) return;
    get('status').then(function (s) {
      if (!s) return;
      if (document.getElementById('qm-freshness-banner')) return;
      var worst = [s.markets_status, s.news_status, s.signals_status];
      // Only 'delayed' and 'paused' speak up. 'fresh' and 'recent' stay
      // silent: a banner that cries wolf on a normal weekend trains users
      // to ignore it, which defeats the point.
      if (worst.indexOf('paused') === -1 && worst.indexOf('delayed') === -1) return;

      var paused = worst.indexOf('paused') !== -1;
      var when = s.signals_market_date || s.last_pipeline_run || '';
      var bar = document.createElement('div');
      bar.id = 'qm-freshness-banner';
      bar.setAttribute('role', 'status');
      bar.style.cssText =
        'padding:8px 16px;font-family:inherit;font-size:12.5px;line-height:1.6;' +
        'text-align:center;border-bottom:1px solid;' +
        (paused
          ? 'background:#3a1d1d;border-color:#5c2b2b;color:#ffb4b4;'
          : 'background:#3a331d;border-color:#5c522b;color:#ffe0a3;');
      bar.textContent = paused
        ? 'Automated data updates are currently paused. Figures below are the ' +
          'last captured snapshot (' + when + ') and are not current. ' +
          'Reference and research content is unaffected.'
        : 'Market data updates are running behind. Figures below are the last ' +
          'captured snapshot (' + when + '), not live prices.';

      var host = document.querySelector('.market-bar') ||
                 document.querySelector('header') || document.body.firstChild;
      if (host && host.parentNode) host.parentNode.insertBefore(bar, host.nextSibling);
      else document.body.insertBefore(bar, document.body.firstChild);
    });
  }

  /* Market bar: renders from the snapshot, or removes itself entirely rather
     than sitting there full of dashes. */
  function marketBar(containerId, labelId) {
    var box = document.getElementById(containerId);
    if (!box) return;
    get('markets_bar').then(function (feed) {
      var rows = feed && feed.data;
      if (!rows || !rows.length) {
        var wrap = box.closest('.market-bar') || box.parentNode;
        if (wrap && wrap.style) wrap.style.display = 'none';
        return;
      }
      box.innerHTML = rows.map(function (r) {
        var c = r.c > 0 ? 'up' : r.c < 0 ? 'dn' : 'nt';
        var dec = Math.abs(r.p) >= 100 ? 2 : 4;
        return '<div class="mbar-item"><span class="mbar-sym">' + r.l +
               '</span><span class="mbar-val">' + fmtNum(r.p, dec) +
               '</span><span class="mbar-chg ' + c + '">' +
               (r.c > 0 ? '+' : '') + fmtNum(r.c) + '%</span></div>';
      }).join('');
      var lab = labelId && document.getElementById(labelId);
      if (lab) {
        var f = freshness(feed.fetched_utc);
        lab.textContent = f.state === 'fresh' || f.state === 'recent'
          ? 'Last close' : 'Delayed';
        lab.title = f.label;
      }
    });
  }

  // Fire the banner check on every page that loads this file.
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', freshnessBanner);
  } else {
    freshnessBanner();
  }

  return {
    get: get,
    freshness: freshness,
    stamp: stamp,
    fmtDate: fmtDate,
    fmtNum: fmtNum,
    hoursSince: hoursSince,
    marketBar: marketBar,
    freshnessBanner: freshnessBanner
  };
})();
