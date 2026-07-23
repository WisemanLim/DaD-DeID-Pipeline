"""정책 엔진 (Epic 2) — 검출 → deid 액션 + 민감도 결정.

builtin 규칙엔진. (OPA/Cedar 는 POLICY_ENGINE env 로 후속 교체)
seed 가드레일 액션(block/redact/...) + category/subCategory → deid 액션으로 매핑.
"""
from __future__ import annotations

from enum import Enum

from app.detect.detector import Detection


class DeidAction(str, Enum):
    REMOVE = "REMOVE"
    MASK = "MASK"
    TOKENIZE = "TOKENIZE"
    GENERALIZE = "GENERALIZE"
    RANGE_BUCKET = "RANGE_BUCKET"
    HASH = "HASH"


class Sensitivity(str, Enum):
    PUBLIC = "PUBLIC"
    INTERNAL = "INTERNAL"
    CONFIDENTIAL = "CONFIDENTIAL"
    RESTRICTED = "RESTRICTED"
    TRADE_SECRET = "TRADE_SECRET"


_RANK = {s: i for i, s in enumerate(Sensitivity)}

# (category, subCategory) → deid 액션. subCategory=None = category 기본값.
_ACTION_MAP: dict[tuple[str, str | None], DeidAction] = {
    ("pii", "national_id_kr"): DeidAction.REMOVE,
    ("pii", "email"): DeidAction.MASK,
    ("pii", "phone_kr"): DeidAction.MASK,
    ("pii", "business_reg_kr"): DeidAction.MASK,
    ("pii", "ip_address"): DeidAction.MASK,
    ("credentials", None): DeidAction.REMOVE,
    ("financial", "card_pan"): DeidAction.TOKENIZE,
    ("financial", "bank_account_kr"): DeidAction.MASK,
    ("financial", None): DeidAction.TOKENIZE,
    ("ip", None): DeidAction.RANGE_BUCKET,          # 영업비밀 → 범주화/recipe token
    ("sensitive", None): DeidAction.GENERALIZE,
    ("pii", None): DeidAction.MASK,
}


def _sensitivity_of(d: Detection, action: DeidAction) -> Sensitivity:
    if d.category == "ip" or action == DeidAction.RANGE_BUCKET:
        return Sensitivity.TRADE_SECRET
    if d.severity == "critical":
        return Sensitivity.RESTRICTED
    if d.severity == "high":
        return Sensitivity.CONFIDENTIAL
    return Sensitivity.INTERNAL


class PolicyDecision:
    def __init__(self, detection: Detection, action: DeidAction, sensitivity: Sensitivity):
        self.detection = detection
        self.action = action
        self.sensitivity = sensitivity


class PolicyEngine:
    def decide(self, d: Detection) -> PolicyDecision:
        action = (
            _ACTION_MAP.get((d.category, d.sub_category))
            or _ACTION_MAP.get((d.category, None))
            or DeidAction.MASK
        )
        return PolicyDecision(d, action, _sensitivity_of(d, action))

    def overall_sensitivity(self, decisions: list[PolicyDecision]) -> Sensitivity:
        if not decisions:
            return Sensitivity.PUBLIC
        return max((p.sensitivity for p in decisions), key=lambda s: _RANK[s])

    @staticmethod
    def export_blocked(level: Sensitivity) -> bool:
        return level in (Sensitivity.RESTRICTED, Sensitivity.TRADE_SECRET)
