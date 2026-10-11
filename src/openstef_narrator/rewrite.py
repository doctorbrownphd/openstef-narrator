"""LLM rewrite layer — backend adapters and fact validation.

The rewrite() interface takes a template draft with «fact» markers
and returns natural prose with all markers preserved. The LLM shapes
language, never numbers.
"""

from __future__ import annotations

import os
import re


def _extract_markers(text: str) -> set[str]:
    """Extract all «...» marker values from text."""
    return set(re.findall(r"«([^»]+)»", text))


def _strip_markers(text: str) -> str:
    """Remove all «...» marker spans, leaving only unmarked prose."""
    return re.sub(r"«[^»]+»", "", text)


# Numeric patterns the LLM might invent outside markers:
# "15%", "3.5 MW", "23°F", "1,200 kW", "$50", "12:00", "48-hour"
# We allow bare integers < 10 (prose like "two or three hours") and
# time-period words already anchored by the template ("48-hour horizon").
_ROGUE_NUMERIC = re.compile(
    r"(?<!\w)"          # not preceded by word char (avoids matching inside words)
    r"(?:"
    r"\d+[.,]\d+"       # decimal or thousand-separator numbers (check first)
    r"|\d+\s*%"         # percentage
    r"|\d+\s*°"         # temperature
    r"|\d+\s*(?:MW|kW|GW|MWh|kWh)" # power/energy units
    r"|\d{2,}"          # any number with 2+ digits (catch-all, checked last)
    r")"
    r"(?!\w)"           # not followed by word char
)

# Tokens that are safe even outside markers (template boilerplate, not LLM-invented)
_SAFE_NUMERIC_PATTERNS = frozenset({"48-hour", "24-hour"})


def _find_rogue_numbers(original: str, rewritten: str) -> list[str]:
    """Find numeric tokens in the rewrite that aren't inside «» markers
    and weren't in the original unmarked prose either."""
    # Numbers that were in the original template's unmarked prose are fine
    # (e.g. "three hours", "48-hour horizon")
    original_bare = _strip_markers(original)
    original_nums = set(_ROGUE_NUMERIC.findall(original_bare))

    # Scan only the unmarked prose of the rewrite
    rewritten_bare = _strip_markers(rewritten)
    rewritten_nums = _ROGUE_NUMERIC.findall(rewritten_bare)

    rogues = []
    for num in rewritten_nums:
        if num not in original_nums and num.strip() not in _SAFE_NUMERIC_PATTERNS:
            rogues.append(num)
    return rogues


def validate_markers(original: str, rewritten: str) -> bool:
    """Validate that a rewrite preserves the hallucination boundary.

    Two checks:
    1. All «fact» markers from the original survive in the rewrite.
    2. No new numeric tokens appear outside markers (the LLM must not
       invent numbers the forecast didn't produce).
    """
    original_facts = _extract_markers(original)
    rewritten_facts = _extract_markers(rewritten)

    # Check 1: all original markers preserved
    if not original_facts.issubset(rewritten_facts):
        return False

    # Check 2: no rogue numbers invented by the LLM
    rogues = _find_rogue_numbers(original, rewritten)
    if rogues:
        return False

    return True


class RewriteBackend:
    """Abstract interface for LLM rewrite backends."""

    name: str = "base"

    def rewrite(self, draft: str, facts: dict[str, str], tone: str) -> str:
        """Rewrite prose between «fact» markers. Must preserve all markers."""
        raise NotImplementedError


class TemplateBackend(RewriteBackend):
    """Passthrough — returns the draft unchanged. Zero latency, zero risk."""

    name = "template_fallback"

    def rewrite(self, draft: str, facts: dict[str, str], tone: str) -> str:
        return draft


class AnthropicBackend(RewriteBackend):
    """Claude-based rewriter. Requires anthropic SDK and ANTHROPIC_API_KEY."""

    name = "anthropic"

    def __init__(self, model: str = "claude-sonnet-4-20250514", api_key: str | None = None):
        import anthropic

        self._client = anthropic.Anthropic(api_key=api_key or os.environ.get("ANTHROPIC_API_KEY"))
        self._model = model
        self.model_version = model  # exposed for audit trail

    def rewrite(self, draft: str, facts: dict[str, str], tone: str) -> str:
        """Rewrite the draft prose while preserving all «fact» markers."""
        prompt = (
            f"You are a distribution-grid operations writer. Rewrite the following "
            f"situation report to be more natural and {tone}.\n\n"
            f"CRITICAL RULES:\n"
            f"1. Preserve ALL text wrapped in «guillemet» markers (« and ») EXACTLY as-is. "
            f"Do NOT change, add, remove, or reformat any «marked» values.\n"
            f"2. Do NOT introduce any number, percentage, temperature, power value, or "
            f"time that is not already present in a «marker». Every quantitative claim "
            f"must come from the markers.\n"
            f"3. Do NOT invent causal claims. The «driver» markers name the causes; you "
            f"may rephrase around them but must not introduce new causes, weather events, "
            f"grid conditions, or explanations not already in the draft.\n"
            f"4. Only reshape the prose BETWEEN markers for fluency and {tone} tone.\n"
            f"5. Return ONLY the rewritten text, no commentary.\n\n"
            f"Draft to rewrite:\n{draft}"
        )

        response = self._client.messages.create(
            model=self._model,
            max_tokens=1024,
            temperature=0.0,  # deterministic for reproducibility (1.4)
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text


def detect_backend() -> RewriteBackend:
    """Auto-detect the best available LLM backend. Falls back to template."""
    try:
        key = os.environ.get("ANTHROPIC_API_KEY")
        if key:
            return AnthropicBackend(api_key=key)
    except ImportError:
        pass
    return TemplateBackend()
