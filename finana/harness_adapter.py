"""DeepSeek harness 适配器：懒构建 driver、结果归一化、崩溃重启重试。

启动 driver 时注入 DSH_SYSTEM_PROMPT（投研人格 + 预测格式）、FINANA_PYTHON
（MCP server 解释器绝对路径）、FINANA_SKILLS_DIR（skill 目录），确保真实运行
携带研究人格与数据工具；这些变量由 SDK 注入子进程环境。
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path

from finana.config import get_settings
from finana.observability import get_logger, get_metrics

log = get_logger("harness")


@dataclass
class AnalysisOutcome:
    """单次 harness 运行的归一化结果。"""

    final_response: str | None = None
    finish_reason: str | None = None
    usage: dict = field(default_factory=dict)
    session_id: str = ""


class HarnessUnavailable(Exception):
    """harness 重试后仍不可用，message 携带最后一次错误摘要，trace_id 可选关联。"""

    def __init__(self, message: str, trace_id: str = ""):
        super().__init__(message)
        self.trace_id = trace_id


def write_npm_wrapper(home: Path, npm_bin: Path) -> Path:
    """生成 dsh-jsonrpc shell wrapper（内容不变则不重写），返回脚本路径。"""
    home.mkdir(parents=True, exist_ok=True)
    bin_dir = home / "bin"
    bin_dir.mkdir(parents=True, exist_ok=True)
    wrapper = bin_dir / "dsh-jsonrpc"
    content = f'#!/bin/sh\nexec node "{npm_bin}" "$@"\n'
    if not wrapper.exists() or wrapper.read_text(encoding="utf-8") != content:
        wrapper.write_text(content, encoding="utf-8")
    wrapper.chmod(0o755)
    return wrapper


def _sum_usage(events) -> dict:
    """聚合 events 中 'assistant/message' 事件的 usage 数值字段，缺失返回 {}。"""
    total: dict = {}
    for event in events:
        if not isinstance(event, dict) or event.get("type") != "assistant/message":
            continue
        data = event.get("data")
        if not isinstance(data, dict) or not isinstance(data.get("usage"), dict):
            continue
        for key, value in data["usage"].items():
            if isinstance(value, bool):
                continue
            if isinstance(value, (int, float)):
                total[key] = total.get(key, 0) + value
    return total


class HarnessAdapter:
    """DeepSeekHarness 驱动适配器：失败时重启重建并重试一次。"""

    def __init__(self, settings=None):
        self.settings = settings or get_settings()
        self.driver = None

    def run(self, prompt: str, session_id: str) -> AnalysisOutcome:
        """执行一次运行；error/None finish_reason 或异常时重启重试一次，仍失败抛 HarnessUnavailable。"""
        last_error = ""
        for attempt in range(1, 3):
            try:
                if self.driver is None:
                    self.driver = self._build_driver()
                outcome = self._normalize(self.driver.run(prompt, session_id), session_id)
            except HarnessUnavailable:
                raise
            except Exception as exc:
                last_error = f"{type(exc).__name__}: {exc}"
                log.warning("attempt %s failed: %s", attempt, last_error)
                self._record(finish_reason="exception")
                self._restart()
                continue
            if outcome.finish_reason in ("error", None):
                last_error = f"finish_reason={outcome.finish_reason}"
                log.warning("attempt %s failed: %s", attempt, last_error)
            else:
                log.info("attempt %s finished with %s", attempt, outcome.finish_reason)
            self._record(finish_reason=outcome.finish_reason)
            if outcome.finish_reason not in ("error", None):
                return outcome
            self._restart()
        raise HarnessUnavailable(f"harness 连续两次运行失败；最后错误：{last_error}")

    def close(self) -> None:
        """关闭底层 driver（若支持 close）并释放引用。"""
        driver, self.driver = self.driver, None
        if driver is not None and hasattr(driver, "close"):
            try:
                driver.close()
            except Exception as exc:
                log.warning("driver close failed: %s", exc)

    def _record(self, finish_reason: str | None) -> None:
        """记录一条 harness.run 指标样本。"""
        get_metrics().record("harness.run", 1, finish_reason=str(finish_reason))

    def _restart(self) -> None:
        """关闭并丢弃当前 driver，下次 run 时懒重建。"""
        self.close()

    def _normalize(self, result, session_id: str) -> AnalysisOutcome:
        """将 SDK RunResult 或 FakeHarness 的 AnalysisOutcome 归一化。"""
        if isinstance(result, AnalysisOutcome):
            result.session_id = result.session_id or session_id
            return result
        events = getattr(result, "events", None) or []
        return AnalysisOutcome(
            final_response=getattr(result, "final_response", None),
            finish_reason=getattr(result, "finish_reason", None),
            usage=_sum_usage(events),
            session_id=session_id,
        )

    def _repo_root(self) -> Path:
        """返回仓库根目录（cordis 配置所在处）。"""
        return Path(__file__).resolve().parent.parent

    def _workspace_dir(self) -> Path:
        """确保并返回 workspace 目录。"""
        workspace = self.settings.finana_home.expanduser() / "workspace"
        workspace.mkdir(parents=True, exist_ok=True)
        return workspace

    def _build_driver(self):
        """按 settings.dsh_runtime 分派构建 wheel/npm 驱动，auto 先 wheel 后 npm。"""
        runtime = self.settings.dsh_runtime
        if runtime == "npm":
            return self._build_npm()
        if runtime == "wheel":
            return self._build_wheel()
        try:
            return self._build_wheel()
        except Exception as exc:
            log.warning("wheel 构建失败，回退 npm：%s", exc)
            return self._build_npm()

    def _build_env(self) -> dict:
        """注入真实运行必需的子进程环境变量：研究人格、MCP 解释器、skill 目录。"""
        from finana.prompts.loader import load_system_prompt

        return {
            "DSH_SYSTEM_PROMPT": load_system_prompt(),
            "FINANA_PYTHON": sys.executable,
            "FINANA_SKILLS_DIR": str(self._repo_root() / "finana" / "prompts" / "skills"),
        }

    def _build_wheel(self):
        """通过已安装的 deepseek_harness 包构建驱动。"""
        from deepseek_harness import DeepSeekHarness

        return DeepSeekHarness(
            provider="deepseek-official",
            model=self.settings.dsh_model,
            max_tokens=self.settings.dsh_max_tokens,
            cwd=str(self._workspace_dir()),
            session_root=str(self.settings.sessions_dir.expanduser()),
            cordis=str(self._repo_root() / "cordis.finana.yml"),
            env=self._build_env(),
            api_key=self.settings.deepseek_api_key or None,
            base_url=self.settings.deepseek_base_url or None,
        )

    def _build_npm(self):
        """通过生成的 jsonrpc wrapper 脚本构建驱动；缺 DSH_NPM_BIN 时抛 HarnessUnavailable。"""
        npm_bin = self.settings.dsh_npm_bin
        if npm_bin is None:
            raise HarnessUnavailable("npm 模式需要设置 DSH_NPM_BIN")
        from deepseek_harness import DeepSeekHarness

        wrapper = write_npm_wrapper(
            self.settings.finana_home.expanduser(), Path(npm_bin).expanduser()
        )
        return DeepSeekHarness(
            provider="deepseek-official",
            model=self.settings.dsh_model,
            max_tokens=self.settings.dsh_max_tokens,
            cwd=str(self._workspace_dir()),
            session_root=str(self.settings.sessions_dir.expanduser()),
            cordis=str(self._repo_root() / "cordis.finana.yml"),
            runtime_bin=str(wrapper),
            env=self._build_env(),
            api_key=self.settings.deepseek_api_key or None,
            base_url=self.settings.deepseek_base_url or None,
        )


class FakeHarness:
    """测试替身：按预设 outcomes 依次返回（耗尽后重复最后一个），记录调用。"""

    def __init__(self, outcomes: list[AnalysisOutcome]):
        if not outcomes:
            raise ValueError("FakeHarness 至少需要一个预设 outcome")
        self.outcomes = list(outcomes)
        self.calls: list[tuple[str, str]] = []
        self.closed = False

    def run(self, prompt: str, session_id: str) -> AnalysisOutcome:
        """弹出下一个预设结果并记录调用。"""
        if len(self.outcomes) > 1:
            outcome = self.outcomes.pop(0)
        else:
            outcome = self.outcomes[0]
        self.calls.append((prompt, session_id))
        return outcome

    def close(self) -> None:
        """标记已关闭。"""
        self.closed = True
