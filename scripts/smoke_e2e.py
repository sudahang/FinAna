"""FinAna v2 live 冒烟脚本。

运行前提：DEEPSEEK_API_KEY 已配置、npm dsh 安装完成（scripts/install-dsh.sh）、
`python -m finana doctor` 检查全部通过。在仓库根目录执行：python scripts/smoke_e2e.py
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from finana.config import get_settings
from finana.orchestrator import Orchestrator

_QUERY = "贵州茅台近期走势如何？"


def main() -> int:
    """缺 DEEPSEEK_API_KEY 时打印 SKIP 退出 0，否则跑一次 analyze 并校验结果。"""
    if not get_settings().deepseek_api_key:
        print("SKIP: DEEPSEEK_API_KEY 未配置，跳过 live 冒烟")
        return 0
    started = time.perf_counter()
    result = Orchestrator().analyze(_QUERY)
    elapsed = time.perf_counter() - started
    if not result.response_md:
        print("FAIL: response_md 为空", file=sys.stderr)
        return 1
    if result.prediction is not None:
        print(
            f"prediction: {result.prediction.direction} "
            f"confidence={result.prediction.confidence:.2f}"
        )
    else:
        print("prediction: 无（模型未输出可解析预测）")
    print(f"OK: 耗时 {elapsed:.1f}s trace_id={result.trace_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
