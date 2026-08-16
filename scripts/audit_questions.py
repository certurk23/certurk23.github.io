#!/usr/bin/env python3
"""
Question-coverage audit.
========================
Scores every question in scripts/ai_queries.py against the ACTUAL visible text
of its target page, then writes two artifacts:

    data/ai_query_intelligence.json   the opportunity map (gaps, scores, status)
    data/ai_citation_benchmark.json   benchmark prompts for visibility testing

    python scripts/audit_questions.py

Why measure rather than assert. It would be easy to hand-write "answer quality:
7" for every question and call it an audit. Instead each question carries
`markers` - phrases that must actually appear in the rendered text - so the
score reflects what the page says. A missing marker is a real, checkable gap.

Pure standard library so it runs in CI alongside the other checks.
"""

from __future__ import annotations

import html as html_mod
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import ai_queries as AQ   # noqa: E402

SITE = 'https://quantmedia.io'

SCRIPT_RE = re.compile(r'<script\b.*?</script>', re.DOTALL | re.I)
STYLE_RE = re.compile(r'<style\b.*?</style>', re.DOTALL | re.I)
COMMENT_RE = re.compile(r'<!--.*?-->', re.DOTALL)
TAG_RE = re.compile(r'<[^>]+>')
WS_RE = re.compile(r'\s+')


def visible_text(rel):
    """Text a crawler or assistant sees WITHOUT running JavaScript.

    Scripts, styles and comments are stripped deliberately: content that only
    exists inside them does not count as answered.
    """
    path = os.path.join(ROOT, rel.lstrip('/'))
    if not os.path.exists(path):
        return None
    raw = open(path, encoding='utf-8', errors='replace').read()
    raw = COMMENT_RE.sub(' ', STYLE_RE.sub(' ', SCRIPT_RE.sub(' ', raw)))
    text = html_mod.unescape(TAG_RE.sub(' ', raw))
    return WS_RE.sub(' ', text).lower()


def headings(rel):
    path = os.path.join(ROOT, rel.lstrip('/'))
    if not os.path.exists(path):
        return []
    raw = open(path, encoding='utf-8', errors='replace').read()
    raw = SCRIPT_RE.sub(' ', raw)
    return [WS_RE.sub(' ', html_mod.unescape(TAG_RE.sub(' ', m.group(1)))).strip().lower()
            for m in re.finditer(r'<h[1-4][^>]*>(.*?)</h[1-4]>', raw, re.DOTALL | re.I)]


def score(rec):
    """0-10 coverage score for one question.

    6 pts  proportion of markers present in the visible text
    2 pts  a heading closely matching the question (answer-first structure)
    2 pts  the page exists and carries real depth (>1,500 chars of text)
    """
    text = visible_text(rec['target_url'])
    if text is None:
        return 0, 'page does not exist', []

    missing = [m for m in rec['markers'] if m not in text]
    hit_ratio = 1.0 - (len(missing) / max(1, len(rec['markers'])))
    pts = 6.0 * hit_ratio

    # Heading proximity: do meaningful words from the question appear together
    # in any heading? Cheap proxy for "the answer is easy to locate".
    words = [w for w in re.findall(r'[a-z]{4,}', rec['question'].lower())
             if w not in ('what', 'does', 'mean', 'this', 'that', 'with', 'from',
                          'have', 'many', 'much', 'should', 'there', 'which',
                          'quantmedia', 'your')]
    hs = headings(rec['target_url'])
    matched_heading = any(sum(w in h for w in words) >= max(1, len(words) // 2)
                          for h in hs) if words else False
    if matched_heading:
        pts += 2.0

    if len(text) > 1500:
        pts += 2.0

    gap = ''
    if missing:
        gap = 'missing: ' + ', '.join(repr(m) for m in missing[:3])
        if len(missing) > 3:
            gap += f' (+{len(missing) - 3} more)'
    elif not matched_heading:
        gap = 'answered in body but no matching heading - harder to extract'

    return round(min(pts, 10.0), 1), gap, missing


def status_for(s, rec):
    if s == 0:
        return 'missing-page'
    if s < 5:
        return 'gap'
    if s < 8:
        return 'needs-improvement'
    return 'covered'


def main():
    print('=' * 74)
    print('QuantMedia AI question-coverage audit')
    print('=' * 74)

    records, by_topic = [], {}
    for rec in AQ.Q:
        s, gap, missing = score(rec)
        st = status_for(s, rec)
        out = {
            'topic': rec['topic'],
            'question': rec['question'],
            'intent': rec['intent'],
            'target_url': rec['target_url'],
            'priority': rec['priority'],
            'primary_source': rec['primary_source'],
            'answer_coverage_score': s,
            'status': st,
            'content_gap': gap or None,
            'notes': rec['notes'] or None,
        }
        records.append(out)
        by_topic.setdefault(rec['topic'], []).append(out)

    # ---- report -----------------------------------------------------------
    print(f"\n{'topic':<20}{'n':>4}{'avg':>7}{'covered':>9}{'needs':>7}{'gap':>6}{'missing':>9}")
    for topic in sorted(by_topic):
        rs = by_topic[topic]
        avg = sum(r['answer_coverage_score'] for r in rs) / len(rs)
        c = sum(r['status'] == 'covered' for r in rs)
        n = sum(r['status'] == 'needs-improvement' for r in rs)
        g = sum(r['status'] == 'gap' for r in rs)
        m = sum(r['status'] == 'missing-page' for r in rs)
        print(f'{topic:<20}{len(rs):>4}{avg:>7.1f}{c:>9}{n:>7}{g:>6}{m:>9}')

    weak = sorted((r for r in records if r['answer_coverage_score'] < 8),
                  key=lambda r: (r['answer_coverage_score'],
                                 {'high': 0, 'medium': 1, 'low': 2}[r['priority']]))
    print(f'\n{len(weak)} question(s) scoring below 8:')
    for r in weak[:25]:
        print(f"  {r['answer_coverage_score']:>4}  [{r['priority']:<6}] "
              f"{r['question'][:52]:<54} {r['content_gap'] or ''}")

    # ---- artifacts --------------------------------------------------------
    intel = {
        'generated_by': 'scripts/audit_questions.py from scripts/ai_queries.py',
        'what_this_is': (
            'Internal map of natural-language questions QuantMedia aims to '
            'answer well, scored against the actual visible text of each '
            'target page. Scores are measured, not estimated.'),
        'not_search_volume': (
            'These are benchmark prompts. No per-question ChatGPT, Gemini or '
            'Google volume is claimed anywhere in this file, because none is '
            'publicly available.'),
        'scoring': {
            'markers': '6 pts, proportion of required phrases present',
            'heading': '2 pts, a heading closely matching the question',
            'depth': '2 pts, target page carries substantive text',
        },
        'totals': {
            'topics': len(by_topic),
            'questions': len(records),
            'covered': sum(r['status'] == 'covered' for r in records),
            'needs_improvement': sum(r['status'] == 'needs-improvement' for r in records),
            'gaps': sum(r['status'] == 'gap' for r in records),
            'missing_pages': sum(r['status'] == 'missing-page' for r in records),
            'primary_source_questions': sum(r['primary_source'] for r in records),
        },
        'questions': records,
    }
    with open(os.path.join(ROOT, 'data', 'ai_query_intelligence.json'), 'w',
              encoding='utf-8') as f:
        json.dump(intel, f, indent=1, ensure_ascii=False)

    bench = {
        'what_this_is': (
            'Benchmark prompts for periodic manual visibility testing against '
            'ChatGPT, Gemini, Copilot and Perplexity. See '
            'docs/ai-visibility-testing.md for the procedure.'),
        'not_search_volume': 'These are test prompts, not measured demand.',
        'count': len(records),
        'questions': [{
            'question': r['question'],
            'topic': r['topic'],
            'expected_quantmedia_url': SITE + r['target_url'],
            'priority': r['priority'],
            'primary_source': r['primary_source'],
            'notes': r['notes'],
        } for r in records],
    }
    with open(os.path.join(ROOT, 'data', 'ai_citation_benchmark.json'), 'w',
              encoding='utf-8') as f:
        json.dump(bench, f, indent=1, ensure_ascii=False)

    print(f"\nwrote data/ai_query_intelligence.json  ({len(records)} questions)")
    print(f"wrote data/ai_citation_benchmark.json  ({len(records)} prompts)")
    return 0


if __name__ == '__main__':
    sys.exit(main())
