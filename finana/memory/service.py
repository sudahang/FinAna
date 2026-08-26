from __future__ import annotations

import datetime
import json
import sqlite3
import time

from finana.prediction.parser import PredictionDraft

_L2_SUMMARY_LIMIT = 400
_L3_LINE_LIMIT = 120
_L3_TOTAL_LIMIT = 600
_BLOCK_LIMIT = 1200


def _clip(text: str, limit: int) -> str:
    return text if len(text) <= limit else text[:limit]


def _prediction_dict(row: sqlite3.Row) -> dict:
    d = dict(row)
    d["invalidation"] = json.loads(d.pop("invalidation_json"))
    return d


def _instrument_summary(inst: dict) -> str:
    parts = [inst["symbol"]]
    if inst["name"]:
        parts.append(inst["name"])
    if inst["sector"]:
        parts.append(inst["sector"])
    summary = "｜".join(parts)
    recent = inst.get("conclusions") or []
    if recent:
        joined = "；".join(f"{c['date']} {c['text']}" for c in recent[-3:])
        summary += "｜近期结论：" + joined
    return _clip(summary, _L2_SUMMARY_LIMIT)


def _prediction_line(p: dict) -> str:
    low, high = p["target_low"], p["target_high"]
    if low is not None and high is not None:
        target = f"{low:g}~{high:g}"
    elif low is not None:
        target = f"≥{low:g}"
    elif high is not None:
        target = f"≤{high:g}"
    else:
        target = "-"
    invalidation = "/".join(p["invalidation"]) or "-"
    return (
        f"- {p['direction']} 置信度{p['confidence']:.2f} 目标{target} "
        f"周期{p['horizon_days']}天 失效:{invalidation}"
    )


class MemoryService:
    """基于 SQLite 的分层记忆服务：标的、语义、画像、会话与预测。"""

    def __init__(self, conn: sqlite3.Connection):
        self._conn = conn

    def upsert_instrument(
        self,
        symbol: str,
        name: str = "",
        sector: str = "",
        conclusion: str | None = None,
    ) -> None:
        """插入或更新标的信息，conclusion 提供时追加为带日期的结论文本。"""
        row = self._conn.execute(
            "SELECT name, sector, conclusions_json FROM instrument_memory WHERE symbol=?",
            (symbol,),
        ).fetchone()
        if row is None:
            cur_name, cur_sector, conclusions = "", "", []
        else:
            cur_name, cur_sector = row["name"], row["sector"]
            conclusions = json.loads(row["conclusions_json"])
        if name:
            cur_name = name
        if sector:
            cur_sector = sector
        if conclusion is not None and conclusion != "":
            conclusions.append(
                {"date": datetime.date.today().isoformat(), "text": conclusion[:200]}
            )
        self._conn.execute(
            """INSERT INTO instrument_memory (symbol, name, sector, conclusions_json, updated_at)
               VALUES (?, ?, ?, ?, strftime('%s','now'))
               ON CONFLICT(symbol) DO UPDATE SET
                 name=excluded.name,
                 sector=excluded.sector,
                 conclusions_json=excluded.conclusions_json,
                 updated_at=excluded.updated_at""",
            (symbol, cur_name, cur_sector, json.dumps(conclusions, ensure_ascii=False)),
        )
        self._conn.commit()

    def get_instrument(self, symbol: str) -> dict | None:
        """返回标的信息字典（结论与价格锚点已反序列化），不存在时返回 None。"""
        row = self._conn.execute(
            "SELECT * FROM instrument_memory WHERE symbol=?", (symbol,)
        ).fetchone()
        if row is None:
            return None
        d = dict(row)
        d["conclusions"] = json.loads(d.pop("conclusions_json"))
        d["price_anchors"] = json.loads(d.pop("price_anchors_json"))
        return d

    def find_symbol_by_name(self, name: str) -> str | None:
        """按标的名称精确匹配返回代码，不存在时返回 None。"""
        row = self._conn.execute(
            "SELECT symbol FROM instrument_memory WHERE name=?", (name,)
        ).fetchone()
        return row["symbol"] if row is not None else None

    def find_symbol_by_substring(self, text: str) -> str | None:
        """返回名称作为子串出现在 text 中的标的代码，不存在时返回 None。"""
        row = self._conn.execute(
            "SELECT symbol FROM instrument_memory WHERE name<>'' AND ? LIKE '%'||name||'%' LIMIT 1",
            (text,),
        ).fetchone()
        return row["symbol"] if row is not None else None

    def remember_semantic(self, content: str, tags: str = "", trace: str = "") -> int:
        """写入一条语义记忆并返回其行 id。"""
        cur = self._conn.execute(
            "INSERT INTO semantic_memory (content, tags, source_trace) VALUES (?, ?, ?)",
            (content, tags, trace),
        )
        self._conn.commit()
        return int(cur.lastrowid)

    def search_semantic(self, query: str | None, k: int = 5) -> list[dict]:
        """按 FTS5 相关性检索语义记忆，空查询回退最近 k 条。"""
        q = (query or "").strip()
        if not q:
            rows = self._conn.execute(
                "SELECT id, content, tags, created_at FROM semantic_memory "
                "ORDER BY created_at DESC, id DESC LIMIT ?",
                (k,),
            ).fetchall()
            return [dict(r) for r in rows]
        match = " OR ".join(
            f'"{term.replace(chr(34), chr(34) * 2)}"*' for term in q.split()
        )
        rows = self._conn.execute(
            "SELECT m.id AS id, m.content AS content, m.tags AS tags, m.created_at AS created_at "
            "FROM semantic_fts f JOIN semantic_memory m ON m.id = f.rowid "
            "WHERE semantic_fts MATCH ? ORDER BY rank LIMIT ?",
            (match, k),
        ).fetchall()
        return [dict(r) for r in rows]

    def get_profile(self) -> dict:
        """返回默认用户画像，缺失时自动创建 default 行。"""
        row = self._profile_row(create=True)
        return {
            "user_id": row["user_id"],
            "risk_preference": row["risk_preference"],
            "style": row["style"],
            "watchlist": json.loads(row["watchlist_json"]),
            "feedback": json.loads(row["feedback_json"]),
            "updated_at": row["updated_at"],
        }

    def update_profile(self, **fields) -> None:
        """按白名单更新默认画像：risk_preference/style 覆盖，watchlist 覆盖，feedback 追加。"""
        row = self._profile_row(create=True)
        sets: dict[str, object] = {}
        if fields.get("risk_preference"):
            sets["risk_preference"] = fields["risk_preference"]
        if fields.get("style"):
            sets["style"] = fields["style"]
        if isinstance(fields.get("watchlist"), list):
            sets["watchlist_json"] = json.dumps(fields["watchlist"], ensure_ascii=False)
        feedback_value = fields.get("feedback")
        if isinstance(feedback_value, (dict, list)):
            current = json.loads(row["feedback_json"])
            if isinstance(feedback_value, list):
                current.extend(feedback_value)
            else:
                current.append(feedback_value)
            sets["feedback_json"] = json.dumps(current, ensure_ascii=False)
        if not sets:
            return
        sets["updated_at"] = time.time()
        assignment = ", ".join(f"{key}=?" for key in sets)
        self._conn.execute(
            f"UPDATE user_profile SET {assignment} WHERE user_id='default'",
            tuple(sets.values()),
        )
        self._conn.commit()

    def bind_session(self, session_id: str, symbol: str) -> None:
        """绑定会话与标的，重复绑定时覆盖。"""
        self._conn.execute(
            """INSERT INTO session_index (session_id, symbol, updated_at)
               VALUES (?, ?, strftime('%s','now'))
               ON CONFLICT(session_id) DO UPDATE SET
                 symbol=excluded.symbol, updated_at=excluded.updated_at""",
            (session_id, symbol),
        )
        self._conn.commit()

    def symbol_for_session(self, session_id: str) -> str | None:
        """返回会话绑定的标的代码，未绑定时返回 None。"""
        row = self._conn.execute(
            "SELECT symbol FROM session_index WHERE session_id=?", (session_id,)
        ).fetchone()
        return row["symbol"] if row is not None else None

    def save_prediction(self, d: PredictionDraft, symbol: str, trace_id: str = "") -> int:
        """保存一条 pending 状态的预测草稿并返回其 id。"""
        cur = self._conn.execute(
            """INSERT INTO predictions
               (trace_id, symbol, made_at, direction, confidence, target_low, target_high,
                horizon_days, invalidation_json, rationale, status)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending')""",
            (
                trace_id,
                symbol,
                time.time(),
                d.direction,
                d.confidence,
                d.target_low,
                d.target_high,
                d.horizon_days,
                json.dumps(d.invalidation, ensure_ascii=False),
                d.rationale,
            ),
        )
        self._conn.commit()
        return int(cur.lastrowid)

    def due_predictions(self, now: float) -> list[dict]:
        """返回已到期且仍处于 pending 状态的预测列表。"""
        rows = self._conn.execute(
            "SELECT * FROM predictions WHERE status='pending' "
            "AND made_at + horizon_days*86400 <= ? ORDER BY prediction_id",
            (now,),
        ).fetchall()
        return [_prediction_dict(r) for r in rows]

    def build_context_block(self, symbol: str, user_query: str) -> str:
        """组装带 L2/L3/L4 标注的记忆上下文块，整体不超过 1200 字符。"""
        sections: list[str] = []
        inst = self.get_instrument(symbol)
        if inst is not None:
            sections.append("[L2] 标的摘要：" + _instrument_summary(inst))
        preds = self._conn.execute(
            "SELECT * FROM predictions WHERE symbol=? AND status='pending' "
            "ORDER BY prediction_id DESC",
            (symbol,),
        ).fetchall()
        if preds:
            lines = [_prediction_line(_prediction_dict(p)) for p in preds]
            sections.append("[L2] 待验证预测：\n" + "\n".join(lines))
        query = (user_query or "").strip()
        if query:
            memory_lines: list[str] = []
            total = 0
            for item in self.search_semantic(query, k=5):
                text = "- " + _clip(item["content"], _L3_LINE_LIMIT)
                if total + len(text) > _L3_TOTAL_LIMIT:
                    break
                memory_lines.append(text)
                total += len(text)
            if memory_lines:
                sections.append("[L3] 相关记忆：\n" + "\n".join(memory_lines))
        profile_row = self._profile_row()
        if profile_row is not None:
            bits = []
            if profile_row["risk_preference"]:
                bits.append(f"风险偏好={profile_row['risk_preference']}")
            if profile_row["style"]:
                bits.append(f"风格={profile_row['style']}")
            watchlist = json.loads(profile_row["watchlist_json"])
            if watchlist:
                bits.append("关注=" + ",".join(watchlist))
            if bits:
                sections.append("[L4] 用户画像：" + "；".join(bits))
        if not sections:
            return ""
        return _clip("\n\n".join(sections), _BLOCK_LIMIT)

    def _profile_row(self, create: bool = False) -> sqlite3.Row | None:
        row = self._conn.execute(
            "SELECT * FROM user_profile WHERE user_id='default'"
        ).fetchone()
        if row is None and create:
            self._conn.execute("INSERT INTO user_profile (user_id) VALUES ('default')")
            self._conn.commit()
            row = self._conn.execute(
                "SELECT * FROM user_profile WHERE user_id='default'"
            ).fetchone()
        return row
