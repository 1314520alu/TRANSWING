# Transwing 实机固件与参数配置

本文档说明 **实机试飞** 应使用的 ArduPilot 固件、Lua 脚本部署顺序，以及 **AP 原生参数 + TW 脚本参数** 的完整配置。与 SITL 专用 patch 无关。

相关文档：

| 文件 | 内容 |
|------|------|
| `ArduPilot_QuadPlane_TiltRotor_参数配置.md` | QuadPlane 构型、通道、调试顺序 |
| `Transwing_Lua_动态混控仿真说明.md` | 28 个 `TW_*` 参数逐项说明 |
| `transwing_sitl_observe.params` | 第一阶段 TW + 守卫参数（实机可直接参考） |
| `transwing_sitl_startup.params` | AP 原生 QuadPlane + 通道映射 |

---

## 1. 用什么固件

### 1.1 实机要求

| 项目 | 要求 |
|------|------|
| **固件类型** | **ArduPlane**（固定翼 + QuadPlane），不是 ArduCopter |
| **来源** | **官方 ArduPilot 正式版**，Mission Planner 或 QGroundControl 刷入飞控 |
| **版本** | **≥ 4.5**（必须支持 Lua Scripting）；建议 **4.5.x / 4.6.x 稳定版** |
| **是否改 C++** | **不需要**。仓库 `patches/` 仅用于 SITL 仿真（`SIM_TranswingQuadPlane`），**不刷进飞控板** |
| **飞控硬件** | 支持 ArduPlane、Flash 足够装 Plane + Lua 的板子（Pixhawk 6X、Cube Orange 等） |

> SITL 开发环境可能使用 `ArduPlane V4.7.0-dev` + `quadplane-transwing`；**实机用官方 Plane 即可**。

### 1.2 构型对应

```text
ArduPlane
  └─ QuadPlane（Q_ENABLE=1）
       └─ Tilt-Rotor / Tilt-Wing（Q_TILT_ENABLE=1）
            └─ Quad X 四旋翼悬停（Q_FRAME_CLASS=1, Q_FRAME_TYPE=1）
                 └─ 四电机同步折叠/倾转（Q_TILT_MASK=15, SERVO11）
```

**不要**配成 Tailsitter。垂起时机身不整体竖直，推力方向由机翼/电机折叠改变。

### 1.3 SITL 与实机对比

| 项目 | SITL | 实机 |
|------|------|------|
| 固件 | 可带 `quadplane-transwing` C++ patch | **官方 ArduPlane** |
| 物理 | 折叠改变电机位置/力臂 | AP 原生只倾转推力方向 |
| Lua 脚本 | `scripts/transwing_dynamic_mix.lua` | **相同** |
| 第一阶段 | `observe` 配置 | `TW_LOG_ONLY=1`, `Q_FRAME_CLASS=1` |

---

## 2. 部署顺序

按以下顺序操作，避免 `TW_` 参数无法创建或脚本不加载：

```text
1. 刷入官方 ArduPlane
2. Mission Planner 完成基础校准（加速度计、罗盘、遥控、ESC）
3. 设置 SCR_ENABLE=1，重启飞控
4. 上传 scripts/transwing_dynamic_mix.lua → 飞控 APM/scripts/
5. 再次重启（脚本创建 28 个 TW_ 参数）
6. 写入本文第 3 节全部 AP + TW 参数
7. 地面检查 Motor Test、SERVO11 折叠行程
8. 首飞：QSTABILIZE 悬停 → 空速 ≥13 m/s → FBWB 转换
```

### 2.1 脚本路径与确认

飞控内路径：

```text
APM/scripts/transwing_dynamic_mix.lua
```

重启后 GCS Messages 应出现：

```text
TW-DYNMIX: loaded
TW-DYNMIX: running, mix_mode=0 log_only=1.0 ...
```

Mission Planner → **Full Parameter Tree** 搜索 `TW_`，应看到 **28 个参数**。

---

## 3. 参数完整配置（第一阶段实测）

数值来自 `transwing_sitl_startup.params` + `transwing_sitl_observe.params`，为当前仓库试飞约定。

### 3.1 A. Lua 与 QuadPlane 总开关

| 参数 | 值 | 说明 |
|------|-----|------|
| `SCR_ENABLE` | **1** | 启用 Lua；**必须先设并重启**，再上传脚本 |
| `SCR_HEAP_SIZE` | MP 默认或略增 | 脚本内存；加载失败可试 ≥100000 |
| `Q_ENABLE` | **1** | 启用 QuadPlane |

### 3.2 B. 悬停构型（AP 原生电机混控）

| 参数 | 值 | 说明 |
|------|-----|------|
| `Q_FRAME_CLASS` | **1** | Quad 四旋翼（**第一阶段不用 17**） |
| `Q_FRAME_TYPE` | **1** | X 型 |

**电机编号**（地面 Motor Test 必核对）：

| AP 电机 | MP Test | 物理位置 | 转向 |
|---------|---------|----------|------|
| MOTOR 1 | A | 右前 | CCW |
| MOTOR 2 | C | 左后 | CCW |
| MOTOR 3 | D | 左前 | CW |
| MOTOR 4 | B | 右后 | CW |

Mission Planner Motor Test 顺序 A→B→C→D 对应电机 **1→4→2→3**。

**电机 PWM**（按 ESC 实测校准）：

| 参数 | 建议初值 | 说明 |
|------|----------|------|
| `Q_M_PWM_MIN` | 1000 | ESC 最低油门 |
| `Q_M_PWM_MAX` | 2000 | ESC 最高油门 |
| `Q_M_SPIN_ARM` | 0.08 | 解锁后怠速 |
| `Q_M_SPIN_MIN` | 0.12 | 最小旋转油门 |
| `Q_M_SPIN_MAX` | 0.95 | 可按实机调整 |

### 3.3 C. 倾转/折叠（AP 原生）

| 参数 | 值 | 说明 |
|------|-----|------|
| `Q_TILT_ENABLE` | **1** | 启用倾转/折叠 |
| `Q_TILT_MASK` | **15** | 四电机参与（bit0–3 = M1–M4） |
| `Q_TILT_TYPE` | **0** | 连续倾转；两档锁定机构才用 **1** |
| `Q_TILT_MAX` | **90** | 原生倾转上限。**勿设 30/45**，否则会提前卡在 ~60°/45°；55°/30° 由 Lua 守卫 |
| `Q_TILT_RATE_UP` | **4.5** | 向垂直折叠 deg/s（≈ 90° / 20 s） |
| `Q_TILT_RATE_DN` | **4.5** | 向固定翼展开 deg/s |
| `Q_TILT_FIX_GAIN` | **0** | 第一阶段关闭固定翼倾转辅助 |
| `Q_TILT_FIX_ANGLE` | **0** | 同上 |
| `Q_TILT_YAW_ANGLE` | **0** | 第一阶段不做矢量偏航 |
| `Q_TRANSITION_MS` | **25000** | 转换时间窗口 25 s |

展开/折叠速度若与 4.5 不一致：

```text
Q_TILT_RATE_DN = 90 / 展开耗时_s
Q_TILT_RATE_UP = 90 / 折叠耗时_s
```

**SERVO11 折叠舵机**（必须地面实测，不可抄模板）：

| 参数 | 值 | 说明 |
|------|-----|------|
| `SERVO11_FUNCTION` | **41** | TiltMotorsFront |
| `SERVO11_MIN` | **实测** | 固定翼位（推力向前）→ 对齐 `TW_PWM_FW` |
| `SERVO11_MAX` | **实测** | 悬停位（推力向上）→ 对齐 `TW_PWM_Q` |
| `SERVO11_TRIM` | **实测** | 机械中位 |
| `SERVO11_REVERSED` | **实测** | Q 模式垂直、MANUAL/FBWA 向前 |

地面检查：

```text
QSTABILIZE / QHOVER  → SERVO11 到悬停位（~90°）
MANUAL / FBWA        → SERVO11 到固定翼位（~0°）
```

PWM 与折叠角参考（当前样机约定，`TW_PWM_FW=2000`, `TW_PWM_Q=1000`）：

| PWM | 折叠角 θ | 备注 |
|-----|----------|------|
| 1000 | 90° | 悬停 |
| 1450 | 55° | `TW_ACCEL_MIN` |
| 1500 | 45° | 混控表节点 |
| 1667 | 30° | `TW_BLEND_MIN` |
| 2000 | 0° | 固定翼 |

### 3.4 D. 输出通道映射

与 `输出通道建议.csv` 一致：

| 输出 | `SERVOx_FUNCTION` | 功能 | 连接 |
|------|-------------------|------|------|
| SERVO1 | 33 | Motor1 | 右前 ESC |
| SERVO2 | 34 | Motor2 | 左后 ESC |
| SERVO3 | 35 | Motor3 | 左前 ESC |
| SERVO4 | 36 | Motor4 | 右后 ESC |
| SERVO5 | 4 | Aileron | 左副翼 |
| SERVO6 | 4 | Aileron | 右副翼 |
| SERVO7 | 19 | Elevator | 左平尾 |
| SERVO8 | 19 | Elevator | 右平尾 |
| SERVO9 | 21 | Rudder | 左垂尾 |
| SERVO10 | 21 | Rudder | 右垂尾 |
| SERVO11 | 41 | TiltMotorsFront | 折叠舵机 |
| SERVO12 | **0** | Disabled | 中间升降舵，首飞先关 |

SERVO5–10 的 `MIN/MAX/TRIM/REVERSED` 必须逐路地面检查。

**实机首飞不需要**（仅 SITL 镜像 Lua 输出）：

| 参数 | 值 |
|------|-----|
| SERVO13_FUNCTION | 94 |
| SERVO14_FUNCTION | 95 |
| SERVO15_FUNCTION | 96 |
| SERVO16_FUNCTION | 97 |

### 3.5 E. 固定翼 / 空速

| 参数 | 值 | 说明 |
|------|-----|------|
| `TW_BLEND_AS` | **13** | Lua 混合段折角门槛（m/s）；与下表 AP 参数分工不同 |
| `TW_FW_AS` | **19** | Lua：<30° 固定翼段门槛（m/s） |
| `AIRSPEED_MIN` | **19** | AP 过渡完成 / 电机减载门槛；与 `TW_FW_AS` 对齐 |
| `ARSPD_FBW_MIN` | **19** | FBW/TECS 最低空速 |
| `Q_ASSIST_SPEED` | **16** | 近失速兜底（比 `ARSPD_FBW_MIN` 低 3 m/s） |
| `TRIM_ARSP_CM` | **2500** | 巡航目标 25 m/s |
| `AIRSPEED_MAX` | **31** | 最大空速 |
| `RC_OVERRIDE_TIME` | **10** | RC 覆盖保持时间 (s) |

**强烈建议安装并校准空速计**；无空速计则 Lua 守卫 `TWTR.AS` 不可靠。

### 3.6 F. Lua TW 参数（脚本加载后写入）

**第一阶段：只守卫 + 记录，不接管电机**

| 参数 | 值 | 说明 |
|------|-----|------|
| `TW_ENABLE` | **1** | 脚本总开关 |
| `TW_LOG_ONLY` | **1** | **不控制电机**，只写 TWNG/TWTR |
| `TW_MIX_MODE` | **0** | 仅观测 |
| `TW_INPUT_SRC` | **1** | 混控输入来自 RC |
| `TW_GUARD` | **1** | 过渡守卫开 |

**折叠角映射**（与 SERVO11 对齐）：

| 参数 | 值 | 说明 |
|------|-----|------|
| `TW_FOLD_CH` | **10** | 零基通道 = SERVO11 |
| `TW_PWM_FW` | **= 固定翼位 PWM** | 例 2000 → θ=0° |
| `TW_PWM_Q` | **= 悬停位 PWM** | 例 1000 → θ=90° |
| `TW_RATE_UP` | **4.5** | 对齐 `Q_TILT_RATE_UP` |
| `TW_RATE_DN` | **4.5** | 对齐 `Q_TILT_RATE_DN` |
| `TW_TIMEOUT` | **25** | 估算角超时报警 (s) |

**过渡守卫**：

| 参数 | 值 | 说明 |
|------|-----|------|
| `TW_ACCEL_MIN` | **55** | 低于 55° 需 blend 空速 |
| `TW_BLEND_MIN` | **30** | 低于 30° 需 FW 空速 |
| `TW_BLEND_AS` | **13** | m/s，30°–90° 段门槛（20 kg 样机） |
| `TW_FW_AS` | **18** | m/s，<30° 段门槛（失速≈18.6 m/s） |
| `TW_ATT_ABORT` | **42** | °，姿态 abort（略高于 `ROLL_LIMIT_DEG`） |
| `ROLL_LIMIT_DEG` | **40** | °，FBWA 最大横滚 |
| `TW_ATT_DANG` | **55** | °，姿态危险 |
| `TW_DESC_DANG` | **-8** | m/s，危险下沉率 |
| `TW_SAT_PWM` | **1980** | 电机饱和判定 |
| `TW_GUARD_FBWA` | **1** | FBWA 低空速只 Hold 不 Abort |
| `TW_GUARD_MS` | **1000** | Hold 折叠 PWM 超时 (ms) |
| `TW_SAFE_MIN` | **55** | assist 联动 Hold 角（见 `TW_ASST_EN`） |
| `TW_ASST_EN` | **1** | Q assist 与 Lua 折叠/混控联动 |

守卫分段（90° → 0°）：

```text
90° ───────── 悬停
     │  ≥55°：空速 < BLEND_AS → WARN
55° ─┼──────── ACCEL_MIN；不足 → Hold@55°
     │  30°–55°：需 AS ≥ 13 m/s
30° ─┼──────── BLEND_MIN；不足 → Hold@30°
     │  <30°：需 AS ≥ 18 m/s
 0° ───────── 固定翼
```

逐项说明见 `Transwing_Lua_动态混控仿真说明.md` 第 4 节。

### 3.7 G. 可导入参数块（Mission Planner 格式）

合并 A–F，**`TW_PWM_FW/Q` 与 `SERVO11_MIN/MAX` 须按实机标定后修改**：

```text
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

导入方式：Mission Planner → **CONFIG → Full Parameter List → Load from file**（或逐条写入后 **Write Params**）。

---

## 4. 第二阶段（后期，首飞勿开）

完成第一阶段悬停 + 转换 + 日志分析后再考虑：

| 参数 | 值 | 说明 |
|------|-----|------|
| `Q_FRAME_CLASS` | **17** | Motors_dynamic 动态混控矩阵 |
| `TW_MIX_MODE` | **2** | Lua 接管 Motor1–4 |
| `TW_LOG_ONLY` | **0** | 允许写电机 |

参考 `transwing_sitl_mp.params`。需 AP 支持 `Q_FRAME_CLASS=17`，且 SITL/台架充分对比 TWNG 与 RCOU。

---

## 5. Mission Planner 操作步骤

### 5.1 刷固件与校准

1. **初始设置 → 安装固件** → 选择 **ArduPlane**（与飞控匹配版本）
2. **必选传感器** → 加速度计、罗盘、遥控、ESC 校准
3. **CONFIG → Full Parameter Tree** → `SCR_ENABLE=1` → Write → **重启**

### 5.2 脚本与参数

4. 上传 `transwing_dynamic_mix.lua` 到 `APM/scripts/`（MP Scripting 或 FTP）
5. **重启飞控**
6. 确认 GCS：`TW-DYNMIX: loaded`
7. 写入第 3.7 节参数（或加载 `transwing_sitl_observe.params` + `transwing_sitl_startup.params` 合并内容）
8. **再次重启**

### 5.3 地面检查

| 检查项 | 期望 |
|--------|------|
| `TW_` 参数 | 28 个 |
| Motor Test A/B/C/D | 1/4/2/3，转向正确 |
| QSTABILIZE | SERVO11 → 悬停位 |
| MANUAL | SERVO11 → 固定翼位 |
| 折叠耗时 | 与 `Q_TILT_RATE_*`、`TW_RATE_*` 一致 |

---

## 6. 试飞顺序

| 步骤 | 操作 |
|------|------|
| 1 | **QSTABILIZE** → 解锁 → 等 SERVO11 到悬停位（约 20 s）→ 短悬停 |
| 2 | 爬升，空速 **≥ 13 m/s** |
| 3 | 切 **FBWB**（推荐；避免低空速 FBWA） |
| 4 | 观察转换；守卫触发时 GCS 显示 `TW-DYNMIX: guard reason=...` |
| 5 | 下载 BIN 日志，查 **TWTR**（Targ/Est/AS/Act）和 **TWNG** |

### 6.1 飞行模式建议

| 模式 | 用途 |
|------|------|
| **QSTABILIZE / QHOVER** | 悬停、首飞 |
| **FBWB** | **前飞转换**（油门手控，TECS 不强制俯仰） |
| **FBWA** | 高空速巡航；低空速易触发守卫 |

### 6.2 第一阶段勿开

| 功能 | 原因 |
|------|------|
| `TW_MIX_MODE=2` + 实机 | 需先完成 TWNG vs AP 对比 |
| `TW_LOG_ONLY=0` 且无隔离 | 脚本可能写电机 |
| `TW_GUARD=0` | 失去过渡保护 |
| Vectored yaw / Tilt assist | 增加调试变量 |
| 自动任务转换 | 先手动验证 |

---

## 7. 日志与事后分析

| 日志类型 | 内容 |
|----------|------|
| **TWTR** | 目标角、估计角、允许角、空速、Phase、Risk、Act |
| **TWNG** | Lua 混控 M1–M4 vs AP 实际 A1–A4 |

工具：

```bash
python tools/peek_latest_twtr.py      # 查看最新 TWTR
python tools/compare_twng_rcou.py log.BIN
python tools/analyze_fold_stuck.py log.BIN
```

---

## 8. 常见问题

| 现象 | 可能原因 | 处理 |
|------|----------|------|
| 无 `TW_` 参数 | 脚本未加载或 `SCR_ENABLE=0` | 上传脚本、设 SCR_ENABLE=1、重启 |
| 转换卡在 ~60° / 45° | `Q_TILT_MAX` 太小 | 改为 **90** |
| 55° Hold 不往下 | 空速 < 13 m/s | 加油门攒速 |
| 30° 以下 Hold | 空速 < 18 m/s | 继续加速 |
| Q 模式折叠方向反 | SERVO11 或 TW_PWM 反 | 调 `SERVO11_REVERSED` 或交换 TW_PWM_FW/Q |
| 起飞翻滚 | 电机序号/旋向/桨向 | Motor Test 逐项核对 |

---

## 9. 参考

- ArduPilot Wiki: [QuadPlane](https://ardupilot.org/plane/docs/quadplane-overview.html)、[Tilt Rotor Planes](https://ardupilot.org/plane/docs/guide-tilt-rotor.html)
- 本仓库：`scripts/transwing_dynamic_mix.lua`
- 本仓库：`输出通道建议.csv`、`折叠角分配表.csv`
