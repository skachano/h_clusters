"""Link the first mention of each cluster species on a page to its page in the web app.

Run after writing or editing a page (safe to run again; links already there count):

    python3 wiki/tools/link_species.py wiki/pages/**/*.md

H₃⁺ becomes [H₃⁺](app:s/3/1/1): size, charge and the ground spin state, which is the lowest
multiplicity for every H_m^n of the baseline (1 for an even electron count, 2 for odd), unless a
spin word stands right next to it ("triplet H₃⁺", "H₄⁻ quartet", "三重項の H⁻"). The bare
atom H and the proton H⁺ (not in the app) are left alone, and so is a species written as part of
a larger formula (H⁻(H₂)ₖ, H₃⁺·H₂). Headings, code, math, links and HTML are never touched.
"""

import re
import sys
from pathlib import Path

SUB = str.maketrans("₀₁₂₃₄₅₆₇₈₉", "0123456789")
# Not after or before letters, digits or formula glue; Japanese text around it is fine.
SPECIES = re.compile(r"(?<![A-Za-z0-9_\[·(/\-])H([₀-₉]+[⁺⁻]?|⁻)(?![A-Za-z0-9_₀-₉⁺⁻·(\]])")
# Spans to leave alone: inline code, inline math, Markdown links and images, HTML tags.
PROTECTED = re.compile(r"`[^`]*`|\$[^$]*\$|!?\[[^\]]*\]\([^)]*\)|<[^>]+>")
LINKED = re.compile(r"\]\(app:s/(\d+)/(-?\d+)/(\d+)\)")
SKIP_LINE = re.compile(r"^\s*(#|!!!|\?\?\?|--8<--|\*\[)")
SPIN = {"singlet": 1, "doublet": 2, "triplet": 3, "quartet": 4, "一重項": 1, "二重項": 2, "三重項": 3, "四重項": 4}
WORDS = "|".join(SPIN)
SPIN_BEFORE = re.compile(rf"({WORDS})の?\s*$")
SPIN_AFTER = re.compile(rf"^\s*\(?({WORDS})")


def multiplicity(match: re.Match, m: int, charge: int) -> int:
    """The spin state named next to the formula, else the ground state (the lowest)."""
    lowest = 1 if (m - charge) % 2 == 0 else 2
    word = SPIN_AFTER.match(match.string[match.end():]) or SPIN_BEFORE.search(match.string[:match.start()])
    named = SPIN[word[1]] if word else lowest
    return named if named % 2 == lowest % 2 else lowest


def route(match: re.Match) -> str | None:
    """The app route of a formula like H₃⁺, or None for H⁺ and the bare atom."""
    digits, sign = match[1].rstrip("⁺⁻"), match[1][-1] if match[1][-1] in "⁺⁻" else ""
    m = int(digits.translate(SUB)) if digits else 1
    charge = {"⁺": 1, "⁻": -1, "": 0}[sign]
    if m == 1 and charge != -1:
        return None
    return f"s/{m}/{charge}/{multiplicity(match, m, charge)}"


def link_text(text: str, seen: set[str]) -> str:
    def replace(match: re.Match) -> str:
        target = route(match)
        if target is None or target in seen:
            return match[0]
        seen.add(target)
        return f"[{match[0]}](app:{target})"

    out, last = [], 0
    for span in PROTECTED.finditer(text):
        out += [SPECIES.sub(replace, text[last:span.start()]), span[0]]
        last = span.end()
    out.append(SPECIES.sub(replace, text[last:]))
    return "".join(out)


def link(text: str) -> str:
    seen = {f"s/{m}/{c}/{mult}" for m, c, mult in LINKED.findall(text)}
    out, in_fence, in_math = [], False, False
    for line in text.split("\n"):
        stripped = line.strip()
        if stripped.startswith("```"):
            in_fence = not in_fence
        elif not in_fence and stripped == "$$":
            in_math = not in_math
        elif not (in_fence or in_math or SKIP_LINE.match(line)):
            line = link_text(line, seen)
        out.append(line)
    return "\n".join(out)


if __name__ == "__main__":
    for name in sys.argv[1:]:
        path = Path(name)
        if path.stem.startswith("writing-pages"):  # its examples are about the syntax
            continue
        text = path.read_text()
        if (new := link(text)) != text:
            path.write_text(new)
            print(f"linked {path}")
