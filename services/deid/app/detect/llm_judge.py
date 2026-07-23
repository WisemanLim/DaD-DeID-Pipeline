"""LLM judge (Claude) — classifier 룰 정밀 판정 (선택, best-effort).

임베딩 margin 판정(classifier_judge)보다 정밀하게, 텍스트가 룰 의도(examplesPositive)에
부합하는지 Claude 로 판정. ANTHROPIC_API_KEY 없으면 no-op(unavailable). 공식 anthropic SDK 사용.
기본 모델 claude-opus-4-8 (LLM_JUDGE_MODEL env 로 override). 구조화 출력(json_schema)로 강제.
"""
from __future__ import annotations

import json
import os

from pydantic import BaseModel

from app.detect.rules import Rule

_MODEL = os.getenv("LLM_JUDGE_MODEL", "claude-opus-4-8")

_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "violates": {"type": "boolean"},
        "reason": {"type": "string"},
    },
    "required": ["violates", "reason"],
}


class LLMVerdict(BaseModel):
    available: bool
    violates: bool = False
    reason: str = ""
    rule_id: str | None = None


def _client():
    """ANTHROPIC_API_KEY 있으면 Anthropic 클라이언트, 없으면 None."""
    if not os.getenv("ANTHROPIC_API_KEY"):
        return None
    try:
        from anthropic import Anthropic

        return Anthropic()
    except Exception:  # noqa: BLE001
        return None


def judge(text: str, rule: Rule) -> LLMVerdict:
    """text 가 rule 의도(차단 대상)에 부합하는지 Claude 판정. 키 없으면 available=False."""
    client = _client()
    if client is None:
        return LLMVerdict(available=False)
    examples = "\n".join(f"- {e}" for e in rule.examplesPositive[:5])
    system = (
        "You are a content policy classifier. Decide whether the USER TEXT matches the "
        "intent of a blocked-content rule. Respond only via the structured schema."
    )
    user = (
        f"Rule category: {rule.category}/{rule.subCategory}\n"
        f"Rule description: {rule.description}\n"
        f"Examples of content this rule blocks:\n{examples}\n\n"
        f"USER TEXT:\n{text}\n\n"
        "Does the USER TEXT match this rule's blocked intent?"
    )
    try:
        resp = client.messages.create(
            model=_MODEL,
            max_tokens=512,
            system=system,
            messages=[{"role": "user", "content": user}],
            output_config={"format": {"type": "json_schema", "schema": _SCHEMA}},
        )
        text_out = "".join(b.text for b in resp.content if getattr(b, "type", "") == "text")
        data = json.loads(text_out)
        return LLMVerdict(
            available=True, violates=bool(data.get("violates")),
            reason=str(data.get("reason", "")), rule_id=rule.ruleId,
        )
    except Exception as e:  # noqa: BLE001 — 판정 실패가 파이프라인을 막지 않음
        return LLMVerdict(available=False, reason=f"error: {e}")
