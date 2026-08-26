# dsh npm Spike 校准报告（Task 7, FinAna v2 Plan 2）

日期: 2026-08-26 · 环境: macOS darwin, node v24.15.0, probe 树 `/var/folders/67/w04136ns313_brc29bz4s1m40000gn/T/opencode/dsh-probe`
约束: 全程零 LLM API 调用（initialize/shutdown 为协议层握手，无需 key）。

## 结论（推荐启动命令）

**Route A 成立，且比预期更简单：`@deepseek-ai/dsh-sdk-jsonrpc-server` 是纯 cordis 插件（无 bin），真正的可执行入口是 `@deepseek-ai/dsh-sdk-jsonrpc-demo@0.1.1-rc.2` 的 `lib/packaged-bin.js`——它把自身模块 URL 作为 `bareModuleBaseUrl` 传给 `boot()`，bare 插件名从安装树解析，相对路径相对配置文件，因此无需 deepseek-harness-runtime-bin 轮子、也无需再包一层 wrapper。**

推荐的 `DSH_NPM_BIN`（Settings 留空由用户填）：

```
DSH_NPM_BIN="<node 绝对路径> <安装目录>/node_modules/@deepseek-ai/dsh-sdk-jsonrpc-demo/lib/packaged-bin.js"
```

启动（argv[2] 与 `$DSH_CORDIS_CONFIG` 二选一，前者会被后者覆盖）：

```bash
env -u DEEPSEEK_API_KEY \
  DSH_SYSTEM_PROMPT=<loader 注入的系统提示词> \
  DSH_CWD=<仓库根> \
  DSH_SESSION_ROOT=<会话根> \
  FINANA_PYTHON=<仓库根>/.venv/bin/python \
  FINANA_SKILLS_DIR=<仓库根>/finana/prompts/skills \
  "$DSH_NPM_BIN" <仓库根>/cordis.finana.yml
```

注意：generic `lib/bin.js` 不传 bareModuleBaseUrl，要求"配置项目自己拥有插件包"，在 FinAna-v2p2 下必然 ERR_MODULE_NOT_FOUND；必须用 `packaged-bin.js`。

## 握手证据（spike b）

命令（cwd=仓库根，stdin 两帧 JSON-RPC，无 DEEPSEEK_API_KEY）：

```bash
printf '%s\n' \
  '{"jsonrpc":"2.0","id":"1","method":"initialize","params":{"cwd":"<repo>","provider":"deepseek-official","model":"deepseek-v4-flash"}}' \
  '{"jsonrpc":"2.0","id":"2","method":"shutdown"}' \
  | node <probe>/node_modules/@deepseek-ai/dsh-sdk-jsonrpc-demo/lib/packaged-bin.js <repo>/cordis.finana.yml
```

stdout 实际输出（exit=0）：

```json
{"jsonrpc":"2.0","id":"1","result":{"serverInfo":{"name":"deepseek-harness-sdk-runtime","version":"0.0.1"}}}
{"jsonrpc":"2.0","id":"2","result":{}}
```

stderr 无错误；组合内全部插件（含 agent-spine/sessions/mcp-finana 段的 `!!js` 表达式求值）加载成功。

## 安装要点（spike a/c）

1. **同树 + `--legacy-peer-deps`**：sdk-jsonrpc-server 的 peer 钉在 0.0.1-rc.5，与 dsh 0.1.1-rc.2 冲突，单独装 ERESOLVE。
2. **peer 缺失要显式补**：`--legacy-peer-deps` 会跳过 peer 自动安装。实测逐轮补齐了：
   `@deepseek-ai/cordis-plugin-group`（dsh-app-boot 运行时硬依赖）、
   `dsh-agent-spine-demo`、`dsh-bash-local`、`dsh-mcp-client`（组合直接引用）、
   以及传递 peer `dsh-scope / dsh-invariants / dsh-shell / dsh-fs / dsh-timeout /
   dsh-compaction / dsh-sandbox / dsh-subagent-in-process-driver / dsh-sdk-protocol /
   dsh-atomic-write / dsh-output-retention / dsh-anonymous-user-id`（均 0.1.1-rc.2）。
   全部固化进 `scripts/install-dsh.sh`（幂等，重跑已验证）。
3. **首次把 sdk-jsonrpc-server 装进既有 probe 树会把 npm 重解析后的树打碎**
   （197 → ~179 包，dsh CLI 一度报缺 cordis-plugin-group）；按上面清单一次性
   显式安装后恢复稳定。脚本采用"一次 install 带全量清单"，避免该坑。
4. `dsh --patch cordis.finana.yml --dump-config` 会 exit 0 但告警
   `entry "xxx" not found`——`--patch` 只做 id 定向覆盖/插入，不是独立组合加载器；
   本配置是完整组合叶，只能经 jsonrpc-demo bin 启动。headless profile 组合
   （`~/.dsh/profiles/headless` 经 `--dump-default-config` 导出）仅作键名参考，
   不是本任务的运行目标。

## 键名实测（spike 要求的 README grep）

| 配置点 | 结论 | 出处 |
|---|---|---|
| MCP 插件 | `name: '@deepseek-ai/dsh-mcp-client'`，config: `serverName/transport/command/args/env/cwd/failOnStartupError/reconnect.*` | 包 README Config 表 |
| MCP 工具名 | `mcp__finana__<rawName>`（serverName 命名空间） | 同上 |
| skills 开关+目录 | agent-spine `skills.enabled`；目录键为 `skills.filesystem.customSkillDirs[]`（spine SkillConfig → dsh-skill-filesystem） | spine types/index.d.ts + skill-filesystem README |
| sessions 压缩 | `compression: !!js "process.env.DSH_SNAPSHOT === undefined ? 'zstd' : 'none'"`（快照回读用 raw JSONL） | 官方示例原样保留 |

## 官方示例基底

基底取自上游 `examples/jsonrpc-agent/cordis.yml`（master 分支全文抓取）：
含 sdk-jsonrpc-server / llm-deepseek / subprocess / bash / agent-spine / sessions /
session-checkpoints / subagent(+spawn-in-process/tool-subagent) / tool-todo /
fs-local / fs-observation-policy / tool-fs / token-meter / compaction-basic ——与
任务要求的保留段一一对应。改动点：persona 兜底改为 `'You are a helpful assistant.'`、
skills.enabled:true + customSkillDirs(FINANA_SKILLS_DIR)、bash.timeoutMs→120000、
追加 mcp-finana 段（command=FINANA_PYTHON??'.venv/bin/python', cwd=DSH_CWD??process.cwd(),
failOnStartupError:false）。minimal.cordis.yml 未被用作基底（其不含 checkpoints/subagent/token-meter 等必需段）。

## 测试说明（ruling 执行记录）

`!!js` 会使 PyYAML `yaml.safe_load` 抛 ConstructorError。按 ruling 采用折中方案：
测试内定义 `JsTagLoader(yaml.SafeLoader)`，multi-constructor 把
`tag:yaml.org,2002:js` 降级为字符串文本——其余解析语义与 safe_load 完全一致，
结构断言（id 集合/serverName==finana/transport==stdio/timeoutMs==120000）照常成立，
`!!js` 表达式以源码文本参与子串断言。非纯 text 锚点，结构校验得以保留。

## 降级路线 B（未触发，备案）

若未来 packaged-bin 入口不可用：`dsh --profile headless "ping"` 可验证 CLI 启动链
（报缺 DEEPSEEK_API_KEY 即链路 OK）。本轮 Route A 已实测通过，无需降级。

## 遗留关注

- `mcp-finana` 挂载成功性依赖 finana.mcp_server.server 可导入（Task 内 failOnStartupError:false 已兜底）；MCP initialize/tools-list 层面的联通属 Task 8 adapter 集成范围。
- npm 树对 `--legacy-peer-deps` 敏感：升级 dsh 版本时需重新核对 peer 清单。
