"""cordis.finana.yml 组合配置契约测试。

dsh 的 cordis.yml 大量使用 ``!!js`` 表达式（运行时由 dsh 的 cordis loader 求值）。
PyYAML 的 safe_load 遇到未知 tag 会抛 ConstructorError，因此这里用一个继承
SafeLoader 的容错 Loader：把未知 tag 的标量按字符串读入，其余解析语义与
safe_load 完全一致。!!js 表达式以源码文本形式参与断言。
"""

from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = REPO_ROOT / "cordis.finana.yml"

REQUIRED_ENTRY_IDS = {
    "sdk-jsonrpc-server",
    "llm-deepseek",
    "subprocess",
    "bash",
    "agent-spine",
    "sessions",
    "session-checkpoints",
    "subagent",
    "fs-local",
    "tool-fs",
    "tool-todo",
    "token-meter",
    "compaction-basic",
    "mcp-finana",
}


class JsTagLoader(yaml.SafeLoader):
    """safe_load 语义 + 把未知 tag（!!js 等）降级为字面文本。"""


def _unknown_tag(loader, suffix, node):
    if isinstance(node, yaml.ScalarNode):
        return loader.construct_scalar(node)
    if isinstance(node, yaml.SequenceNode):
        return loader.construct_sequence(node)
    return loader.construct_mapping(node)


JsTagLoader.add_multi_constructor("tag:yaml.org,2002:js", _unknown_tag)


def load_composition() -> dict:
    assert CONFIG_PATH.exists(), f"缺少组合配置文件: {CONFIG_PATH}"
    with CONFIG_PATH.open(encoding="utf-8") as fh:
        data = yaml.load(fh, Loader=JsTagLoader)
    assert isinstance(data, list) and data, "cordis.finana.yml 应为非空 entry 列表"
    ids = [entry.get("id") for entry in data]
    assert len(ids) == len(set(ids)), f"entry id 重复: {ids}"
    return {entry["id"]: entry for entry in data}


def test_composition_parses_and_contains_required_entries():
    entries = load_composition()
    missing = REQUIRED_ENTRY_IDS - set(entries)
    assert not missing, f"缺少必需 entry: {sorted(missing)}"


def test_agent_spine_persona_uses_env_injection():
    spine = load_composition()["agent-spine"]
    assert spine["name"] == "@deepseek-ai/dsh-agent-spine-demo"
    persona = spine["config"]["persona"]
    assert "DSH_SYSTEM_PROMPT" in persona
    assert "You are a helpful assistant." in persona


def test_agent_spine_skills_enabled_with_finana_dir():
    skills = load_composition()["agent-spine"]["config"]["skills"]
    assert skills["enabled"] is True
    dirs = skills["filesystem"]["customSkillDirs"]
    assert any("FINANA_SKILLS_DIR" in d and "./finana/prompts/skills" in d for d in dirs)


def test_sessions_root_env_injected_and_snapshot_compression():
    sessions = load_composition()["sessions"]
    assert sessions["name"] == "@deepseek-ai/dsh-session-persistence-jsonl"
    assert "DSH_SESSION_ROOT" in sessions["config"]["root"]
    assert "DSH_SNAPSHOT" in sessions["config"]["compression"]


def test_bash_timeout_is_120s():
    bash = load_composition()["bash"]
    assert bash["name"] == "@deepseek-ai/dsh-bash-local"
    assert bash["config"]["timeoutMs"] == 120000


def test_mcp_finana_stdio_server():
    mcp = load_composition()["mcp-finana"]
    config = mcp["config"]
    assert mcp["name"] == "@deepseek-ai/dsh-mcp-client"
    assert config["serverName"] == "finana"
    assert config["transport"] == "stdio"
    assert config["args"] == ["-m", "finana.mcp_server.server"]
    assert "FINANA_PYTHON" in config["command"]
    assert ".venv/bin/python" in config["command"]
    assert config["failOnStartupError"] is False


def test_jsonrpc_server_entry_present():
    server = load_composition()["sdk-jsonrpc-server"]
    assert server["name"] == "@deepseek-ai/dsh-sdk-jsonrpc-server"


def test_llm_deepseek_adapter_present():
    llm = load_composition()["llm-deepseek"]
    assert llm["name"] == "@deepseek-ai/dsh-llm-deepseek"
