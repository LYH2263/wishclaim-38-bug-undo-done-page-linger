"""投影: single read-side shape so 倒计时/详情/我的认领/已完成 stay 同钉.

所有倒计时只从这里出:
- claimed: remaining_seconds  ← expires_at (撤销后 = 核销前剩余, 不是满额)
- fulfilled: undo_remaining_seconds / undo_deadline ← undo_until 核销时刻快照
  (legacy 行兜底 fulfilled_at + 当前 undo_seconds), can_undo 与之严格同口径
"""
from datetime import timedelta

from app.engines.claim_lock import parse_ts
from app.engines.undo_gate import undo_deadline


def project_wish(row: dict, now, undo_seconds: int) -> dict:
    w = dict(row)
    w["remaining_seconds"] = None
    w["undo_remaining_seconds"] = None
    w["undo_deadline"] = None
    w["can_undo"] = False
    if w.get("status") == "claimed" and w.get("expires_at"):
        w["remaining_seconds"] = max(0, int((parse_ts(w["expires_at"]) - now).total_seconds()))
    if w.get("status") == "fulfilled":
        if w.get("undo_until"):
            deadline = parse_ts(w["undo_until"])
        elif w.get("fulfilled_at"):
            deadline = undo_deadline(w["fulfilled_at"], undo_seconds)
        else:
            deadline = None
        if deadline is not None:
            w["undo_deadline"] = deadline.isoformat()
            left = int((deadline - now).total_seconds())
            w["undo_remaining_seconds"] = max(0, left)
            w["can_undo"] = left > 0
    return w
