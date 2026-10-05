from app.db import connect

def init_db():
    c = connect()
    c.executescript("""
    CREATE TABLE IF NOT EXISTS wishes(
      id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT, note TEXT, status TEXT,
      claimer TEXT, claimed_at TEXT, expires_at TEXT, data_quality TEXT
    );
    CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY, value TEXT);
    """)
    cols = [r["name"] for r in c.execute("PRAGMA table_info(wishes)")]
    for col in ("fulfilled_at", "proof", "undo_deadline"):
        if col not in cols:
            c.execute(f"ALTER TABLE wishes ADD COLUMN {col} TEXT")
    c.execute("INSERT OR IGNORE INTO settings(key,value) VALUES ('undo_seconds','3600')")
    if c.execute("SELECT COUNT(*) c FROM wishes").fetchone()["c"] == 0:
        c.executemany(
            "INSERT INTO wishes(title,note,status,claimer,claimed_at,expires_at,data_quality,fulfilled_at,proof,undo_deadline) VALUES (?,?,?,?,?,?,?,?,?,?)",
            [
                ("机械键盘", "红轴", "open", None, None, None, "clean", None, None, None),
                ("围巾", "羊毛", "open", None, None, None, "clean", None, None, None),
                ("脏愿望-空标题", "", "open", None, None, None, "dirty", None, None, None),
                ("过期锁样例", "应被TTL释放", "claimed", "ghost", "2020-01-01T00:00:00+00:00",
                 "2020-01-01T01:00:00+00:00", "dirty", None, None, None),
                ("撤销窗已过期样例", "窗外撤销应失败", "fulfilled", "ghost",
                 "2020-01-01T00:00:00+00:00", "2020-01-01T01:00:00+00:00", "clean",
                 "2020-01-01T00:30:00+00:00", "已当面交付", "2020-01-01T01:30:00+00:00"),
            ],
        )
        c.execute("INSERT INTO settings(key,value) VALUES ('ttl_seconds','86400')")
        c.execute("INSERT INTO settings(key,value) VALUES ('wall_title','暖粉愿望墙')")
        c.commit()
    c.commit()
    c.close()
