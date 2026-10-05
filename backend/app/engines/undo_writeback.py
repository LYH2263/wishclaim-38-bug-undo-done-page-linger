"""状态回写: restore the pre-fulfill claim when an undo passes the gate.

拍板 (locked decisions):
1. 举证快照: 撤销即清空 — 再次核销必须重新举证, 旧快照不保留。
2. TTL: 继承核销前剩余 (expires_at - fulfilled_at), 负值钳 0 — 不重开满额,
   防止 fulfill/undo 循环刷满 TTL。mine/墙卡/详情三处倒计时同吃这一个 expires_at。
3. 撤销窗长: 核销时把 undo_deadline = fulfilled_at + 当时 undo_seconds 写入行内快照,
   事后改窗长不影响已核销行; 门禁与投影同读该快照, 撤销成功即清掉。
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
        "undo_deadline": None,
    }
