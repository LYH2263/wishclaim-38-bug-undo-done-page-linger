"""撤销门禁: decide whether a fulfilled wish may be undone back to claimed.

只认行内 undo_deadline 快照 (核销时写入), 不读实时窗长 —
与投影的 undo_remaining_seconds / can_undo 同一口径。
"""
from datetime import datetime

from app.engines.claim_lock import parse_ts


def undo_allowed(status: str, undo_deadline: str | None, now: datetime) -> dict:
    """Only fulfilled wishes inside the snapped undo window can be undone."""
    if status != "fulfilled":
        return {"ok": False, "reason": "not_fulfilled"}
    if not undo_deadline:
        # Legacy rows without a snapshot cannot prove they are in-window.
        return {"ok": False, "reason": "window_expired"}
    if now >= parse_ts(undo_deadline):
        return {"ok": False, "reason": "window_expired"}
    return {"ok": True, "reason": ""}
