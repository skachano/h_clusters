"""Join soft-wrapped lines in Japanese Markdown so no stray spaces appear between CJK text.

Run after editing a Japanese page:

    python3 wiki/tools/join_ja.py wiki/pages/**/*.ja.md

A line is merged into the previous one when both are ordinary paragraph text of the
same block. Between Japanese characters (or next to Japanese punctuation) the line
break simply disappears; next to Latin text, code or math it becomes a space.
"""

import re
import sys
from pathlib import Path

BLOCK_START = re.compile(r"^(#|\||```|\$\$|!!!|\?\?\?|--8<--|>|[-*+] |\d+\. |</?[a-zA-Z])")


JA_PUNCT = set("、。，．・「」『』（）：；！？〜")


def no_space(left: str, right: str) -> bool:
    """Japanese joins without a space; Latin text, code and math keep one."""
    if left in JA_PUNCT or right in JA_PUNCT:
        return True
    return not left.isascii() and not right.isascii()


def is_block_start(stripped: str) -> bool:
    return bool(BLOCK_START.match(stripped))


def join(text: str) -> str:
    out: list[str] = []
    in_fence = in_math = False
    prev_joinable = False
    for line in text.split("\n"):
        stripped = line.strip()
        if stripped.startswith("```"):
            in_fence = not in_fence
            out.append(line)
            prev_joinable = False
            continue
        if not in_fence and stripped == "$$":
            in_math = not in_math
            out.append(line)
            prev_joinable = False
            continue
        if in_fence or in_math:
            out.append(line)
            continue
        if stripped and prev_joinable and not is_block_start(stripped):
            prev = out[-1].rstrip()
            # Look past emphasis markers: "*word*" next to Japanese needs no space either.
            space = "" if no_space(prev.rstrip("*_")[-1:], stripped.lstrip("*_")[:1]) else " "
            out[-1] = prev + space + stripped
            continue
        out.append(line)
        # A line can be continued if it is text: not empty, not a heading, table, fence,
        # callout title or snippet include.
        prev_joinable = bool(stripped) and not re.match(r"^(#|\||!!!|\?\?\?|--8<--)", stripped)
    return "\n".join(out)


for path in map(Path, sys.argv[1:]):
    path.write_text(join(path.read_text()))
