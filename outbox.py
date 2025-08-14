# © 2025 Tejas Gajjar. All rights reserved.
# Owner: Tejas Gajjar — Agentic Middleware for Enterprise Integration
# Contact: tejas.gajjar@macys.com | tejgajjar2001@gmail.com
# Note: This module is tailored for OCI/GCP/AWS + TIBCO BW/JMS environments.

import sqlite3, os, json
from typing import Optional

class Outbox:
    def __init__(self, path: str):
        self.path = path
        init = not os.path.exists(path)
        self.conn = sqlite3.connect(path, check_same_thread=False)
        if init:
            self._init_db()

    def _init_db(self):
        cur = self.conn.cursor()
        cur.execute("CREATE TABLE outbox (k TEXT PRIMARY KEY, v TEXT)")
        cur.execute("CREATE TABLE offsets (topic TEXT PRIMARY KEY, val INTEGER)")
        self.conn.commit()

    def get(self, key: str) -> Optional[dict]:
        cur = self.conn.cursor()
        cur.execute("SELECT v FROM outbox WHERE k=?", (key,))
        row = cur.fetchone()
        if not row: return None
        return json.loads(row[0])

    def put(self, key: str, value: dict):
        cur = self.conn.cursor()
        cur.execute("INSERT OR REPLACE INTO outbox (k, v) VALUES (?, ?)", (key, json.dumps(value)))
        self.conn.commit()

    def next_offset(self, topic: str) -> int:
        cur = self.conn.cursor()
        cur.execute("SELECT val FROM offsets WHERE topic=?", (topic,))
        row = cur.fetchone()
        if row is None:
            cur.execute("INSERT INTO offsets(topic, val) VALUES(?, ?)", (topic, 0))
            self.conn.commit()
            return 0
        val = row[0] + 1
        cur.execute("UPDATE offsets SET val=? WHERE topic=?", (val, topic))
        self.conn.commit()
        return val
