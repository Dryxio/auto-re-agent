"""Text analysis utilities for C++ source and assembly."""
from __future__ import annotations

import re

# ---------------------------------------------------------------------------
# Compiled regex patterns
# ---------------------------------------------------------------------------

COMMENT_BLOCK_RE: re.Pattern[str] = re.compile(r"/\*.*?\*/", re.S)
COMMENT_LINE_RE: re.Pattern[str] = re.compile(r"//.*")
TOKEN_CALL_RE: re.Pattern[str] = re.compile(r"\b([A-Za-z_][A-Za-z0-9_:]*)\s*\(")
CONTROL_FLOW_RE: re.Pattern[str] = re.compile(r"\b(if|for|while|switch|do|goto)\b")
ASM_LINE_RE: re.Pattern[str] = re.compile(r"^[0-9a-fA-F]{8}\s+([A-Z]+)")

# ---------------------------------------------------------------------------
# Token sets
# ---------------------------------------------------------------------------

CPP_KEYWORDS: set[str] = {
    "if",
    "for",
    "while",
    "switch",
    "return",
    "sizeof",
    "alignof",
    "decltype",
    "static_cast",
    "reinterpret_cast",
    "const_cast",
    "dynamic_cast",
    "catch",
    "new",
    "delete",
}

FP_SOURCE_TOKENS: tuple[str, ...] = (
    "std::sin",
    "std::cos",
    "std::tan",
    "std::sqrt",
    "std::pow",
    "std::asin",
    "std::acos",
    "std::atan",
    "std::atan2",
    "std::fabs",
    "std::abs",
    "std::ceil",
    "std::floor",
    "std::isnan",
    "std::isfinite",
    "std::copysign",
    "sin(",
    "cos(",
    "sqrt(",
    "atan2(",
    "fabs(",
)

FP_ASM_PREFIXES: tuple[str, ...] = (
    "FCOM",
    "FUCOM",
    "FSIN",
    "FCOS",
    "FPTAN",
    "FPATAN",
    "FSQRT",
    "FDIV",
    "FMUL",
    "FADD",
    "FSUB",
    "FABS",
    "FRNDINT",
    "FNSTSW",
)


# ---------------------------------------------------------------------------
# Functions
# ---------------------------------------------------------------------------

def strip_comments(text: str) -> str:
    """Remove both block (``/* ... */``) and line (``// ...``) comments from C++ source."""
    return COMMENT_LINE_RE.sub("", COMMENT_BLOCK_RE.sub("", text))


def count_calls(
    body_no_comments: str,
    stub_call_prefix: str = "plugin::Call",
) -> tuple[int, int, int]:
    """Count function calls in comment-stripped C++ source.

    Args:
        body_no_comments: Source text with comments already removed.
        stub_call_prefix: Prefix used to identify stub/plugin calls.

    Returns:
        A tuple of ``(total_calls, plugin_calls, non_plugin_calls)``.
    """
    total = 0
    plugin = 0
    non_plugin = 0
    for m in TOKEN_CALL_RE.finditer(body_no_comments):
        tok = m.group(1)
        if tok in CPP_KEYWORDS:
            continue
        if tok.endswith("::operator") or tok == "operator":
            continue
        total += 1
        if tok.startswith(stub_call_prefix):
            plugin += 1
        else:
            non_plugin += 1
    return total, plugin, non_plugin


def count_control_flow(body_no_comments: str) -> int:
    """Count control-flow keywords in comment-stripped C++ source."""
    return len(CONTROL_FLOW_RE.findall(body_no_comments))


def has_fp_token(text: str) -> bool:
    """Check whether the text contains any floating-point math tokens."""
    return any(tok in text for tok in FP_SOURCE_TOKENS)


def parse_asm_line_op(line: str) -> str | None:
    """Extract the opcode from an assembly listing line.

    Expects the format ``XXXXXXXX  OPCODE ...`` where ``XXXXXXXX`` is an
    8-digit hex address.

    Returns:
        The opcode string if matched, otherwise ``None``.
    """
    m = ASM_LINE_RE.match(line)
    if m:
        return m.group(1)
    return None


def has_fp_asm(instructions: str) -> bool:
    """Check whether assembly instructions contain floating-point sensitive opcodes."""
    for line in instructions.splitlines():
        op = parse_asm_line_op(line)
        if op is not None and op.startswith(FP_ASM_PREFIXES):
            return True
    return False
