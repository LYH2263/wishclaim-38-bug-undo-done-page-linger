"""撤销门禁: decide whether a fulfilled wish may be undone back to claimed.

拍板 (locked decision):
- 窗长按核销时刻快照 (wishes.undo_until 绝对截止时刻)。事后改 undo_seconds
  不影响已核销行: 可否撤销只看 undo_until。
- legacy 行没有 undo_until 时, 以 fulfilled_at + 当前 undo_seconds 兜底。
"""
from datetime import datetime, timedelta

from app.engines.claim_lock import parse_ts


def undo_deadline(fulfilled_at: str, undo_seconds: int) -> datetime:
    return parse_ts(fulfilled_at) + timedelta(seconds=undo_seconds)


def undo_allowed(status: str, fulfilled_at: str | None, undo_until: str | None,
                 now: datetime, undo_seconds: int) -> dict:
    """Only fulfilled wishes inside the (snapshotted) undo window can be undone."""
    if status != "fulfilled" or not fulfilled_at:
        return {"ok": False, "reason": "not_fulfilled"}
    deadline = parse_ts(undo_until) if undo_until else undo_deadline(fulfilled_at, undo_seconds)
    if now >= deadline:
        return {"ok": False, "reason": "window_expired"}
    return {"ok": True, "reason": "", "deadline": deadline.isoformat()}
