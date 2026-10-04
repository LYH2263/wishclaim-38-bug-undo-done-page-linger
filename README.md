# Wishclaim · 礼物愿望认领

发布 → 认领锁定（互斥+TTL）→ 核销/释放 → 撤销窗内可撤销。

**核销撤销窗**：fulfill 后 `undo_seconds`（默认 3600s）内可 `POST /api/wishes/{id}/undo` 撤销回 `claimed`；窗外返回 `409 window_expired`，非 fulfilled 返回 `400 not_fulfilled`。两处拍板：撤销后**举证快照清空**（再次核销须重新举证）、**TTL 继承核销前剩余**（`expires_at - fulfilled_at`，负值钳 0，不重开满额）。撤销门禁 / 状态回写 / 投影分属 `engines/undo_gate`、`engines/undo_writeback`、`modules/claim_projection`，倒计时、详情、我的认领、已完成共用同一投影同钉。

| 服务 | 端口 |
| --- | --- |
| 前端 | 5200 |
| API | 10200 |

```bash
docker compose up --build
pytest backend/app/tests
```

0-1：`wish_comment` / `secret_santa` / `price_cap`。
