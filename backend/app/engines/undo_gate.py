"""撤销门禁: decide whether a fulfilled wish may be undone back to claimed."""
from datetime import datetime

from app.engines.claim_lock import parse_ts


def undo_allowed(status: str, fulfilled_at: str | None, now: datetime, undo_seconds: int) -> dict:
    """Only fulfilled wishes inside the undo window can be undone."""
    if status != "fulfilled":
        return {"ok": False, "reason": "not_fulfilled"}
    if not fulfilled_at:
        # Legacy rows without a fulfill timestamp cannot prove they are in-window.
        return {"ok": False, "reason": "not_fulfilled"}
    elapsed = (now - parse_ts(fulfilled_at)).total_seconds()
    if elapsed > undo_seconds:
        return {"ok": False, "reason": "window_expired"}
    return {"ok": True, "reason": ""}
