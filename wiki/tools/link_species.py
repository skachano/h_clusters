"""Link every mention of a cluster species on a page to its page in the web app.

Run after writing or editing a page (safe to run again: links already there are left alone):

    python3 wiki/tools/link_species.py wiki/pages/**/*.md

H₃⁺ becomes [H₃⁺](app:s/3/1/1): size, charge and the ground spin state, which is the lowest
multiplicity for every H_m^n of the baseline (1 for an even electron count, 2 for odd), unless a
spin word stands right next to it ("triplet H₃⁺", "H₄⁻ quartet", "三重項の H⁻"). A formula made
of several units links as a whole to the species they add up to: (H₂)₂, H₂·H, H₃⁺·H₂, H⁻(H₂)₄,
(H₂H₂H₂)⁺. So does a sum written with +, the products or the reactants of a channel: H₃⁺ + H₂
and H₄⁺ + H open H₅⁺, also when its terms were linked one by one before. Left alone: the bare atom H and the proton H⁺ (not in the app), families with a
variable count such as H⁻(H₂)ₖ, sums outside the app's grid, and headings, code, math, links
and HTML.
"""

import re
import sys
from dataclasses import dataclass
from pathlib import Path

SUB = str.maketrans("₀₁₂₃₄₅₆₇₈₉", "0123456789")
DIGITS = "₀₁₂₃₄₅₆₇₈₉"
VARIABLE = "ₖₙₘₓ"  # a subscript letter: a family of species, not one
SIGN = {"⁺": 1, "⁻": -1}
# A formula does not start after, or end before, letters, digits or formula glue; Japanese
# text around it is fine.
NOT_BEFORE = set("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_[·/-⁺⁻" + DIGITS)
NOT_AFTER = set("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_]·(⁺⁻" + DIGITS + VARIABLE)
# Spans to leave alone: inline code, inline math, Markdown links and images, HTML tags.
PROTECTED = re.compile(r"`[^`]*`|\$[^$]*\$|!?\[[^\]]*\]\([^)]*\)|<[^>]+>")
# A species link already on the page, which can be a term of a sum.
APP_LINK = re.compile(r"\[([^\]]+)\]\(app:s/[-\d/]+\)")
PLUS = " + "
SKIP_LINE = re.compile(r"^\s*(#|!!!|\?\?\?|--8<--|\*\[)")
SPIN = {"singlet": 1, "doublet": 2, "triplet": 3, "quartet": 4, "一重項": 1, "二重項": 2, "三重項": 3, "四重項": 4}
WORDS = "|".join(SPIN)
SPIN_BEFORE = re.compile(rf"({WORDS})の?\s*$")
SPIN_AFTER = re.compile(rf"^\s*\(?({WORDS})")


@dataclass
class Formula:
    end: int  # index after the formula
    m: int = 0
    charge: int = 0
    units: int = 0
    family: bool = False  # a variable count somewhere: (H₂)ₖ


def _subscript(text: str, i: int) -> tuple[int, int | None]:
    """The subscript number at i (None if there is none) and the index after it."""
    j = i
    while j < len(text) and text[j] in DIGITS:
        j += 1
    return j, int(text[i:j].translate(SUB)) if j > i else None


def parse(text: str, i: int) -> Formula | None:
    """The formula at i: units like H₂ or H₃⁺, side by side or joined by · or ···, groups (…)₂,
    (…)⁺ or (…)ₖ. Plain parentheses, with no count or charge after them, end it."""
    f = Formula(i)
    while True:
        glue = next((g for g in ("···", "·") if f.units and text.startswith(g, i)), "")
        j = i + len(glue)
        if text[j:j + 1] == "H":
            j, size = _subscript(text, j + 1)
            f.m += size or 1
            f.units += 1
        elif text[j:j + 1] == "(":
            inner = parse(text, j + 1)
            if inner is None or text[inner.end:inner.end + 1] != ")":
                break
            j = inner.end + 1
            if text[j:j + 1] in VARIABLE and j < len(text):
                j, times, f.family = j + 1, 1, True
            else:
                j, times = _subscript(text, j)
            if times is None and text[j:j + 1] not in SIGN:
                break  # plain parentheses
            f.m += inner.m * (times or 1)
            f.charge += inner.charge * (times or 1)
            f.units += 2
            f.family |= inner.family
        else:
            break
        if text[j:j + 1] in SIGN:
            f.charge += SIGN[text[j]]
            j += 1
        i = f.end = j
    return f if f.units else None


def multiplicity(text: str, start: int, end: int, m: int, charge: int) -> int:
    """The spin state named next to the formula, else the ground state (the lowest)."""
    lowest = 1 if (m - charge) % 2 == 0 else 2
    word = SPIN_AFTER.match(text[end:]) or SPIN_BEFORE.search(text[:start])
    named = SPIN[word[1]] if word else lowest
    return named if named % 2 == lowest % 2 else lowest


def route(text: str, start: int, f: Formula) -> str | None:
    """The app route of a formula, or None when it is no single state of the app."""
    electrons = f.m - f.charge
    if f.family or not (1 <= f.m <= 10 and -1 <= f.charge <= 1 and electrons > 0):
        return None
    if f.m == 1 and f.charge != -1:
        return None
    mult = multiplicity(text, start, f.end, f.m, f.charge)
    return f"s/{f.m}/{f.charge}/{mult}" if mult <= electrons + 1 else None


def link_species(text: str) -> str:
    out, i = [], 0
    while i < len(text):
        f = None
        if text[i] in "H(" and (i == 0 or text[i - 1] not in NOT_BEFORE):
            f = parse(text, i)
        if f is None:
            out.append(text[i])
            i += 1
            continue
        target = None if text[f.end:f.end + 1] in NOT_AFTER and f.end < len(text) else route(text, i, f)
        out.append(text[i:f.end] if target is None else f"[{text[i:f.end]}](app:{target})")
        i = f.end
    return "".join(out)


def term(text: str, i: int) -> tuple[str, Formula] | None:
    """The term of a sum at i, a formula or a species link, as its label and formula (its end in
    text)."""
    if (a := APP_LINK.match(text, i)) is not None:
        f = parse(a[1], 0)
        if f is None or f.end != len(a[1]):
            return None
        f.end = a.end()
        return a[1], f
    if text[i] not in "H(" or (i > 0 and text[i - 1] in NOT_BEFORE):
        return None
    f = parse(text, i)
    if f is None or (f.end < len(text) and text[f.end] in NOT_AFTER):
        return None
    return text[i:f.end], f


def link_sums(text: str) -> str:
    """Link every sum of formulas, H₃⁺ + H₂, whole to the species it adds up to."""
    out, i = [], 0
    while i < len(text):
        first = term(text, i)
        if first is None:
            span = PROTECTED.match(text, i)
            j = span.end() if span else i + 1
            out.append(text[i:j])
            i = j
            continue
        labels, total = [first[0]], Formula(first[1].end, first[1].m, first[1].charge, 1, first[1].family)
        while text.startswith(PLUS, total.end) and (t := term(text, total.end + len(PLUS))) is not None:
            labels.append(t[0])
            total.m += t[1].m
            total.charge += t[1].charge
            total.family |= t[1].family
            total.end = t[1].end
        target = route(text, i, total) if len(labels) > 1 else None
        # A single term, or a sum that is no species of the app, is left to link_species.
        out.append(text[i:total.end] if target is None else f"[{PLUS.join(labels)}](app:{target})")
        i = total.end
    return "".join(out)


def link_text(text: str) -> str:
    text = link_sums(text)
    out, last = [], 0
    for span in PROTECTED.finditer(text):
        out += [link_species(text[last:span.start()]), span[0]]
        last = span.end()
    out.append(link_species(text[last:]))
    return "".join(out)


def link(text: str) -> str:
    out, in_fence, in_math = [], False, False
    for line in text.split("\n"):
        stripped = line.strip()
        if stripped.startswith("```"):
            in_fence = not in_fence
        elif not in_fence and stripped == "$$":
            in_math = not in_math
        elif not (in_fence or in_math or SKIP_LINE.match(line)):
            line = link_text(line)
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
