# Transwing Lua 折叠角 MAVLink 反馈设计

- 日期：2026-09-18
- 状态：设计已确认（对话评审通过）
- 关联：`Transwing_折叠执行器_MAVLink回传说明.md`
- 改动文件：`scripts/transwing_dynamic_mix.lua`（原地增强，不新建主脚本）
- 板端固件：`G:\soft\折叠翼开发\firmware\wing_fold_actuator`（本设计不改板协议）

## 1. 目标与边界

### 1.1 目标

在现有动态混控 / 守卫 Lua 中，用折叠执行器经 UART 回传的 `NAMED_VALUE_FLOAT` 实测行程，替换（优先于）开环 `TW_RATE_*` 估角，使 `theta_est`、守卫与混控基于真实折叠位置。

### 1.2 非目标

- 不改板端 MAVLink 协议或字段名
- 不以 `fold_cnt` 作主反馈（仅日志）
- 不做开环+反馈融合滤波（方案 3）
- 不强制新增独立 sniff 脚本（台架手工验证即可）
- 不改变首飞默认「`Q_FRAME_CLASS=1`、暂不启 Lua 动态混控」的工程惯例；本设计仅定义脚本能力

### 1.3 已确认决策

| 项 | 选择 |
|----|------|
| 交付形态 | 原地改 `transwing_dynamic_mix.lua`，参数切换反馈/开环 |
| 反馈失效策略 | 立即回退开环 `theta_ol`，守卫/混控继续 |
| 默认与门控 | `TW_FB_EN` 默认开；`TW_FB_REQ` 默认开时无有效反馈禁止 CONTROL |
| 架构 | 双轨（开环轨始终跑）+ 选择器；反馈有效时对齐 `theta_ol` 避免回跳 |

## 2. 系统数据流

```text
飞控 SERVO(折叠通道) ──PWM──► 执行器          （指令）
执行器 USART3 ──MAVLink 251──► 飞控 SERIALn   （反馈）

Lua 每 tick:
  PWM ──► theta_target
       ──► theta_ol = step_theta_estimate(...)     // 开环轨始终更新

  mavlink receive ──► fold_pct / fold_cnt / fold_flt / fold_pwm / fold_hld
                   ──► last_rx_ms

  fb_ok = FB_EN
          AND 已收到过 fold_pct
          AND (now - last_rx_ms) <= FB_STALE
          AND fold_flt ~= 1
          AND fold_hld ~= 1

  if fb_ok:
      theta_est = clamp(fold_pct,0,100)/100 * THETA_MAX
      theta_ol  = theta_est                        // 对齐，回退不跳变
  else:
      theta_est = theta_ol

  evaluate_transition / 混控 / 现有日志 仍消费 theta_est
```

板协议要点（以回传说明为准）：

- msgid 251 `NAMED_VALUE_FLOAT`；五 name 轮询，单字段约 5 Hz
- 主反馈：`fold_pct` ∈ [0,100] → 度
- 必须 `mavlink:register_rx_msgid(251)`；name 去 `\0` 填充

## 3. 参数

扩展现有 `TW_` 表（当前 29 项之后追加；`add_table` 容量需 ≥ 33）：

| 参数 | 默认 | 含义 |
|------|------|------|
| `TW_FB_EN` | 1 | 允许使用板反馈 |
| `TW_FB_REQ` | 1 | 反馈无效时禁止进入 CONTROL / 电机接管 |
| `TW_FB_STALE` | 1000 | 无任一反馈帧超时（ms） |
| `TW_THETA_MAX` | 90 | `fold_pct/100 * THETA_MAX`（满行程度） |

保留：`TW_RATE_UP/DN`、`TW_TIMEOUT`、`TW_FOLD_CH`、`TW_PWM_FW/Q` 等现有参数（开环轨与指令映射仍需要）。

`TW_FB_EN=0`：永远走开环；此时 `fb_ok` 恒 false，若 `TW_FB_REQ=1` 则同样禁止 CONTROL。

## 4. CONTROL 门控

在现有 `can_takeover_motors` / CONTROL 路径上：

1. 若 `TW_FB_REQ ≥ 0.5` 且 `fb_ok == false`：
   - 禁止电机 `Motors_dynamic` 接管
   - 禁止 fold slew CONTROL 输出路径按「有效 CONTROL」执行
   - 用户将 `TW_MIX_MODE` 设为 2 时，运行时降为 MIRROR（或 OBSERVE），GCS 警告节流（避免刷屏）
2. `TW_FB_REQ=0`：允许无反馈进 CONTROL（开环行为，接近现状）
3. 现有 `|target - estimate| < 3` 等接管条件保留

已知取舍（已接受）：`fold_hld=1` 按失效回退开环时，`theta_ol` 可能仍向 `theta_target` 爬升，与机构 HOLD 短暂不一致；优先满足「可飞、可回退」，不做 HOLD 专用冻结策略（可后续加）。

## 5. 日志与地面站

- 新增 DataFlash：`TWFB` — `Pct,Cnt,Flt,Hld,Ok,Src`（`Src`：0=开环，1=反馈）
- 现有 `TWNG`/`TWTR` 的 `Est` 继续写最终 `theta_est`
- 可选低频 `gcs:send_named_float("TW_DEG", theta_est)`，仅观察，不参与控制

## 6. 超时与语义

- `|theta_target - theta_est| > 2` 且超过 `TW_TIMEOUT` 的现有报警：反馈模式下表示真实滞后；开环回退时语义与现在相同
- STALE 判据：任一 `fold_*` 帧刷新 `last_rx_ms`（不要求每帧都是 `fold_pct`）

## 7. 测试

### 7.1 宿主机

在 `transwing_lua_mix_model.mjs`（及 test）增加纯函数：

- `fbOk({en, lastRxMs, nowMs, staleMs, flt, hld, havePct})`
- `selectThetaEst({fbOk, foldPct, thetaMax, thetaOl})`（含对齐语义的说明/辅助）

不在 Node 中模拟真实 mavlink 收包。

### 7.2 文档

- 更新 `Transwing_折叠执行器_MAVLink回传说明.md`：Lua 差异表与验收勾选反映已接入
- 更新 `Transwing_Lua_动态混控仿真说明.md`：反馈参数与 `theta_est` 来源

### 7.3 台架 / 实机（人工）

1. `SERIALn` 接板，115200，PROTOCOL MAVLink；能周期性见 `fold_pct`
2. 手动动折叠：`theta_est` 与目视一致；`TWFB.Src=1`
3. 断线：STALE → `Src=0`，混控不沿用陈旧角
4. `fold_flt=1`：回退开环
5. `TW_FB_REQ=1` 且无反馈：无法进入有效 CONTROL

## 8. 实现顺序（供后续 plan）

1. 扩展 `TW_` 参数表与默认值
2. MAVLink 注册 / 收包 / name 解析状态机
3. `fb_ok` + `theta_est` 选择与 `theta_ol` 对齐
4. CONTROL / `can_takeover_motors` 门控与 GCS 提示
5. `TWFB` 日志与可选 `TW_DEG`
6. JS 模型单测 + 文档同步

## 9. 风险

| 风险 | 缓解 |
|------|------|
| 五字段轮询导致单字段仅 ~5 Hz | STALE 用「任一帧」刷新；混控角阶梯可接受 |
| HOLD 时开环漂移 | 已记录取舍；后续可对 hld 冻结 `theta_est` |
| `add_table` 容量不足 | 实现时把 table size 提到 ≥ 33 |
| SITL 无板 | `FB_EN=0` 或 `FB_REQ=0` 恢复可仿真路径 |
