# 预测输出格式（Prediction Format）

报告正文结束后，必须在最后一个代码围栏中输出如下结构的预测 JSON：

```json
{"direction": "up|down|sideways", "confidence": 0.0-1.0, "target_low": 可选, "target_high": 可选, "horizon_days": 正整数, "invalidation": ["失效条件1", ...], "rationale": "一句话核心论据"}
```

## 字段说明

| 字段 | 类型 | 含义 | 约束 |
|------|------|------|------|
| direction | string | 方向判断 | 只能取 up / down / sideways 三选一 |
| confidence | number | 置信度 | 0.0-1.0 |
| target_low | number | 目标区间下沿 | 可选；给出时须小于 target_high |
| target_high | number | 目标区间上沿 | 可选；给出时须大于 target_low |
| horizon_days | int | 预测有效期 | 正整数，单位天 |
| invalidation | string[] | 失效条件列表 | 可为空数组；每条须可观察、可验证 |
| rationale | string | 核心论据 | 一句话 |

## 完整示例

```json
{
  "direction": "up",
  "confidence": 0.62,
  "target_low": 1680.0,
  "target_high": 1850.0,
  "horizon_days": 30,
  "invalidation": ["跌破 60 日均线且放量", "北向资金连续五个交易日净流出"],
  "rationale": "批价企稳叠加资金回流，估值处于近三年低位"
}
```

## 规则

- JSON 必须合法，可被 `json.loads` 解析。
- 预测块必须放在报告最后一个代码围栏中，其后不得再出现其他围栏块。
- direction 只能三选一：up / down / sideways。
- 确实无法给出方向判断时可省略整个块，但须在报告中说明原因。
