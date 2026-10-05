import os
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    from app.main import app  # db_path() reads DATA_DIR per connection
    with TestClient(app) as c:
        from app.db import connect
        db = connect(); db.execute("DELETE FROM wishes"); db.commit(); db.close()
        yield c


def iso(dt):
    return dt.isoformat()


def set_setting(client, key, value):
    from app.db import connect
    c = connect()
    c.execute("INSERT INTO settings(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
              (key, str(value)))
    c.commit(); c.close()


def insert(client, **kw):
    from app.db import connect
    base = dict(title="t", note="", status="open", claimer=None, claimed_at=None,
                expires_at=None, data_quality="clean", fulfilled_at=None, proof=None, undo_until=None)
    base.update(kw)
    c = connect()
    cur = c.execute(
        "INSERT INTO wishes(title,note,status,claimer,claimed_at,expires_at,data_quality,"
        "fulfilled_at,proof,undo_until) VALUES(:title,:note,:status,:claimer,:claimed_at,"
        ":expires_at,:data_quality,:fulfilled_at,:proof,:undo_until)", base)
    c.commit(); wid = cur.lastrowid; c.close()
    return wid


def get_row(client, wid):
    from app.db import connect
    c = connect(); r = dict(c.execute("SELECT * FROM wishes WHERE id=?", (wid,)).fetchone()); c.close()
    return r


NOW = datetime(2026, 10, 4, 12, 0, 0, tzinfo=timezone.utc)


def test_in_window_undo_clears_proof_and_inherits_remaining(client, monkeypatch):
    # 核销时刻 TTL 还剩 110s (expires-fulfilled); 核销 10s 期间 TTL 冻结,
    # 全局 ttl 是满额 86400, 撤销后必须等于 110 而非满额。
    monkeypatch.setattr("app.main.now", lambda: NOW)
    wid = insert(client, status="fulfilled", claimer="alice",
                 claimed_at=iso(NOW - timedelta(hours=2)),
                 expires_at=iso(NOW + timedelta(seconds=100)),
                 fulfilled_at=iso(NOW - timedelta(seconds=10)),
                 proof="照片A", undo_until=iso(NOW + timedelta(seconds=3590)))

    r = client.post(f"/api/wishes/{wid}/undo")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "claimed"
    assert body["proof"] is None and body["fulfilled_at"] is None
    assert body["remaining_seconds"] == 110

    row = get_row(client, wid)
    assert row["status"] == "claimed" and row["proof"] is None
    assert row["fulfilled_at"] is None and row["undo_until"] is None
    assert row["expires_at"] == iso(NOW + timedelta(seconds=110))

    # 已完成页必须消失; mine 行回到认领中且倒计时吃剩余
    assert client.get("/api/done").json() == []
    mine = [w for w in client.get("/api/mine?claimer=alice").json() if w["id"] == wid][0]
    assert mine["status"] == "claimed" and mine["remaining_seconds"] == 110

    detail = client.get(f"/api/wishes/{wid}").json()
    assert detail["remaining_seconds"] == 110 and detail["can_undo"] is False


def test_out_of_window_undo_fails_and_changes_nothing(client, monkeypatch):
    monkeypatch.setattr("app.main.now", lambda: NOW)
    wid = insert(client, status="fulfilled", claimer="bob",
                 expires_at=iso(NOW + timedelta(seconds=50)),
                 fulfilled_at=iso(NOW - timedelta(seconds=7200)),
                 proof="照片B", undo_until=iso(NOW - timedelta(seconds=3600)))

    before = get_row(client, wid)
    r = client.post(f"/api/wishes/{wid}/undo")
    assert r.status_code == 409 and r.json()["detail"] == "window_expired"
    after = get_row(client, wid)
    # 接口失败: TTL / 举证 / 状态全部停在失败前
    assert after == before

    done = client.get("/api/done").json()
    assert [w["id"] for w in done] == [wid]
    assert done[0]["can_undo"] is False and done[0]["undo_remaining_seconds"] == 0


def test_window_length_change_after_fulfill_uses_snapshot(client, monkeypatch):
    monkeypatch.setattr("app.main.now", lambda: NOW)
    set_setting(client, "undo_seconds", 3600)
    wid = insert(client, status="fulfilled", claimer="carol",
                 expires_at=iso(NOW + timedelta(days=1)),
                 fulfilled_at=iso(NOW), undo_until=iso(NOW + timedelta(seconds=3600)))
    # 核销后把窗长改成 1s — 已核销行吃快照, 仍可撤销
    set_setting(client, "undo_seconds", 1)
    detail = client.get(f"/api/wishes/{wid}").json()
    assert detail["can_undo"] is True
    assert detail["undo_remaining_seconds"] == 3600
    assert client.post(f"/api/wishes/{wid}/undo").status_code == 200


def test_undo_non_fulfilled_is_400_without_mutation(client, monkeypatch):
    monkeypatch.setattr("app.main.now", lambda: NOW)
    exp = iso(NOW + timedelta(seconds=300))
    wid = insert(client, status="claimed", claimer="dave", expires_at=exp)
    r = client.post(f"/api/wishes/{wid}/undo")
    assert r.status_code == 400 and r.json()["detail"] == "not_fulfilled"
    assert get_row(client, wid)["expires_at"] == exp


def test_fulfill_twice_conflicts_and_undo_then_refulfill_needs_new_proof(client):
    r = client.post("/api/wishes", json={"title": "x"})
    wid = r.json()["id"]
    assert client.post(f"/api/wishes/{wid}/claim", json={"claimer": "eve"}).status_code == 200
    assert client.post(f"/api/wishes/{wid}/fulfill", json={"proof": "签收单"}).status_code == 200
    # 撤销与再次核销互斥: 已核销再核销必须 409, 不出现双态
    r2 = client.post(f"/api/wishes/{wid}/fulfill", json={"proof": "重复"})
    assert r2.status_code == 409
    assert client.post(f"/api/wishes/{wid}/undo").status_code == 200
    row = get_row(client, wid)
    assert row["status"] == "claimed" and row["proof"] is None
    # 再次核销: 旧举证不保留
    assert client.post(f"/api/wishes/{wid}/fulfill", json={"proof": ""}).status_code == 200
    assert client.get(f"/api/wishes/{wid}").json()["proof"] == ""
    assert [w["id"] for w in client.get("/api/done").json()] == [wid]


def test_done_ignores_claimed_rows_even_with_proof(client):
    # 防御: 撤销后理论上 proof 已清, 但 /done 只认真状态, 残留举证也不该挂行
    insert(client, status="claimed", claimer="finn", proof="孤儿举证",
           expires_at=iso(NOW + timedelta(seconds=10)))
    assert client.get("/api/done").json() == []
