"""Quiet action policy — vision evidence changes what Northbridge does next."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class ActionKind(str, Enum):
    AUTO_LOG = "auto_log"
    NOTIFY = "notify"
    HUMAN_REQUIRED = "human_required"
    NOOP = "noop"


@dataclass
class ActionDecision:
    action: ActionKind
    reason: str
    severity: float
    notify_targets: list[str]
    speakable_brief: str
    requires_ack: bool
    policy_version: str = "northbridge-watch-policy-v1"

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["action"] = self.action.value
        return d


class PolicyEngine:
    def __init__(
        self,
        notify_confidence: float = 0.5,
        multi_package_human: int = 2,
        quiet_hours: tuple[int, int] = (22, 7),
    ):
        self.notify_confidence = notify_confidence
        self.multi_package_human = multi_package_human
        self.quiet_hours = quiet_hours

    def decide(self, detection_dict: dict[str, Any], now: datetime | None = None) -> ActionDecision:
        now = now or datetime.now(timezone.utc)
        primary = detection_dict.get("primary")
        detections = detection_dict.get("detections") or []
        if not primary:
            return ActionDecision(
                action=ActionKind.NOOP,
                reason="No anomaly detected — porch/kitchen calm.",
                severity=0.0,
                notify_targets=[],
                speakable_brief="All quiet at Northbridge.",
                requires_ack=False,
            )

        label = primary["label"]
        conf = float(primary["confidence"])
        n_packages = sum(1 for d in detections if d["label"] == "package")
        in_quiet = self._in_quiet_hours(now)

        if label == "spill":
            return ActionDecision(
                action=ActionKind.HUMAN_REQUIRED,
                reason=f"Spill detected (conf={conf:.2f}) — safety hazard.",
                severity=min(1.0, conf + 0.15),
                notify_targets=["Avery", "Morgan"],
                speakable_brief="Heads up — I see a spill on the kitchen floor. Want me to log a clean-up task?",
                requires_ack=True,
            )

        if label == "empty_fridge":
            if in_quiet:
                return ActionDecision(
                    action=ActionKind.AUTO_LOG,
                    reason="Empty fridge logged quietly (quiet hours).",
                    severity=conf * 0.5,
                    notify_targets=[],
                    speakable_brief="Fridge looks sparse. I logged a restock note for morning.",
                    requires_ack=False,
                )
            return ActionDecision(
                action=ActionKind.NOTIFY if conf >= self.notify_confidence else ActionKind.AUTO_LOG,
                reason=f"Empty fridge shelf (conf={conf:.2f}).",
                severity=conf * 0.6,
                notify_targets=["Morgan"],
                speakable_brief="The fridge looks mostly empty. Shall I add milk and produce to the list?",
                requires_ack=True,
            )

        if label == "package":
            if n_packages >= self.multi_package_human:
                return ActionDecision(
                    action=ActionKind.HUMAN_REQUIRED,
                    reason=f"{n_packages} packages at door (conf={conf:.2f}) — doorway blocked.",
                    severity=min(1.0, 0.55 + 0.15 * n_packages),
                    notify_targets=["Avery", "Morgan"],
                    speakable_brief=f"There are {n_packages} packages by the door. Bring them in when you can?",
                    requires_ack=True,
                )
            if conf >= self.notify_confidence and not in_quiet:
                return ActionDecision(
                    action=ActionKind.NOTIFY,
                    reason=f"Single package (conf={conf:.2f}).",
                    severity=conf * 0.7,
                    notify_targets=["Avery"],
                    speakable_brief="A package arrived on the porch. I can mark it received.",
                    requires_ack=True,
                )
            return ActionDecision(
                action=ActionKind.AUTO_LOG,
                reason=f"Package signal (conf={conf:.2f})"
                + (" — quiet hours, auto-logged." if in_quiet else " — logged only."),
                severity=conf * 0.45,
                notify_targets=[],
                speakable_brief="Package noted on the porch ledger.",
                requires_ack=False,
            )

        return ActionDecision(
            action=ActionKind.AUTO_LOG,
            reason=f"Unrecognized label {label} — safe default auto-log.",
            severity=conf * 0.3,
            notify_targets=[],
            speakable_brief="I noticed something unusual and logged it.",
            requires_ack=False,
        )

    def _in_quiet_hours(self, now: datetime) -> bool:
        start, end = self.quiet_hours
        hour = now.hour
        if start > end:
            return hour >= start or hour < end
        return start <= hour < end
