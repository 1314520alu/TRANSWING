# Transwing 展开测试与参数调整表

文档版本：2026-09-24  
依据：`Transwing_实机固件与参数配置.md` 第 3.7 节、`Transwing_守卫动作说明.md`、`scripts/transwing_dynamic_mix.lua`  
适用：地面吹空速管检查折叠展开；首飞第一阶段（`Q_FRAME_CLASS=1`，不用 Lua 动态混控）  
`TW_FW_AS` 取 **19**，与 `AIRSPEED_MIN` / `ARSPD_FBW_MIN` 对齐。

---

## 0. 怎么测（先看再改参数）

吹风本身**不必改参数**。展开由两层逻辑决定：

| 层 | 行为 | 和空速的关系 |
|---|---|---|
| 飞控原生倾转 | Q 模式命令 θ→90°；切 MANUAL / FBWA / FBWB 后命令 θ→0° | 不管空速，一切固定翼模式就开始往前展 |
| Lua 守卫 `TW_GUARD=1` | 空速不够则 Hold，挡住继续往 0° | 过 55° 要 ≥13 m/s；过 30°、展到 0° 要 ≥19 m/s |

地面检查（不装桨、上锁）：

1. `QSTABILIZE` → SERVO11 到悬停位（θ≈90°）
2. 切 **MANUAL**（地面查行程首选）或 FBWB
3. 对着空速管**进气孔**吹，看 HUD / `TWTR.AS`
4. 吹到 ≥13 可过 55°；吹到 ≥19 可展到 0°
5. 普通吹风机经常吹不到 19。只想看全程、不测守卫：临时 `TW_GUARD=0`，测完改回 **1**

不要装桨解锁后切 FBWB 再吹管。不要用热风长时间对着空速管。没有校准空速计或 `ARSPD_USE=0` 时，吹管改不了守卫空速。

---

## 1. 吹风展开：可能临时改的

| 参数 | 正常/首飞 | 地面吹风测全程 | 说明 |
|------|----------|----------------|------|
| `TW_GUARD` | **1** | 查全程可临时 **0** | `1` 时空速不够会 Hold@55°/30°。地面只查机构行程可关，测完必须改回 1 |
| `TW_BLEND_AS` | **13** | 保持 13 | 过 55° 的空速门槛。吹到 `TWTR.AS` ≥13 即可，不要为了好吹而改低 |
| `TW_FW_AS` | **19** | 保持 19 | 过 30°、展到 0° 的门槛。吹不到不要改成 8、10 |
| `TW_ASST_EN` | **1** | 一般保持 1 | Assist 且 AS<13 时也会 Hold@55°。吹到 ≥13 会放行 |
| `ARSPD_USE` | **1**（有空速计） | 保持 1 | `0` 时吹管改不了守卫用的空速 |
| `ARSPD_TYPE` | 按传感器 | 按实机 | 数字/模拟空速计类型，配错则吹风无读数 |
| `ARSPD_OFFSET` / `ARSPD_RATIO` | 校准值 | 先校准再吹 | 未校准则 `TWTR.AS` 不准 |

---

## 2. 空速门槛（决定卡在哪）

首飞对齐后不要改。吹风只是让读数达到这些门槛。

| 参数 | 值 | 作用 |
|------|---:|------|
| `TW_BLEND_AS` | **13** | 目标 <55° 且 AS<13 → Hold@55°；55°–90° 只 WARN |
| `TW_FW_AS` | **19** | 目标 <30° 且 AS<19 → Hold@30° |
| `TW_ACCEL_MIN` | **55** | 混合段 Hold 角（deg） |
| `TW_BLEND_MIN` | **30** | 固定翼段 Hold 角（deg） |
| `TW_SAFE_MIN` | **55** | Assist 联动 Hold 角（deg） |
| `AIRSPEED_MIN` | **19** | AP 过渡完成 / 电机减载，与 `TW_FW_AS` 对齐 |
| `ARSPD_FBW_MIN` | **19** | FBW/TECS 最低空速 |
| `Q_ASSIST_SPEED` | **16** | 近失速 Assist（比 19 低 3） |
| `TRIM_ARSP_CM` | **2500** | 巡航 25 m/s |
| `AIRSPEED_MAX` | **31** | 最大空速 |

守卫分段（90° → 0°）：

```
90° ───────── 悬停
     │  ≥55°：空速 < 13 → WARN（仍允许）
55° ─┼──────── ACCEL_MIN；不足 → Hold@55°
     │  30°–55°：需 AS ≥ 13 m/s
30° ─┼──────── BLEND_MIN；不足 → Hold@30°
     │  <30°：需 AS ≥ 19 m/s
 0° ───────── 固定翼
```

上电 15 s 内且空速 <3 m/s 时守卫暂不生效；一吹到 ≥3，守卫马上开始干活。

---

## 3. 折叠机构：必须按实机标定

| 参数 | 模板值 | 是否要改 | 说明 |
|------|--------|----------|------|
| `SERVO11_FUNCTION` | **41** | 保持 | TiltMotorsFront |
| `SERVO11_MIN` | 实测 | **必改** | 固定翼位 PWM（推力向前） |
| `SERVO11_MAX` | 实测 | **必改** | 悬停位 PWM（推力向上） |
| `SERVO11_TRIM` | 实测 | **必改** | 机械中位 |
| `SERVO11_REVERSED` | 实测 | **必改** | Q 模式垂直、MANUAL/FBWA 向前 |
| `TW_FOLD_CH` | **10** | 保持 | 零基通道 = SERVO11 |
| `TW_PWM_FW` | 例 **2000** | **与 SERVO11 固定翼位一致** | θ=0° |
| `TW_PWM_Q` | 例 **1000** | **与 SERVO11 悬停位一致** | θ=90° |
| `Q_TILT_RATE_UP` | **4.5** | 按实测行程改 | 90 / 折叠耗时_s |
| `Q_TILT_RATE_DN` | **4.5** | 按实测行程改 | 90 / 展开耗时_s |
| `TW_RATE_UP` / `TW_RATE_DN` | **4.5** | **与上面一对齐** | Lua 开环估算速率 |

当前样机 PWM 与折叠角参考（`TW_PWM_FW=2000`，`TW_PWM_Q=1000`）：

| PWM | 折叠角 θ | 备注 |
|-----|----------|------|
| 1000 | 90° | 悬停 |
| 1450 | 55° | `TW_ACCEL_MIN` |
| 1500 | 45° | 混控表节点 |
| 1667 | 30° | `TW_BLEND_MIN` |
| 2000 | 0° | 固定翼 |

---

## 4. 倾转 / 构型（首飞写入后一般不动）

| 参数 | 值 | 说明 |
|------|---:|------|
| `SCR_ENABLE` | **1** | 先写再重启，否则没有 `TW_*` |
| `Q_ENABLE` | **1** | QuadPlane |
| `Q_FRAME_CLASS` | **1** | 原生 Quad X，首飞不要 17 |
| `Q_FRAME_TYPE` | **1** | X |
| `Q_TILT_ENABLE` | **1** | 倾转/折叠 |
| `Q_TILT_MASK` | **15** | 四电机 |
| `Q_TILT_TYPE` | **0** | 连续倾转 |
| `Q_TILT_MAX` | **90** | 勿设 30/45，否则卡在约 60°/45° |
| `Q_TILT_FIX_GAIN` | **0** | 首飞关固定翼倾转辅助 |
| `Q_TILT_FIX_ANGLE` | **0** | 同上 |
| `Q_TILT_YAW_ANGLE` | **0** | 首飞不做矢量偏航 |
| `Q_TRANSITION_MS` | **25000** | 转换窗口 25 s |

---

## 5. Lua 守卫 / 脚本（第一阶段）

| 参数 | 值 | 说明 |
|------|---:|------|
| `TW_ENABLE` | **1** | 脚本总开关 |
| `TW_LOG_ONLY` | **1** | 不写电机，只记 TWNG/TWTR |
| `TW_MIX_MODE` | **0** | 只观测 |
| `TW_INPUT_SRC` | **1** | 混控输入来自 RC |
| `TW_GUARD` | **1** | 过渡守卫；地面查全程可临时 0 |
| `TW_TIMEOUT` | **25** | 估算角超时告警（s） |
| `TW_ATT_ABORT` | **42** | 姿态 Abort（略高于 `ROLL_LIMIT_DEG`） |
| `ROLL_LIMIT_DEG` | **40** | FBWA 最大横滚 |
| `TW_ATT_DANG` | **55** | 姿态危险 |
| `TW_DESC_DANG` | **-8** | 危险下沉（m/s） |
| `TW_SAT_PWM` | **1980** | 电机饱和 |
| `TW_GUARD_FBWA` | **1** | FBWA 低空速只 Hold 不 Abort |
| `TW_GUARD_MS` | **1000** | Hold PWM 超时（ms） |
| `TW_MIX_BLEND` | **0** | 第一阶段 |
| `TW_OUT_GAIN` | **0.2** | 第一阶段 |

---

## 6. 不要为了吹风去改

| 参数 | 不要改成 | 原因 |
|------|----------|------|
| `TW_BLEND_AS` / `TW_FW_AS` | 改低迁就吹风机 | 空中会过早展过 55°/30° |
| `Q_TILT_MAX` | 30 / 45 | 机构会提前卡死，和守卫无关 |
| `Q_FRAME_CLASS` | 17 | 首飞不用 Lua 动态混控 |
| `TW_MIX_MODE` / `TW_LOG_ONLY` | 2 / 0 | 会接管电机 |
| `TW_GUARD` | 飞过之后还停在 0 | 失去 Hold/Abort |

第二阶段（首飞勿开）：`Q_FRAME_CLASS=17`、`TW_MIX_MODE=2`、`TW_LOG_ONLY=0`。需先完成 TWNG 与 AP 对比。

---

## 7. 第一阶段可导入参数块

Mission Planner → CONFIG → Full Parameter List → Load from file。  
`TW_PWM_FW/Q` 与 `SERVO11_MIN/MAX` 须按实机标定后修改。

```
SCR_ENABLE,1
Q_ENABLE,1
Q_FRAME_CLASS,1
Q_FRAME_TYPE,1

Q_TILT_ENABLE,1
Q_TILT_MASK,15
Q_TILT_TYPE,0
Q_TILT_MAX,90
Q_TILT_RATE_UP,4.5
Q_TILT_RATE_DN,4.5
Q_TILT_FIX_GAIN,0
Q_TILT_FIX_ANGLE,0
Q_TILT_YAW_ANGLE,0
Q_TRANSITION_MS,25000

Q_M_PWM_MIN,1000
Q_M_PWM_MAX,2000
Q_M_SPIN_ARM,0.08
Q_M_SPIN_MIN,0.12

SERVO1_FUNCTION,33
SERVO2_FUNCTION,34
SERVO3_FUNCTION,35
SERVO4_FUNCTION,36
SERVO5_FUNCTION,4
SERVO6_FUNCTION,4
SERVO7_FUNCTION,19
SERVO8_FUNCTION,19
SERVO9_FUNCTION,21
SERVO10_FUNCTION,21
SERVO11_FUNCTION,41
SERVO12_FUNCTION,0

AIRSPEED_MIN,19
ARSPD_FBW_MIN,19
Q_ASSIST_SPEED,16
TRIM_ARSP_CM,2500
AIRSPEED_MAX,31
ROLL_LIMIT_DEG,40
RC_OVERRIDE_TIME,10

TW_ENABLE,1
TW_LOG_ONLY,1
TW_MIX_MODE,0
TW_INPUT_SRC,1
TW_GUARD,1
TW_FOLD_CH,10
TW_PWM_FW,2000
TW_PWM_Q,1000
TW_RATE_UP,4.5
TW_RATE_DN,4.5
TW_TIMEOUT,25
TW_ACCEL_MIN,55
TW_BLEND_MIN,30
TW_BLEND_AS,13
TW_FW_AS,19
TW_ATT_ABORT,42
TW_ASST_EN,1
TW_SAFE_MIN,55
TW_ATT_DANG,55
TW_DESC_DANG,-8
TW_SAT_PWM,1980
TW_GUARD_FBWA,1
TW_GUARD_MS,1000
TW_MIX_BLEND,0
TW_OUT_GAIN,0.2
```

---

## 8. 相关文档

| 文件 | 内容 |
|------|------|
| `Transwing_实机固件与参数配置.md` | 实机固件、通道、第一阶段完整参数 |
| `Transwing_守卫动作说明.md` | ALLOW / HOLD / ABORT |
| `Transwing_模式转换与保护说明.md` | 模式、空速门槛、Abort 链 |
| `scripts/transwing_dynamic_mix.lua` | 守卫实现与 `TW_*` 默认值 |
