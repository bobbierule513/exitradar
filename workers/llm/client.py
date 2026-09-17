"""LLM client adapter — Groq / OpenAI / Anthropic via explicit LLM_PROVIDER."""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

PROMPTS_DIR = Path(__file__).resolve().parents[2] / "docs" / "prompts"

# Groq retired llama-3.3-70b-versatile (2026-08-16) for free/developer tiers.
GROQ_DEFAULT_MODEL = "openai/gpt-oss-120b"
GROQ_BASE_URL = "https://api.groq.com/openai/v1"
GROQ_RETIRED_MODELS = {
    "llama-3.3-70b-versatile",
    "llama-3.1-8b-instant",
    "llama-3.3-70b-specdec",
}


def load_prompt(name: str) -> str:
    """Load a prompt template from docs/prompts."""
    path = PROMPTS_DIR / name
    if not path.exists():
        raise FileNotFoundError(f"Prompt not found: {path}")
    return path.read_text(encoding="utf-8")


def strip_fences(text: str) -> str:
    """Strip markdown code fences before JSON parsing."""
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    return text.strip()


def parse_json_response(raw: str) -> Dict[str, Any]:
    """Parse JSON from an LLM response with one retry-friendly strip."""
    cleaned = strip_fences(raw)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        logger.error("LLM JSON parse failure. Raw response: %s", raw)
        match = re.search(r"\{[\s\S]*\}", cleaned)
        if match:
            return json.loads(match.group(0))
        raise


class LLMClient:
    """Provider-agnostic LLM wrapper. Provider is explicit via LLM_PROVIDER."""

    def __init__(self) -> None:
        from apps.api.app.core.config import get_settings

        self.settings = get_settings()

    @property
    def available(self) -> bool:
        """True when the configured provider has an API key."""
        provider = (self.settings.llm_provider or "").lower()
        if provider == "groq":
            return bool(self.settings.groq_api_key)
        if provider == "anthropic":
            return bool(self.settings.anthropic_api_key)
        if provider == "openai":
            return bool(self.settings.openai_api_key)
        # Unknown provider: any key
        return bool(
            self.settings.groq_api_key
            or self.settings.openai_api_key
            or self.settings.anthropic_api_key
        )

    def complete(self, system: str, user: str, temperature: float = 0.2) -> str:
        """Run a chat completion and return text content."""
        provider = (self.settings.llm_provider or "openai").lower()
        if provider == "groq":
            if not self.settings.groq_api_key:
                raise RuntimeError("LLM_PROVIDER=groq but GROQ_API_KEY is not set")
            return self._groq(system, user, temperature)
        if provider == "anthropic":
            if not self.settings.anthropic_api_key:
                raise RuntimeError("LLM_PROVIDER=anthropic but ANTHROPIC_API_KEY is not set")
            return self._anthropic(system, user, temperature)
        if provider == "openai":
            if not self.settings.openai_api_key:
                raise RuntimeError("LLM_PROVIDER=openai but OPENAI_API_KEY is not set")
            return self._openai(system, user, temperature)
        raise RuntimeError(f"Unsupported LLM_PROVIDER: {provider}")

    def complete_json(self, system: str, user: str) -> Dict[str, Any]:
        """Complete and parse JSON, retrying once on parse failure."""
        raw = self.complete(system, user)
        try:
            return parse_json_response(raw)
        except (json.JSONDecodeError, ValueError):
            logger.warning("Retrying LLM JSON parse once")
            raw2 = self.complete(
                system + "\nRespond with valid JSON only. No markdown.",
                user,
            )
            return parse_json_response(raw2)

    def _groq(self, system: str, user: str, temperature: float) -> str:
        from openai import OpenAI

        client = OpenAI(api_key=self.settings.groq_api_key, base_url=GROQ_BASE_URL)
        model = self._resolve_groq_model()
        resp = client.chat.completions.create(
            model=model,
            temperature=temperature,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
        usage = resp.usage
        if usage:
            logger.info(
                "LLM groq tokens input=%s output=%s",
                usage.prompt_tokens,
                usage.completion_tokens,
            )
        return resp.choices[0].message.content or ""

    def _resolve_groq_model(self) -> str:
        """Map OpenAI/Anthropic IDs and retired Groq IDs to a live Groq model."""
        model = (self.settings.llm_model or GROQ_DEFAULT_MODEL).strip()
        if (
            model.startswith("gpt-")
            or model.startswith("claude")
            or model in GROQ_RETIRED_MODELS
            or model.startswith("llama-3")
        ):
            logger.warning(
                "LLM_MODEL=%s is not a current Groq model; using %s",
                model,
                GROQ_DEFAULT_MODEL,
            )
            return GROQ_DEFAULT_MODEL
        return model

    def _openai(self, system: str, user: str, temperature: float) -> str:
        from openai import OpenAI

        client = OpenAI(api_key=self.settings.openai_api_key)
        resp = client.chat.completions.create(
            model=self.settings.llm_model or "gpt-4o-mini",
            temperature=temperature,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
        usage = resp.usage
        if usage:
            logger.info(
                "LLM openai tokens input=%s output=%s",
                usage.prompt_tokens,
                usage.completion_tokens,
            )
        return resp.choices[0].message.content or ""

    def _anthropic(self, system: str, user: str, temperature: float) -> str:
        import anthropic

        client = anthropic.Anthropic(api_key=self.settings.anthropic_api_key)
        model = self.settings.llm_model
        if not model or model.startswith("gpt") or "llama" in model.lower():
            model = "claude-3-5-haiku-20241022"
        resp = client.messages.create(
            model=model,
            max_tokens=2048,
            temperature=temperature,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        logger.info(
            "LLM anthropic tokens input=%s output=%s",
            resp.usage.input_tokens,
            resp.usage.output_tokens,
        )
        parts = [b.text for b in resp.content if hasattr(b, "text")]
        return "\n".join(parts)


def parse_thesis_nl(text: str) -> Dict[str, Any]:
    """Convert natural-language thesis into structured criteria."""
    client = LLMClient()
    if not client.available:
        return _heuristic_thesis_parse(text)
    try:
        system = load_prompt("thesis_parse.txt")
        return client.complete_json(system, text)
    except Exception:
        logger.exception("Thesis NL parse via LLM failed; using heuristic fallback")
        return _heuristic_thesis_parse(text)


def _heuristic_thesis_parse(text: str) -> Dict[str, Any]:
    """Offline fallback when no LLM key is present."""
    lower = text.lower()
    industries = []
    for kw in ("hvac", "plumbing", "roofing", "landscaping", "dental", "veterinary", "saas"):
        if kw in lower:
            industries.append(kw.upper() if kw == "saas" else kw.title() if kw != "hvac" else "HVAC")
    if not industries:
        industries = ["General services"]
    states = []
    for st in ("CA", "TX", "FL", "AZ", "NY", "IL", "WA", "CO"):
        if st.lower() in lower or f" {st} " in f" {text} ":
            states.append(st)
    return {
        "name": (text[:60] + "…") if len(text) > 60 else text or "Untitled thesis",
        "criteria": {
            "industries": industries,
            "geographies": [{"country": "US", "states": states or ["CA"], "cities": []}],
            "revenue_min": 2_000_000 if "2" in text and "10" in text else None,
            "revenue_max": 10_000_000 if "10" in text else None,
            "owner_operated": "owner" in lower,
            "min_years_in_business": 15 if "15" in text else None,
            "keywords": industries,
        },
        "strategy": {
            "rationale": text[:240],
            "adjacent_segments": [],
        },
    }


def generate_outreach(
    company: Dict[str, Any],
    evidence: list,
    recommendation: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Generate evidence-grounded outreach draft."""
    client = LLMClient()
    evidence_ids = [e.get("id") for e in evidence if e.get("id")]
    snippets = [
        {"id": e.get("id"), "snippet": e.get("snippet"), "url": e.get("url")}
        for e in evidence[:8]
    ]
    if not client.available:
        subject = f"Quick question about {company.get('canonical_name')}"
        body = (
            f"Hi — I've been researching {company.get('canonical_name')} "
            f"({company.get('industry') or 'your industry'}) in "
            f"{(company.get('geo') or {}).get('city', 'your market')}. "
            f"Based on public information (evidence refs: {', '.join(evidence_ids[:3]) or 'n/a'}), "
            f"I'd value a brief conversation about the business trajectory — "
            f"not a hard pitch. Would you be open to a 15-minute call?\n\nBest regards"
        )
        return {"subject": subject, "body": body, "evidence_refs": evidence_ids}

    system = load_prompt("outreach.txt")
    user = json.dumps(
        {
            "company": {
                "name": company.get("canonical_name"),
                "industry": company.get("industry"),
                "geo": company.get("geo"),
                "founded_year": company.get("founded_year"),
            },
            "recommendation": recommendation,
            "evidence": snippets,
        },
        default=str,
    )
    result = client.complete_json(system, user)
    result["evidence_refs"] = evidence_ids
    return result


def generate_deal_brief(
    company: Dict[str, Any],
    opportunity: Dict[str, Any],
    evidence: list,
) -> Dict[str, Any]:
    """Generate a short deal brief from scores + evidence."""
    client = LLMClient()
    if not client.available:
        expl = opportunity.get("explanation") or {}
        return {
            "deal_brief": " ".join(expl.get("why_now") or ["Insufficient evidence for a full brief."]),
            "risks": expl.get("counter_signals") or [],
            "suggested_questions": [
                "Who is the decision-maker for ownership transitions?",
                "What does customer concentration look like?",
            ],
        }
    system = load_prompt("deal_brief.txt")
    user = json.dumps(
        {"company": company, "opportunity": opportunity, "evidence": evidence[:10]},
        default=str,
    )
    return client.complete_json(system, user)


def generate_weekly_brief(
    thesis_name: str,
    iso_week: Optional[str],
    cadence: Dict[str, Any],
    slots: List[Dict[str, Any]],
    evidence_ids: List[str],
) -> Dict[str, Any]:
    """Summarize an already-packed Book of Work. Never invent companies."""
    client = LLMClient()
    if not client.available:
        lines = [f"Week {iso_week or 'current'} — {thesis_name}"]
        for s in slots[:8]:
            lines.append(f"- [{s.get('kind')}] {s.get('name')}: {s.get('reason')}")
        return {
            "brief": "\n".join(lines),
            "focus": [s.get("name") for s in slots if s.get("kind") == "outreach"][:5],
            "evidence_refs": evidence_ids[:8],
        }
    system = load_prompt("weekly_brief.txt")
    user = json.dumps(
        {
            "thesis": thesis_name,
            "iso_week": iso_week,
            "cadence": cadence,
            "slots": slots,
            "evidence_ids": evidence_ids[:20],
        },
        default=str,
    )
    result = client.complete_json(system, user)
    if "evidence_refs" not in result:
        result["evidence_refs"] = evidence_ids[:8]
    return result
