"""投影: single read-side shape so 倒计时/详情/我的认领/已完成 stay 同钉."""
from datetime import datetime

from app.engines.claim_lock import parse_ts


def project_wish(row: dict, now: datetime, undo_seconds: int) -> dict:
    """Add countdown + undo-window fields derived from one clock and one config."""
    w = dict(row)
    w["remaining_seconds"] = None
    w["undo_remaining_seconds"] = None
    w["can_undo"] = False
    if w.get("status") == "claimed" and w.get("expires_at"):
        w["remaining_seconds"] = max(0, int((parse_ts(w["expires_at"]) - now).total_seconds()))
    if w.get("status") == "claimed" and w.get("fulfilled_at") is None and w.get("proof"):
        w["remaining_seconds"] = max(0, int((parse_ts(w["expires_at"]) - now).total_seconds())) if w.get("expires_at") else None
    if w.get("status") == "fulfilled" and w.get("fulfilled_at"):
        left = undo_seconds - int((now - parse_ts(w["fulfilled_at"])).total_seconds())
        w["undo_remaining_seconds"] = max(0, left)
        w["can_undo"] = left > 0
    return w
