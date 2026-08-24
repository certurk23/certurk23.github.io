"""Stop stating, as fact, that this site is funded by Google AdSense.

It is not. The AdSense application has not been approved, so every sentence
written in the present tense about ad revenue was false at the moment a
reviewer would read it - and a reviewer reading "Advertising, served by Google
AdSense" on a site whose application is pending sees a claim they know to be
untrue. That is a worse trust signal than having no funding section at all.

What is actually true, and all that is now claimed:

  - the site currently earns nothing
  - an application to Google AdSense has been submitted and is pending
  - if approved, ads may appear, and this page will be updated to say so
  - there are no sponsorships, affiliate links or paid placements of any kind

The AdSense script tag stays in the markup: serving it is how the application
is reviewed in the first place. What changes is the prose around it.

Also fixed here: about.html described a "non-commercial mandate" while the site
was applying to run advertising. The footer badge saying the same thing was
corrected in an earlier pass; this is the prose that was missed.

Idempotent.
"""
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent

EDITS = [
    # ---- editorial-policy.html: the funding section -----------------------
    ('editorial-policy.html',
     '<p>Advertising, served by Google AdSense. Advertisers have no input into\n'
     'research topics, conclusions or the timing of publication, and no advertiser is\n'
     'shown the content in advance. Ad revenue does not depend on any particular\n'
     'conclusion.</p>',
     '<p><strong>QuantMedia currently generates no revenue.</strong> There are no '
     'sponsorships, no paid placements, no affiliate links and no paid '
     'subscriptions, and nothing on this site has ever been written for payment.</p>\n'
     '<p>An application to Google AdSense has been submitted and is pending. If it '
     'is approved, advertising may appear on this site in future, and this page '
     'will be updated to say so plainly. No other form of monetisation is planned '
     'at present.</p>\n'
     '<p>Whatever funding arrives later, the rule is fixed in advance: advertisers '
     'get no input into research topics, conclusions or publication timing, they '
     'are never shown content ahead of readers, and no revenue arrangement will '
     'depend on reaching any particular conclusion. Any change to this will be '
     'disclosed here before it takes effect, not after.</p>'),

    # ---- editorial-policy.html: privacy paragraph -------------------------
    ('editorial-policy.html',
     '<p>QuantMedia uses Google Analytics 4 for aggregate traffic measurement and\n'
     'Google AdSense for advertising. No accounts, logins or personal profiles are\n'
     'collected by this site. Details are in the\n'
     '<a href="/privacy.html">privacy policy</a>.</p>',
     '<p>QuantMedia uses Google Analytics 4 for aggregate traffic measurement. '
     'Google AdSense code is present because an application is pending; should it '
     'be approved, advertising cookies would apply as described in the '
     '<a href="/privacy.html">privacy policy</a>. No accounts, logins or personal '
     'profiles are collected by this site.</p>'),

    # ---- privacy.html: cookie list ----------------------------------------
    ('privacy.html',
     '<li><strong>Advertising cookies</strong> — to serve relevant ads and measure '
     'ad performance (via Google AdSense)</li>',
     '<li><strong>Advertising cookies</strong> — if and when Google AdSense serves '
     'ads on this Site, to deliver and measure them. An AdSense application is '
     'pending; no ads are being served at the time of writing.</li>'),

    # ---- about.html: the contradicting mandate ----------------------------
    ('about.html',
     'This research environment operates under an <strong>independent, '
     'non-commercial</strong> mandate.',
     'QuantMedia is <strong>independently operated and unaffiliated</strong> with '
     'any fund, broker, exchange or data vendor. It currently earns no revenue; an '
     'advertising application is pending, and the '
     '<a href="/editorial-policy.html">editorial policy</a> sets out what would and '
     'would not change if it were approved.'),
]

# Nothing on the site may state ad serving as a present fact.
BANNED = [
    ('editorial-policy.html', 'Advertising, served by Google AdSense'),
    ('editorial-policy.html', 'Google AdSense for advertising'),
    ('about.html', 'non-commercial</strong> mandate'),
    ('privacy.html', 'to serve relevant ads and measure ad performance'),
]


def main():
    changed = missing = 0
    for rel, old, new in EDITS:
        p = ROOT / rel
        if not p.exists():
            print(f'  MISSING FILE {rel}')
            missing += 1
            continue
        s = p.read_text(encoding='utf-8')
        if new in s:
            print(f'  [  -] {rel}: already applied')
            continue
        if old not in s:
            print(f'  [MISS] {rel}: {old[:62]}...')
            missing += 1
            continue
        p.write_text(s.replace(old, new, 1), encoding='utf-8')
        changed += 1
        print(f'  [chg] {rel}: {old[:58]}...')

    print(f'\n{changed} applied, {missing} not matched')

    fail = False
    for rel, needle in BANNED:
        if needle in (ROOT / rel).read_text(encoding='utf-8'):
            print(f'  STILL PRESENT  {rel}: {needle!r}')
            fail = True
    print('verified: no page states AdSense revenue as a present fact'
          if not fail else 'FAILED')
    sys.exit(1 if (fail or missing) else 0)


if __name__ == '__main__':
    main()
