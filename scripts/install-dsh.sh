#!/usr/bin/env bash
# 安装 FinAna v2 所需的 DeepSeek Harness (dsh) npm 运行时。
#
# 用法:
#   scripts/install-dsh.sh [目标目录]
#     目标目录默认 $DSH_NPM_DIR，再默认 /var/folders/67/w04136ns313_brc29bz4s1m40000gn/T/opencode/dsh-probe。
#     可传参覆盖（幂等：重复执行安全）。
#
# 版本钉子与安装策略（spike 实测结论，见 docs/superpowers/notes/dsh-spike.md）:
#   * 镜像 npmmirror；sdk-jsonrpc-server 的 peer 声明钉在 0.0.1-rc.5，与
#     dsh 0.1.1-rc.2 冲突，必须 --legacy-peer-deps 同树安装。
#   * --legacy-peer-deps 跳过自动装 peer：dsh-app-boot 运行时必需的
#     @deepseek-ai/cordis-plugin-group 以及组合内插件的传递 peer
#     （scope/invariants/shell/fs/timeout/compaction/sandbox/subagent-in-process-driver/
#     sdk-protocol/atomic-write/output-retention/anonymous-user-id）都会缺，
#     启动时报 ERR_MODULE_NOT_FOUND，故全部显式列出（幂等）。
#   * sdk-jsonrpc-server 是纯插件（无 bin）。可执行入口是
#     @deepseek-ai/dsh-sdk-jsonrpc-demo 的 packaged-bin.js——它把自身模块 URL
#     作为 bareModuleBaseUrl 传给 boot()，bare 插件从安装树解析，
#     相对路径仍相对配置文件；无需 deepseek-harness-runtime-bin 轮子。

set -euo pipefail

TARGET_DIR="${1:-${DSH_NPM_DIR:-/var/folders/67/w04136ns313_brc29bz4s1m40000gn/T/opencode/dsh-probe}}"
REGISTRY="${NPM_REGISTRY:-https://registry.npmmirror.com}"
RC="0.1.1-rc.2"

mkdir -p "$TARGET_DIR"
cd "$TARGET_DIR"

echo "==> npm install into $TARGET_DIR (registry=$REGISTRY)"
npm install \
  "@deepseek-ai/dsh@${RC}" \
  "@deepseek-ai/dsh-sdk-jsonrpc-server@0.0.1-rc.5" \
  "@deepseek-ai/dsh-sdk-jsonrpc-demo@${RC}" \
  "@deepseek-ai/cordis-plugin-group@^1.0.1" \
  "@deepseek-ai/dsh-agent-spine-demo@${RC}" \
  "@deepseek-ai/dsh-bash-local@${RC}" \
  "@deepseek-ai/dsh-mcp-client@${RC}" \
  "@deepseek-ai/dsh-llm-deepseek@${RC}" \
  "@deepseek-ai/dsh-subprocess-local@${RC}" \
  "@deepseek-ai/dsh-session-persistence-jsonl@${RC}" \
  "@deepseek-ai/dsh-session-checkpoint-policy@${RC}" \
  "@deepseek-ai/dsh-subagent@${RC}" \
  "@deepseek-ai/dsh-subagent-spawn-in-process@${RC}" \
  "@deepseek-ai/dsh-tool-subagent@${RC}" \
  "@deepseek-ai/dsh-tool-todo@${RC}" \
  "@deepseek-ai/dsh-fs-local@${RC}" \
  "@deepseek-ai/dsh-fs-observation-policy@${RC}" \
  "@deepseek-ai/dsh-tool-fs@${RC}" \
  "@deepseek-ai/dsh-token-meter@${RC}" \
  "@deepseek-ai/dsh-compaction-basic@${RC}" \
  "@deepseek-ai/dsh-scope@${RC}" \
  "@deepseek-ai/dsh-invariants@${RC}" \
  "@deepseek-ai/dsh-shell@${RC}" \
  "@deepseek-ai/dsh-fs@${RC}" \
  "@deepseek-ai/dsh-timeout@${RC}" \
  "@deepseek-ai/dsh-compaction@${RC}" \
  "@deepseek-ai/dsh-sandbox@${RC}" \
  "@deepseek-ai/dsh-subagent-in-process-driver@${RC}" \
  "@deepseek-ai/dsh-sdk-protocol@${RC}" \
  "@deepseek-ai/dsh-atomic-write@${RC}" \
  "@deepseek-ai/dsh-output-retention@${RC}" \
  "@deepseek-ai/dsh-anonymous-user-id@${RC}" \
  --legacy-peer-deps \
  --registry="$REGISTRY"

NODE_BIN="$(command -v node)"
DSH_BIN="$TARGET_DIR/node_modules/@deepseek-ai/dsh/lib/bin.js"
JSONRPC_BIN="$TARGET_DIR/node_modules/@deepseek-ai/dsh-sdk-jsonrpc-demo/lib/packaged-bin.js"

echo "==> 校验入口存在且可执行"
"$NODE_BIN" "$DSH_BIN" --version >/dev/null

echo ""
echo "==== 安装完成 ===="
echo "node 入口 (CLI):        $NODE_BIN $DSH_BIN"
echo "node 入口 (JSON-RPC):   $NODE_BIN $JSONRPC_BIN"
echo ""
echo "建议 Settings.dsh_npm_bin 值（单一可执行路径，wrapper 以 exec node 调用，需 node 在 PATH）:"
echo "  DSH_NPM_BIN=\"$JSONRPC_BIN\""
echo "启动示例（argv[2] 或 DSH_CORDIS_CONFIG 指向组合配置；node 需在 PATH）:"
echo "  node \"$JSONRPC_BIN\" <仓库根>/cordis.finana.yml"
echo "配套环境变量（FinAna 启动时自动注入，无需手动设置）:"
echo "  DSH_SYSTEM_PROMPT=<投研人格+预测格式，由 harness_adapter 注入>"
echo "  DSH_CWD=<仓库根>          # bash/fs/mcp-finana 的工作目录"
echo "  DSH_SESSION_ROOT=<会话根>  # 缺省 ./.sessions"
echo "  FINANA_PYTHON=<仓库根>/.venv/bin/python"
echo "  FINANA_SKILLS_DIR=<仓库根>/finana/prompts/skills"
