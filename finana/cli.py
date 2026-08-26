from __future__ import annotations

import sys
import uuid

from finana.config import get_settings
from finana.harness_adapter import HarnessUnavailable
from finana.observability import init_logging
from finana.orchestrator import AnalysisResult, Orchestrator

_BANNER = "FinAna 投研助手 | 会话 {session_id} | 直接提问开始分析，/help 查看命令，/quit 退出"
_FAREWELL = "再见，祝投资顺利。"
_PROFILE_USAGE = "用法: /profile set risk=保守 style=趋势"

_HELP = """命令:
  /quit            退出
  /help            显示本帮助
  /new             开启新会话（更换 session id）
  /session         显示当前会话 ID
  /profile         查看当前用户画像
  /profile set risk=保守 style=趋势   更新用户画像"""

_PROFILE_FIELDS = {"risk": "risk_preference", "style": "style"}
_CARD_WIDTH = 34


def build_orchestrator() -> Orchestrator:
    return Orchestrator()


def parse_profile_args(raw: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    for token in raw.split():
        key, sep, value = token.partition("=")
        if not sep or not value:
            raise ValueError(f"参数需为 k=v 形式: {token}")
        field = _PROFILE_FIELDS.get(key)
        if field is None:
            raise ValueError(f"不支持的画像字段: {key}")
        fields[field] = value
    return fields


def render_result(res: AnalysisResult) -> str:
    if res.prediction is None:
        return res.response_md
    return res.response_md.rstrip() + "\n\n" + _prediction_card(res.prediction, res.prediction_id)


def _prediction_card(prediction, prediction_id: int | None) -> str:
    label = f"pred #{prediction_id}" if prediction_id is not None else "new"
    low, high = prediction.target_low, prediction.target_high
    target = f"{low} – {high}" if low is not None and high is not None else "-"
    invalidation = "; ".join(prediction.invalidation) if prediction.invalidation else "-"
    rows = [
        f"方向: {prediction.direction}   置信度: {prediction.confidence:.2f}",
        f"区间: {target}",
        f"期限: {prediction.horizon_days} 天   ID: {label}",
        f"失效条件: {invalidation}",
    ]
    lines = ["┌─ 预测 " + "─" * _CARD_WIDTH + "┐"]
    lines.extend("│ " + row.ljust(_CARD_WIDTH) + " │" for row in rows)
    lines.append("└" + "─" * (_CARD_WIDTH + 3) + "┘")
    return "\n".join(lines)


def main(argv: list[str] | None = None, factory=build_orchestrator) -> None:
    tokens = list(sys.argv[1:] if argv is None else argv)
    init_logging(get_settings())
    orchestrator = factory()
    if "--once" in tokens:
        idx = tokens.index("--once")
        query = " ".join(tokens[idx + 1 :]).strip()
        if not query:
            print('用法: --once "问题"', file=sys.stderr)
            sys.exit(2)
        sys.exit(_run_once(orchestrator, query))
    session_id = uuid.uuid4().hex
    sys.exit(_repl(orchestrator, session_id))


def _run_once(orchestrator, query: str) -> int:
    try:
        result = orchestrator.analyze(query)
    except HarnessUnavailable as exc:
        _print_harness_error(exc)
        return 2
    print(render_result(result))
    return 0


def _repl(orchestrator, session_id: str) -> int:
    print(_BANNER.format(session_id=session_id))
    while True:
        try:
            line = input("finana> ").strip()
        except (KeyboardInterrupt, EOFError):
            print()
            print(_FAREWELL)
            return 0
        if not line:
            continue
        if line in ("/quit", "/exit"):
            print(_FAREWELL)
            return 0
        if line == "/help":
            print(_HELP)
            continue
        if line == "/new":
            session_id = uuid.uuid4().hex
            print(f"新会话: {session_id}")
            continue
        if line == "/session":
            print(f"当前会话: {session_id}")
            continue
        if line.startswith("/profile"):
            _handle_profile(orchestrator, line[len("/profile") :].strip())
            continue
        if line.startswith("/accuracy"):
            _handle_accuracy(orchestrator, line[len("/accuracy") :].strip())
            continue
        if line.startswith("/"):
            print(f"未知命令: {line} (/help 查看可用命令)")
            continue
        try:
            result = orchestrator.analyze(line, session_id=session_id)
        except HarnessUnavailable as exc:
            _print_harness_error(exc)
            continue
        print(render_result(result))


def _handle_profile(orchestrator, rest: str) -> None:
    if not rest:
        profile = orchestrator.memory.get_profile()
        watchlist = ", ".join(profile.get("watchlist") or []) or "-"
        feedback_count = len(profile.get("feedback") or [])
        print(
            f"用户画像: risk={profile.get('risk_preference') or '-'} "
            f"style={profile.get('style') or '-'} "
            f"watchlist={watchlist} feedback={feedback_count} 条"
        )
        return
    parts = rest.split(None, 1)
    if parts[0] != "set" or len(parts) != 2:
        print(_PROFILE_USAGE)
        return
    try:
        fields = parse_profile_args(parts[1])
    except ValueError as exc:
        print(f"画像参数错误: {exc}")
        return
    if not fields:
        print(_PROFILE_USAGE)
        return
    orchestrator.memory.update_profile(**fields)
    rendered = ", ".join(f"{key}={value}" for key, value in fields.items())
    print(f"画像已更新: {rendered}")


def _print_harness_error(exc: HarnessUnavailable) -> None:
    tid = getattr(exc, "trace_id", "") or "本地未记录"
    print(f"分析失败(HarnessUnavailable): {exc} trace={tid}", file=sys.stderr)


def _handle_accuracy(orchestrator, rest: str) -> None:
    symbol = rest.strip() or None
    stats = orchestrator.memory.accuracy_stats(symbol)
    if stats["total"] == 0:
        print(f"暂无已验证预测（symbol={stats['symbol']}）")
        return
    rate = f"{stats['direction_hit_rate'] * 100:.1f}%"
    conf = f"{stats['avg_confidence']:.2f}" if stats["avg_confidence"] is not None else "-"
    print(
        f"命中率统计[symbol={stats['symbol']}]: "
        f"样本={stats['total']} 方向命中={stats['direction_hits']} "
        f"方向命中率={rate} 平均置信度={conf}"
    )
