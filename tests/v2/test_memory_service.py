# tests/v2/test_memory_service.py
import sqlite3
import time

from finana.memory.service import MemoryService
from finana.prediction.parser import PredictionDraft
from finana.storage.db import connect


def _svc(tmp_path):
    return MemoryService(connect(tmp_path / "m.db"))


def test_instrument_upsert_twice_single_row_conclusions_appended(tmp_path):
    conn = connect(tmp_path / "m.db")
    svc = MemoryService(conn)
    svc.upsert_instrument("TSLA", name="特斯拉", sector="汽车")
    svc.upsert_instrument("TSLA", conclusion="基本面强劲")
    svc.upsert_instrument("TSLA", conclusion="短期波动放大" + "细节" * 150)
    info = svc.get_instrument("TSLA")
    assert info is not None
    assert info["name"] == "特斯拉"
    assert info["sector"] == "汽车"
    assert len(info["conclusions"]) == 2
    assert info["conclusions"][0]["text"] == "基本面强劲"
    assert len(info["conclusions"][1]["text"]) == 200
    assert info["price_anchors"] == []
    assert info["hit_total"] == 0
    assert info["hit_ok"] == 0
    assert svc.get_instrument("MISS") is None
    assert conn.execute("SELECT COUNT(*) FROM instrument_memory").fetchone()[0] == 1


def test_instrument_empty_name_sector_keeps_existing(tmp_path):
    svc = _svc(tmp_path)
    svc.upsert_instrument("AAPL", name="苹果", sector="消费电子")
    svc.upsert_instrument("AAPL", conclusion="生态护城河稳固")
    info = svc.get_instrument("AAPL")
    assert info["name"] == "苹果"
    assert info["sector"] == "消费电子"
    assert len(info["conclusions"]) == 1


def test_semantic_fts_hits_relevant_first_and_empty_query_latest_first(tmp_path):
    svc = _svc(tmp_path)
    id1 = svc.remember_semantic("美联储加息冲击成长股估值", tags="宏观", trace="t-1")
    svc.remember_semantic("特斯拉降价刺激销量 供应链承压", tags="汽车", trace="t-2")
    id3 = svc.remember_semantic("茅台年报稳健 白酒消费回暖", tags="白酒")
    assert isinstance(id1, int) and isinstance(id3, int)

    hits = svc.search_semantic("特斯拉 供应链")
    assert len(hits) == 1
    assert hits[0]["content"].startswith("特斯拉降价")
    assert hits[0]["tags"] == "汽车"
    assert set(hits[0]) >= {"id", "content", "tags", "created_at"}

    recent = svc.search_semantic("")
    contents = [h["content"] for h in recent]
    assert contents[0] == "茅台年报稳健 白酒消费回暖"
    assert contents[-1] == "美联储加息冲击成长股估值"

    limited = svc.search_semantic(None, k=1)
    assert len(limited) == 1


def test_profile_default_row_and_update_roundtrip(tmp_path):
    svc = _svc(tmp_path)
    profile = svc.get_profile()
    assert profile["risk_preference"] == ""
    assert profile["watchlist"] == []
    assert profile["feedback"] == []

    svc.update_profile(risk_preference="保守", watchlist=["TSLA", "NVDA"])
    svc.update_profile(feedback={"note": "太乐观"})
    updated = svc.get_profile()
    assert updated["risk_preference"] == "保守"
    assert updated["watchlist"] == ["TSLA", "NVDA"]
    assert updated["feedback"] == [{"note": "太乐观"}]

    svc.update_profile(unknown_field="ignored")
    assert svc.get_profile()["feedback"] == [{"note": "太乐观"}]


def test_save_prediction_due_window_boundaries(tmp_path):
    conn = connect(tmp_path / "m.db")
    svc = MemoryService(conn)
    now = time.time()
    draft_long = PredictionDraft(
        direction="up",
        confidence=0.8,
        target_low=210.0,
        target_high=260.0,
        horizon_days=30,
        invalidation=["跌破200日均线", "放量下跌"],
        rationale="需求强劲",
    )
    draft_short = PredictionDraft(direction="down", confidence=0.6, horizon_days=1)
    pid_long = svc.save_prediction(draft_long, "TSLA", trace_id="trace-1")
    pid_short = svc.save_prediction(draft_short, "NVDA")
    assert isinstance(pid_long, int)
    assert pid_short != pid_long

    early = svc.due_predictions(now + 2 * 86400)
    assert [p["symbol"] for p in early] == ["NVDA"]

    made_at = conn.execute("SELECT made_at FROM predictions WHERE symbol='NVDA'").fetchone()[0]
    exact_boundary = svc.due_predictions(made_at + 1 * 86400)
    assert [p["symbol"] for p in exact_boundary] == ["NVDA"]

    late = svc.due_predictions(made_at + 31 * 86400)
    assert sorted(p["symbol"] for p in late) == ["NVDA", "TSLA"]
    tsla = next(p for p in late if p["symbol"] == "TSLA")
    assert tsla["direction"] == "up"
    assert tsla["confidence"] == 0.8
    assert tsla["invalidation"] == ["跌破200日均线", "放量下跌"]
    assert tsla["rationale"] == "需求强劲"
    assert tsla["status"] == "pending"
    assert tsla["trace_id"] == "trace-1"

    conn.execute("UPDATE predictions SET status='done', verdict='命中' WHERE symbol='NVDA'")
    conn.commit()
    after = svc.due_predictions(made_at + 31 * 86400)
    assert [p["symbol"] for p in after] == ["TSLA"]


def test_session_bind_and_lookup(tmp_path):
    svc = _svc(tmp_path)
    assert svc.symbol_for_session("s1") is None
    svc.bind_session("s1", "TSLA")
    svc.bind_session("s2", "NVDA")
    svc.bind_session("s1", "AAPL")
    assert svc.symbol_for_session("s1") == "AAPL"
    assert svc.symbol_for_session("s2") == "NVDA"
    assert svc.symbol_for_session("ghost") is None


def test_build_context_block_empty_db_returns_empty_string(tmp_path):
    svc = _svc(tmp_path)
    assert svc.build_context_block("TSLA", "特斯拉走势如何") == ""
    assert svc.build_context_block("TSLA", "") == ""


def test_build_context_block_full_sections_within_cap(tmp_path):
    svc = _svc(tmp_path)
    svc.upsert_instrument(
        "TSLA",
        name="特斯拉",
        sector="汽车制造",
        conclusion="基本面强劲" + "补充论据" * 120,
    )
    svc.save_prediction(
        PredictionDraft(
            direction="up",
            confidence=0.75,
            target_low=200.0,
            target_high=260.0,
            horizon_days=14,
            invalidation=["跌破180"],
        ),
        "TSLA",
    )
    for i in range(3):
        svc.remember_semantic(f"特斯拉{i}号观察：趋势延续" + "走强" * 60, tags="汽车")
    svc.update_profile(risk_preference="进取", style="成长股", watchlist=["TSLA"])

    block = svc.build_context_block("TSLA", "特斯拉 供应链")
    assert len(block) <= 1200
    assert "[L2] 标的摘要" in block
    assert "待验证预测" in block
    assert "[L3] 相关记忆" in block
    assert "[L4] 用户画像" in block

    l3_section = block.split("[L3] 相关记忆：\n")[1].split("\n\n")[0]
    lines = [ln for ln in l3_section.split("\n") if ln]
    assert all(len(ln[2:]) <= 120 for ln in lines)


def test_build_context_block_one_sided_target_does_not_crash(tmp_path):
    svc = _svc(tmp_path)
    svc.upsert_instrument("TSLA", name="特斯拉")
    svc.save_prediction(
        PredictionDraft(
            direction="up",
            confidence=0.7,
            target_low=100.0,
            target_high=None,
            horizon_days=14,
            invalidation=["跌破90"],
        ),
        "TSLA",
    )

    block = svc.build_context_block("TSLA", "特斯拉走势")
    assert "≥100" in block


def test_find_symbol_by_name(tmp_path):
    svc = _svc(tmp_path)
    assert svc.find_symbol_by_name("贵州茅台") is None
    svc.upsert_instrument("600519.SH", name="贵州茅台")
    assert svc.find_symbol_by_name("贵州茅台") == "600519.SH"


def test_build_context_block_omits_missing_sections(tmp_path):
    svc = _svc(tmp_path)
    svc.remember_semantic("黄金 ETF 配置观点跟踪", tags="商品")

    assert svc.build_context_block("TSLA", "") == ""

    block = svc.build_context_block("MISS", "黄金 配置")
    assert "标的摘要" not in block
    assert "待验证预测" not in block
    assert "相关记忆" in block
    assert "用户画像" not in block
