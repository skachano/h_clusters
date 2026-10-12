"""Links from the wiki into the web app: `[H₅⁺](app:s/5/1/1)` opens that species page.

The target is the app's route without the campaign: `app:s/5/1/1`, `app:trends`, or `app:`
for the grid; `app:c/<campaign>/...` picks another campaign than baseline. APP_URL is where
the app's routes start: the dev server by default, `/h_clusters/#/` on GitHub Pages (its
routes live in the hash). Japanese pages add `?lang=ja` so the app opens in Japanese.

Rewritten in the finished HTML, so links in the navigation (`- Open the app: "app:"` in
mkdocs.yml) work too; MkDocs sees `app:` as an external scheme and does not validate it, so
species routes are checked here against the baseline's states (H_m^n, m = 1-10, n = -1, 0, +1,
the two lowest spin states): a wrong one is a warning, which fails `build --strict`.
"""

import logging
import os
import re

APP_URL = os.environ.get("APP_URL", "http://localhost:5173/")
CAMPAIGN = "baseline"

HREF = re.compile(r'href="app:([^"#?]*)(\?[^"#]*)?(#[^"]*)?"')
SPECIES = re.compile(r"(?:c/[^/]+/)?s/(\d+)/(-?\d+)/(\d+)")
log = logging.getLogger("mkdocs.hooks.app_links")


def species_exists(m: int, charge: int, mult: int) -> bool:
    electrons = m - charge
    lowest = 1 if electrons % 2 == 0 else 2
    return (1 <= m <= 10 and -1 <= charge <= 1 and electrons > 0
            and mult in (lowest, lowest + 2) and mult <= electrons + 1)


def app_href(path: str, query: str, fragment: str, lang: str) -> str:
    if not path.startswith("c/"):
        path = f"c/{CAMPAIGN}/{path}".rstrip("/")
    if lang != "en":
        query = f"{query}&lang={lang}" if query else f"?lang={lang}"
    return f"{APP_URL}{path}{query}{fragment}"


def on_post_page(output: str, page, config) -> str:
    # The i18n plugin builds each language into its own folder: ja/... for Japanese.
    lang = "ja" if page.file.dest_uri.startswith("ja/") else "en"
    for m in HREF.finditer(output):
        if (s := SPECIES.fullmatch(m[1])) and not species_exists(*map(int, s.groups())):
            log.warning("%s: app:%s is not a state of the app", page.file.src_uri, m[1])
    return HREF.sub(lambda m: f'href="{app_href(m[1], m[2] or "", m[3] or "", lang)}"', output)
