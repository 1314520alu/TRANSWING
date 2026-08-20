# Transwing 模式转换与保护说明

本文档说明 Transwing 倾转/折叠无人机在不同**飞行模式**、**过渡相位**与 **Lua 混控模式**下的转换过程，以及 `transwing_dynamic_mix.lua` 过渡守卫的**保护条件**与**响应动作**。

**相关文件**

| 文件 | 说明 |
|------|------|
| `scripts/transwing_dynamic_mix.lua` | Lua 脚本（29 个 `TW_*` 参数） |
| `Transwing_Lua_动态混控仿真说明.md` | TW 参数逐项说明 |
| `Transwing_守卫动作说明.md` | ALLOW / HOLD / ABORT 守卫动作详解 |
| `ArduPilot_QuadPlane_TiltRotor_参数配置.md` | AP 原生 QuadPlane 配置 |
| `Transwing_实机固件与参数配置.md` | 实机刷机与试飞顺序 |

---

## 1. 折叠角与过渡相位

### 1.1 折叠角 θ 定义

| θ | 推力方向 | 典型 PWM（样机） | 含义 |
|---|----------|------------------|------|
| **90°** | 向上 | 1000（`TW_PWM_Q`） | 垂起/悬停 |
| **55°** | 过渡 | 1450 | `TW_ACCEL_MIN` 加速段下限 |
| **45°** | 过渡 | 1500 | 混控表插值节点 |
| **30°** | 过渡 | 1667 | `TW_BLEND_MIN` 混合段下限 |
| **0°** | 向前 | 2000（`TW_PWM_FW`） | 固定翼前飞 |

映射公式：

```text
θ = clamp((PWM - TW_PWM_FW) / (TW_PWM_Q - TW_PWM_FW), 0, 1) × 90°
```

**注意**：当前机构无角度传感器，`theta_est` 为开环估算（按 `TW_RATE_UP/DN` 向目标角逼近），不是实测角。

### 1.2 过渡相位（TWTR.Phase）

由**估算角 `theta_est`** 划分，用于日志与阶段理解：

| Phase | 名称 | θ_est 范围 | 典型特征 |
|------:|------|------------|----------|
| 0 | **HOVER** 悬停 | > 75° | 四电机垂直升力，Quad X 混控 |
| 1 | **ACCEL** 加速 | 55°–75° | 大角度过渡，需足够空速才能继续展开 |
| 2 | **BLEND** 混合 | 30°–55° | 升力与推力混合，对空速最敏感 |
| 3 | **FIXED_WING** 固定翼 | < 30° | 机翼基本展开，依赖固定翼气动 |

```text
90° ───────── HOVER（悬停）
     │
75° ─┼──────── HOVER / ACCEL 分界
     │
55° ─┼──────── ACCEL_MIN（加速段下限）
     │
30° ─┼──────── BLEND_MIN（混合段下限）
     │
 0° ───────── FIXED_WING（固定翼）
```

---

## 2. 飞行模式说明

ArduPilot 飞行模式决定 AP 如何指挥折叠机构与电机。Lua 守卫在此基础上叠加空速/姿态/下沉保护。

### 2.1 Q 模式（Mode 17–23）

| 模式 | 典型用途 | AP 折叠目标 | Lua 混控 |
|------|----------|-------------|----------|
| **QSTABILIZE** | 首飞悬停、Abort 回退目标 | **90°**（垂直） | 允许（CONTROL 时） |
| **QHOVER** | 定点悬停 | **90°** | 允许 |
| **QLOITER / QLAND 等** | 任务/降落 | **90°** | 允许 |

**特点**：AP 将 `SERVO11`（TiltMotorsFront）驱动到悬停位；四电机按 Quad X 提供垂直升力。

### 2.2 固定翼模式

| 模式 | Mode | 行为 | 转换建议 |
|------|-----:|------|----------|
| **FBWB** | 6 | 油门手控，TECS **不强制俯仰** | **前飞转换首选** |
| **FBWA** | 5 | TECS 管空速/俯仰 | 仅高空速巡航；低空速易触发守卫 |
| **MANUAL** | 0 | 直接杆量 | 地面检查折叠方向 |

**AP 折叠指令**：进入 FBWA/FBWB 后，AP **始终**命令折叠到 **0°**（固定翼位），与当前空速无关。

### 2.3 模式与 Lua 动态混控

| 飞行模式 | `TW_MIX_MODE=2` 时 Lua 接管电机 |
|----------|----------------------------------|
| Q 模式（17–23） | 允许 |
| FBWB | 允许 |
| FBWA | **不接管**（避免与 TECS 冲突） |
| 其他固定翼 | 视 `mode_allows_lua_mix` 默认不允许 |

---

## 3. Lua 脚本运行模式（TW_MIX_MODE）

与飞行模式独立，控制 Lua 是否写输出：

| 值 | 名称 | 行为 | 首飞建议 |
|----|------|------|----------|
| **0** | OBSERVE 观测 | 只算混控、写 TWNG/TWTR 日志；**不改电机/折叠**（`TW_LOG_ONLY=1`） | 第一阶段推荐 |
| **1** | MIRROR 镜像 | Lua M1–M4 写到 Scripting1–4（SERVO13–16），**不改 Motor1–4** | SITL 对比 |
| **2** | CONTROL 接管 | 通过 `Motors_dynamic`（`Q_FRAME_CLASS=17`）接管电机混控矩阵；CONTROL 下 Lua 可 **slew 折叠舵机** | 第二阶段 |

**联动规则**

- `TW_LOG_ONLY=0` 且 `MIX_MODE=0` → 自动升为 **MIRROR**。
- `TW_GUARD=1` 时，即使 `LOG_ONLY=1`，守卫仍可 **Hold 折叠 PWM** 或 **Abort 切 Q**。

---

## 4. 转换过程

完整转换约 **20 s**（机构 `4.5 deg/s`，90° 行程）。应把过渡当作**长时间状态**，而非瞬间切换。

### 4.1 垂起 → 固定翼（Q → FBWB）

**推荐试飞顺序**

| 步骤 | 操作 | 折叠角变化 | 说明 |
|------|------|------------|------|
| 1 | **QSTABILIZE** 悬停 | θ ≈ 90° | 确认 TWTR `Act=0`（ALLOW） |
| 2 | 前飞加速 | θ 仍 90° | 油门推满，积累空速 |
| 3 | 空速 **≥ 13 m/s** | — | 达到 `TW_BLEND_AS` 门槛 |
| 4 | 切换 **FBWB** | AP 开始命令 θ → 0° | 折叠机构展开，约 20 s |
| 5 | 过渡中 | 90° → 55° → 30° → 0° | 守卫按段检查空速 |
| 6 | θ < 30° 且 AS ≥ 18 m/s | 进入 FIXED_WING | 固定翼段稳定 |

**AP 与 Lua 协同**

```text
飞控（AP）                    Lua 脚本
─────────                    ─────────
FBWB → SERVO11 向 0°         读 PWM → theta_target
Q_TILT_RATE_DN = 4.5 deg/s   开环估算 theta_est
                             evaluate_transition()
                             必要时 Hold / Abort
                             插值混控表 → TWNG 日志
```

**各段最低空速要求**

| 目标段 | 条件 | 空速不足时 |
|--------|------|------------|
| θ 从 90° 向 55° 以下 | AS < 13 m/s | **WARN**（55°–90° 仅警告） |
| θ 在 30°–55°（BLEND） | AS < 13 m/s | **DANGER → Hold @ 55°** |
| θ < 30°（FIXED_WING） | AS < 18 m/s | **DANGER → Hold @ 30°** |

### 4.2 固定翼 → 垂起（FBWB → Q）

| 步骤 | 操作 | 折叠角变化 |
|------|------|------------|
| 1 | 减速或进入 Q 模式 | AP 命令 θ → 90° |
| 2 | 切换 **QSTABILIZE** | 折叠回悬停位 |
| 3 | 等待机构到位（~20 s） | θ → 90° |
| 4 | 悬停 | Quad X 升力恢复 |

**守卫**：向 90° 折叠（回 Q）时，空速门槛**不阻止**展开；主要保护发生在**向 0° 展开**的前飞转换。

### 4.3 Abort 回 Q（紧急保护）

当守卫判定 **ABORT_TO_Q**（`Act=2`）时：

1. 将允许角 **`Allow = 90°`**，折叠 PWM 限时写入悬停位（`TW_GUARD_MS`，默认 1000 ms）。
2. 调用 `vehicle:set_mode(17)` 切 **QSTABILIZE**。
3. GCS 显示：`TW-DYNMIX: guard reason=...`

---

## 5. 过渡守卫保护体系

守卫由 `evaluate_transition()` 实现，每 50–100 ms 运行一次。输入：**目标角、估算角、空速、姿态、滤波爬升率、电机饱和、飞行模式、Q Assist 状态**。

### 5.1 总开关与上电保护

| 项 | 参数/常量 | 说明 |
|----|-----------|------|
| 守卫总开关 | `TW_GUARD=1` | `0` 时只写 TWTR 日志，**不 Hold、不 Abort** |
| 上电宽限期 | `BOOT_GUARD_GRACE_S = 15 s` | 上电后 15 s 内 |
| 宽限空速 | `BOOT_GUARD_MAX_AS = 3 m/s` | 且 AS < 3 m/s 时，**守卫暂不生效** |
| 守卫生效条件 | AS ≥ 3 m/s 或上电超过 15 s | 避免地面静止误触发 |

### 5.2 空速门槛保护

| 参数 | 默认 | 保护逻辑 |
|------|-----:|----------|
| `TW_BLEND_AS` | 13 m/s | 目标 θ < 55° 且 AS < 13 → **DANGER，Hold @ 55°** |
| | | 目标 θ 在 55°–90° 且 AS < 13 → **WARN**（不 Hold） |
| `TW_FW_AS` | 18 m/s（脚本默认 19） | 目标 θ < 30° 且 AS < 18 → **DANGER，Hold @ 30°** |

**实测含义**：转换卡在 55° → 加油门攒速至 13 m/s；卡在 30° → 继续加速至 18 m/s。

### 5.3 姿态保护

| 参数 | 默认 | 条件 | 风险 |
|------|-----:|------|------|
| `TW_ATT_ABORT` | 42° | \|roll\| 或 \|pitch\| > 42° | DANGER，触发 abort 链 |
| `TW_ATT_DANG` | 55° | \|roll\| 或 \|pitch\| > 55° | DANGER |

建议 `TW_ATT_ABORT` 略高于 `ROLL_LIMIT_DEG`（40°），避免 FBWA 正常坡度误触发。

### 5.4 下沉率保护

| 参数/常量 | 值 | 说明 |
|-----------|-----|------|
| `TW_DESC_DANG` | -8 m/s | 滤波爬升率低于此值 → DANGER |
| `DESC_SUSTAIN_S` | 0.4 s | 持续低于阈值算 **sustained** |
| 严重下沉 | < -12 m/s（×1.5） | 立即触发 abort 链 |

**Abort 判定**（`should_abort_for_descent`）

| 阶段 | 触发 Abort 条件 |
|------|-----------------|
| 过渡段（θ ≥ 30° 或 AS < FW_AS） | 严重下沉 **或** sustained 下沉 |
| 固定翼段（θ < 30° 且 AS ≥ FW_AS） | 严重下沉 **或**（sustained **且** 姿态 abort/danger） |

### 5.5 电机饱和保护

| 参数 | 默认 | 条件 |
|------|-----:|------|
| `TW_SAT_PWM` | 1980 | 任一电机 PWM ≥ 1980 |
| 差动饱和 | — | 某电机 ≤ 1050 且另一电机 ≥ 1930 |

→ **DANGER**，参与 abort 链。

### 5.6 Q Assist 联动保护（TW_ASST_EN=1）

AP 在空速低于 `Q_ASSIST_SPEED`（典型 16 m/s）时介入升力/稳定。

| 条件 | Lua 行为 |
|------|----------|
| assist 激活 且 目标 θ < `TW_SAFE_MIN`（55°） | **Hold @ 55°**，混控矩阵 θ ≥ 55° |
| AS ≥ `TW_BLEND_AS`（13 m/s） | 允许折叠继续低于 SAFE_MIN（正常前飞转换） |
| 已 ABORT_TO_Q | assist 联动**不覆盖** Abort |

### 5.7 FBWA 特殊处理（TW_GUARD_FBWA=1）

| 条件 | 行为 |
|------|------|
| FBWA 且 AS < 13 m/s | |
| 仅姿态 abort（非下沉、非饱和） | **Hold** 在安全角，**不 Abort 回 Q** |
| 其他 DANGER 原因 | 正常 Abort 链 |

**实测建议**：前飞转换用 **FBWB**，不用 FBWA。

---

## 6. 守卫动作与决策逻辑

> 守卫动作逐项详解见 **`Transwing_守卫动作说明.md`**。

### 6.1 三种动作（TWTR.Act）

| Act | 名称 | 行为 |
|----:|------|------|
| 0 | **ALLOW** | 允许 AP 继续驱动折叠 |
| 1 | **HOLD_THETA** | 限时写入 `Allow` 角对应 PWM（`TW_GUARD_MS`） |
| 2 | **ABORT_TO_Q** | Hold @ 90° + 切 QSTABILIZE |

### 6.2 风险等级（TWTR.Risk）

| Risk | 含义 | 典型原因 |
|-----:|------|----------|
| 0 OK | 正常 | — |
| 1 WARN | 警告 | 55°–90° 段空速不足；assist Hold |
| 2 DANGER | 危险 | 空速门槛、姿态、下沉、饱和 |

### 6.3 决策优先级（简化）

```text
1. 评估风险 → OK / WARN / DANGER
2. DANGER + 目标在 30°–55° 且 AS 不足     → Hold @ 55°
3. DANGER + 目标 < 30° 且 AS 不足         → Hold @ 30°
4. DANGER + (姿态abort / 下沉abort / 饱和) → 通常 Abort @ 90° + QSTABILIZE
   └─ 例外：FBWA 低空速仅姿态abort        → Hold 安全角，不 Abort
5. assist 激活 + 目标 < SAFE_MIN + AS < BLEND_AS → Hold @ 55°（不覆盖 Abort）
```

### 6.4 决策流程图

```mermaid
flowchart TD
  A[每周期 evaluate_transition] --> B{TW_GUARD 且 as_guard?}
  B -- 否 --> Z[Act=ALLOW 仅记录]
  B -- 是 --> C[读 AS / 姿态 / 爬升率 / 饱和]
  C --> D{空速门槛}
  D -->|BLEND 段 AS 不足| E[DANGER Hold@55°]
  D -->|FW 段 AS 不足| F[DANGER Hold@30°]
  D -->|55-90° AS 不足| G[WARN]
  C --> H{姿态 / 下沉 / 饱和}
  H -->|abort 触发| I{FBWA 低空速仅姿态?}
  I -- 是 --> J[Hold 安全角]
  I -- 否 --> K[ABORT_TO_Q → 90° + QSTABILIZE]
  C --> L{assist 且 θ < SAFE_MIN?}
  L -- 是且 AS<13 --> M[Hold@55° WARN]
  E --> N[写 TWTR + GCS 告警]
  F --> N
  G --> N
  J --> N
  K --> N
  M --> N
  Z --> N
```

---

## 7. 保护条件汇总表

| 保护类型 | 触发条件 | 默认阈值 | 响应动作 |
|----------|----------|----------|----------|
| 混合段空速 | θ_target < 55° 且 θ ≥ 30°，AS < 门槛 | 13 m/s | Hold @ 55° |
| 固定翼段空速 | θ_target < 30°，AS < 门槛 | 18 m/s | Hold @ 30° |
| 大角 WARN | 55° ≤ θ < 90°，AS < 门槛 | 13 m/s | WARN only |
| 姿态 abort | \|roll\| 或 \|pitch\| 超阈 | 42° | DANGER → Abort（FBWA 例外 Hold） |
| 姿态 danger | \|roll\| 或 \|pitch\| 超阈 | 55° | DANGER |
| 危险下沉 | climb_rate < 阈 | -8 m/s | DANGER |
| 持续下沉 | 低于阈持续 0.4 s | — | 参与 Abort 判定 |
| 严重下沉 | climb_rate < -12 m/s | — | 立即 Abort |
| 电机饱和 | PWM ≥ 1980 或差动饱和 | 1980 | DANGER → Abort |
| Q Assist | assist 且 θ < 55° 且 AS < 13 | 55° | Hold @ 55° |
| 上电保护 | 上电 < 15 s 且 AS < 3 | — | 守卫关闭 |
| 折叠超时 | \|θ_target - θ_est\| > 2° 超 TW_TIMEOUT | 25 s | GCS 告警（非 Hold） |

---

## 8. 关键参数对照

| 参数 | 默认 | 与 AP 参数关系 |
|------|-----:|----------------|
| `TW_RATE_UP/DN` | 4.5 | 对齐 `Q_TILT_RATE_UP/DN` |
| `TW_TIMEOUT` | 25 | 对齐 `Q_TRANSITION_MS/1000` |
| `TW_ACCEL_MIN` | 55° | 加速段守卫下限 |
| `TW_BLEND_MIN` | 30° | 混合/固定翼分界 |
| `TW_BLEND_AS` | 13 | 前飞转换启动建议空速 |
| `TW_FW_AS` | 18–19 | 固定翼段最低空速 |
| `TW_SAFE_MIN` | 55° | assist 联动 Hold 角 |
| `TW_ATT_ABORT` | 42° | 略高于 `ROLL_LIMIT_DEG` |
| `TW_GUARD_MS` | 1000 ms | Hold/Abort PWM 超时 |
| `TW_GUARD` | 1 | **首飞必须开启** |
| `TW_LOG_ONLY` | 1 | 第一阶段只记录 |

**第一阶段推荐**（`transwing_sitl_observe.params`）：`TW_GUARD=1`，`TW_LOG_ONLY=1`，`TW_MIX_MODE=0`。

---

## 9. 试飞与日志

### 9.1 不建议首飞打开

| 组合 | 原因 |
|------|------|
| `TW_GUARD=0` | 失去过渡保护 |
| `TW_MIX_MODE=2` + 实机 | 需先 TWNG vs AP 对比 |
| `TW_LOG_ONLY=0` 无隔离 | 脚本可能写电机 |
| FBWA 低空速转换 | 易误触发守卫 |
| 自动任务转换 | 先手动验证 |

### 9.2 日志字段

| 日志 | 关键字段 |
|------|----------|
| **TWTR** | Targ / Est / Allow / Phase / Risk / AS / Act |
| **TWNG** | Lua 混控 M1–M4 vs AP 实际 A1–A4 |
| **TWAS** | assist 激活、Hold 角、混控 θ |

分析工具：

```bash
python tools/peek_latest_twtr.py
python tools/compare_twng_rcou.py log.BIN
python tools/analyze_fold_stuck.py log.BIN
```

---

## 10. 常见问题

| 现象 | 原因 | 处理 |
|------|------|------|
| 转换卡在 ~55° | AS < 13 m/s | 加油门攒速 |
| 卡在 ~30° | AS < 18 m/s | 继续加速 |
| 突然回 Q | 姿态/下沉/饱和 Abort | 查 TWTR `reason` |
| 卡在 ~60°/45° | `Q_TILT_MAX` 太小 | 改为 **90** |
| 地面误告警 | 上电 15 s 内 | 正常；或等 AS 稳定 |

---

*文档版本：2026-06-24 · 依据 `scripts/transwing_dynamic_mix.lua` 与项目试飞配置整理*
