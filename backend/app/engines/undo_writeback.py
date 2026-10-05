"""状态回写: restore the pre-fulfill claim when an undo passes the gate.

拍板 (locked decisions):
1. 举证快照: 撤销即清空 (proof/fulfilled_at/undo_until 全清) — 再次核销必须
   重新举证, 旧快照不保留。
2. TTL: 继承核销前剩余 (expires_at - fulfilled_at), 负值钳 0 — 核销期间 TTL
   冻结, 不从撤销这一刻重开满额, 防止 fulfill/undo 循环刷满 TTL。
   mine / 墙卡 / 详情三处倒计时只读回写后的 expires_at 这一个钉。
"""
from datetime import datetime, timedelta

from app.engines.claim_lock import parse_ts


def undo_writeback(now: datetime, fulfilled_at: str | None, expires_at: str | None) -> dict:
    remaining = 0
    if fulfilled_at and expires_at:
        remaining = max(0, int((parse_ts(expires_at) - parse_ts(fulfilled_at)).total_seconds()))
    return {
        "status": "claimed",
        "expires_at": (now + timedelta(seconds=remaining)).isoformat(),
        "fulfilled_at": None,
        "proof": None,
        "undo_until": None,
        "remaining_seconds": remaining,
    }
