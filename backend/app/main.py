from datetime import datetime, timezone
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from app import seed
from app.db import connect
from app.engines.claim_lock import claim_allowed, lock_payload, release_if_expired
from app.engines.undo_gate import undo_allowed, undo_deadline
from app.engines.undo_writeback import undo_writeback
from app.modules.claim_projection import project_wish

app = FastAPI(title="Wishclaim", version="0.1.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

@app.on_event("startup")
def _startup(): seed.init_db()

def now(): return datetime.now(timezone.utc)

def ttl():
    c = connect(); row = c.execute("SELECT value FROM settings WHERE key='ttl_seconds'").fetchone(); c.close()
    return int(row["value"] if row else 86400)

def undo_seconds():
    c = connect(); row = c.execute("SELECT value FROM settings WHERE key='undo_seconds'").fetchone(); c.close()
    return int(row["value"] if row else 3600)

def project(rows):
    n, u = now(), undo_seconds()
    return [project_wish(r, n, u) for r in rows]

def sweep(c):
    for r in c.execute("SELECT * FROM wishes WHERE status='claimed'"):
        rel = release_if_expired(r["status"], r["expires_at"], now())
        if rel:
            c.execute("UPDATE wishes SET status=?, claimer=?, claimed_at=?, expires_at=? WHERE id=?",
                      (rel["status"], None, None, None, r["id"]))

@app.get("/api/health")
def health(): return {"ok": True, "project": "wishclaim"}

@app.get("/api/wishes")
def list_wishes():
    c = connect(); sweep(c); c.commit()
    rows = [dict(r) for r in c.execute("SELECT * FROM wishes ORDER BY id DESC")]; c.close()
    return project(rows)

@app.get("/api/wishes/{wid}")
def get_wish(wid: int):
    c = connect(); sweep(c); c.commit()
    r = c.execute("SELECT * FROM wishes WHERE id=?", (wid,)).fetchone(); c.close()
    if not r: raise HTTPException(404, "not found")
    return project([dict(r)])[0]

class WishIn(BaseModel):
    title: str
    note: str = ""

@app.post("/api/wishes")
def create_wish(body: WishIn):
    c = connect()
    cur = c.execute("INSERT INTO wishes(title,note,status,data_quality) VALUES (?,?,?,?)",
                    (body.title, body.note, "open", "clean"))
    c.commit(); wid = cur.lastrowid; c.close(); return {"id": wid}

class ClaimIn(BaseModel):
    claimer: str

@app.post("/api/wishes/{wid}/claim")
def claim(wid: int, body: ClaimIn):
    c = connect(); c.execute("BEGIN IMMEDIATE")
    sweep(c)
    r = c.execute("SELECT * FROM wishes WHERE id=?", (wid,)).fetchone()
    if not r: c.rollback(); c.close(); raise HTTPException(404, "not found")
    allowed = claim_allowed(r["status"], r["claimer"], now(), r["expires_at"])
    if not allowed["ok"]:
        c.rollback(); c.close(); raise HTTPException(409, allowed["reason"])
    p = lock_payload(body.claimer, now(), ttl())
    c.execute("UPDATE wishes SET status=?, claimer=?, claimed_at=?, expires_at=? WHERE id=?",
              (p["status"], p["claimer"], p["claimed_at"], p["expires_at"], wid))
    c.commit(); c.close(); return p

@app.post("/api/wishes/{wid}/release")
def release(wid: int):
    c = connect(); c.execute("BEGIN IMMEDIATE")
    r = c.execute("SELECT * FROM wishes WHERE id=?", (wid,)).fetchone()
    if not r: c.rollback(); c.close(); raise HTTPException(404, "not found")
    if r["status"] != "claimed":
        c.rollback(); c.close(); raise HTTPException(400, "not_claimed")
    c.execute("UPDATE wishes SET status='released', claimer=NULL, claimed_at=NULL, expires_at=NULL WHERE id=?", (wid,))
    c.commit(); c.close(); return {"ok": True, "status": "released"}

class FulfillIn(BaseModel):
    proof: str = ""

@app.post("/api/wishes/{wid}/fulfill")
def fulfill(wid: int, body: FulfillIn | None = None):
    c = connect(); c.execute("BEGIN IMMEDIATE")
    r = c.execute("SELECT * FROM wishes WHERE id=?", (wid,)).fetchone()
    if not r: c.rollback(); c.close(); raise HTTPException(404, "not found")
    # 核销与撤销互斥: 只有 claimed 能进 fulfilled, 已 fulfilled 直接 409,
    # 不可能出现 done 与 认领中 同时成立。
    if r["status"] != "claimed":
        c.rollback(); c.close(); raise HTTPException(409 if r["status"] == "fulfilled" else 400, "need_claim")
    ts = now()
    # 撤销窗按核销时刻快照, expires_at 原样保留 = 核销前剩余的冻结基线。
    cur = c.execute(
        "UPDATE wishes SET status='fulfilled', fulfilled_at=?, undo_until=?, proof=? "
        "WHERE id=? AND status='claimed'",
        (ts.isoformat(), undo_deadline(ts.isoformat(), undo_seconds()).isoformat(),
         body.proof if body else "", wid))
    if cur.rowcount == 0:
        c.rollback(); c.close(); raise HTTPException(409, "state_changed")
    c.commit(); c.close()
    return {"ok": True, "status": "fulfilled", "fulfilled_at": ts.isoformat()}

@app.post("/api/wishes/{wid}/undo")
def undo(wid: int):
    c = connect(); c.execute("BEGIN IMMEDIATE")
    r = c.execute("SELECT * FROM wishes WHERE id=?", (wid,)).fetchone()
    if not r: c.rollback(); c.close(); raise HTTPException(404, "not found")
    gate = undo_allowed(r["status"], r["fulfilled_at"], r["undo_until"], now(), undo_seconds())
    if not gate["ok"]:
        # 窗外/非已核销: 不写任何字段 — TTL、举证、状态全部停在失败前。
        c.rollback(); c.close()
        raise HTTPException(400 if gate["reason"] == "not_fulfilled" else 409, gate["reason"])
    p = undo_writeback(now(), r["fulfilled_at"], r["expires_at"])
    cur = c.execute(
        "UPDATE wishes SET status='claimed', expires_at=?, fulfilled_at=NULL, proof=NULL, "
        "undo_until=NULL WHERE id=? AND status='fulfilled'",
        (p["expires_at"], wid))
    if cur.rowcount == 0:
        c.rollback(); c.close(); raise HTTPException(409, "state_changed")
    c.commit(); c.close()
    return {"ok": True, **p}

@app.get("/api/mine")
def mine(claimer: str):
    c = connect(); sweep(c); c.commit()
    rows = [dict(r) for r in c.execute("SELECT * FROM wishes WHERE claimer=?", (claimer,))]; c.close()
    return project(rows)

@app.get("/api/done")
def done():
    c = connect()
    # 只认真状态: 撤销后 proof 已清空, 行回到 claimed, 必须从这里消失。
    rows = [dict(r) for r in c.execute("SELECT * FROM wishes WHERE status='fulfilled'")]; c.close()
    return project(rows)

@app.get("/api/settings")
def settings():
    c = connect(); rows = {r["key"]: r["value"] for r in c.execute("SELECT * FROM settings")}; c.close(); return rows

@app.get("/api/rules")
def rules():
    return {
        "mutex": "同一愿望同时只能被一人认领",
        "ttl": "认领超时未核销则自动释放；核销期间 TTL 冻结",
        "fulfill": "核销后状态变为 fulfilled，撤销窗截止时刻按核销当时窗长快照",
        "undo": "核销后撤销窗内可撤销回认领态（举证清空、TTL 继承核销前剩余，不重开满额），窗外不可撤销",
    }
