# Transwing 多旋翼动力与滤波参数配置

**文档版本**：2026-06-24  
**适用机型**：Transwing 样机（20 kg，翼展 2448 mm）  
**动力配置**：T-MOTOR U8Ⅱ Lite KV100 × 4 + G26×8.5 桨 × 4 + ALPHA 60A 12S V1.2 × 4  
**固件**：ArduPlane ≥ 4.5（QuadPlane + Tilt-Rotor）  
**阶段**：第一阶段首飞（`Q_FRAME_CLASS=1`，原生 Quad X 混控）

---

## 1. 设计输入摘要

| 项目 | 数值 |
|------|------|
| 起飞重量 | 20 kg |
| 外形 | 长 1379 mm × 翼展 2448 mm × 高 537 mm |
| 螺旋桨 | G26×8.5（直径 660.4 mm，螺距 215.9 mm） |
| 电机 | U8Ⅱ Lite KV100，12S / 48–52 V，最大持续 31 A / 387 W |
| 电调 | ALPHA 60A 12S，油门行程 **1100–1940 μs**，刷新率 500 Hz |
| 悬停构型 | Quad X，四电机同步折叠（θ=90° 悬停） |
| 单桨悬停推力 | 约 4.9 kg（50%–70% 油门段） |
| 悬停转速 | 约 2489 RPM（基频 42 Hz，桨叶通过频率 83 Hz） |

---

## 2. QuadPlane 构型与倾转

| 参数 | 值 | 说明 |
|------|-----|------|
| `Q_ENABLE` | 1 | 启用 QuadPlane 垂起功能 |
| `Q_FRAME_CLASS` | 1 | 四旋翼布局；首飞阶段用原生混控，不用 17（动态混控） |
| `Q_FRAME_TYPE` | 1 | X 型电机布局 |
| `Q_TILT_ENABLE` | 1 | 启用倾转/折叠电机推力方向切换 |
| `Q_TILT_MASK` | 15 | 四个电机均参与倾转（bit0–bit3 = Motor1–4） |
| `Q_TILT_TYPE` | 0 | 连续倾转；仅机构两档锁定时才改 1 |
| `Q_TILT_MAX` | 90 | 原生倾转上限 90°，对应折叠角 θ=90° 悬停 |
| `Q_TILT_RATE_UP` | 4.5 | 向垂直方向倾转速率（deg/s），匹配约 20 s 折叠行程 |
| `Q_TILT_RATE_DN` | 4.5 | 向前飞方向倾转速率（deg/s） |
| `Q_TILT_FIX_GAIN` | 0 | 首飞不用固定翼模式倾转辅助 |
| `Q_TILT_FIX_ANGLE` | 0 | 首飞不用固定翼模式倾转辅助角 |
| `Q_TILT_YAW_ANGLE` | 0 | 首飞不做矢量偏航 |
| `Q_TRANSITION_MS` | 25000 | 前飞转换时间窗口（ms），匹配慢速折叠机构 |

---

## 3. 电机输出通道映射

| 参数 | 值 | 说明 |
|------|-----|------|
| `SERVO1_FUNCTION` | 33 | Motor1，右前，测试字母 A，CCW |
| `SERVO2_FUNCTION` | 34 | Motor2，左后，测试字母 C，CCW |
| `SERVO3_FUNCTION` | 35 | Motor3，左前，测试字母 D，CW |
| `SERVO4_FUNCTION` | 36 | Motor4，右后，测试字母 B，CW |
| `SERVO11_FUNCTION` | 41 | 机翼折叠舵机（TiltMotorsFront） |

Motor Test 顺序 A→B→C→D 对应电机 **1→4→2→3**。

---

## 4. 电机 PWM 与推力曲线（ALPHA 电调专用）

ALPHA 60A 油门行程固化为 **1100–1940 μs**，**无需电调校准**，飞控 PWM 范围必须对齐。

| 参数 | 值 | 说明 |
|------|-----|------|
| `Q_M_PWM_MIN` | 1100 | 对齐 ALPHA 电调最小油门（μs），不要用默认 1000 |
| `Q_M_PWM_MAX` | 1940 | 对齐 ALPHA 电调最大油门（μs），不要用默认 2000 |
| `Q_M_PWM_TYPE` | 0 | 普通 PWM；ESC 支持 DShot 时可改 |
| `Q_RC_SPEED` | 500 | ESC 刷新率（Hz），对齐 ALPHA 标称 500 Hz |
| `Q_M_SPIN_ARM` | 0.08 | 解锁后电机怠速旋转占空比 |
| `Q_M_SPIN_MIN` | 0.12 | 推力有效起点；台架标定后微调（大桨约 0.10–0.12） |
| `Q_M_SPIN_MAX` | 0.92 | 上限留 8% 余量，避免顶满 31 A 电机极限 |
| `Q_M_THST_EXPO` | 0.60 | 推力线性化指数；Alpha FOC 内置线性化，比普通大桨 0.75 低 |
| `Q_M_THST_HOVER` | 0.55 | 悬停油门初值（约 4.9 kg/桨）；首飞偏低更安全 |
| `Q_M_HOVER_LEARN` | 2 | 悬停时自动学习修正 `Q_M_THST_HOVER` |
| `Q_M_SPOOL_TIME` | 0.30 | 电机启动加速时间（s）；大桨惯量大，略长于默认 |
| `Q_M_YAW_HEADROOM` | 300 | 偏航控制预留油门余量；20 kg 大桨建议加大 |
| `Q_M_SPOOL_TIM_DN` | 0 | 保持默认 |
| `Q_M_SAFE_TIME` | 1 | 解锁后安全延时（s） |

**EXPO 微调规则**：

- 悬停高频快振荡 → 降至 **0.50–0.55**（Alpha 过度补偿）
- 悬停软、高度掉 → 升至 **0.65**
- 最终用台架数据 + [ArduPilot Thrust Expo 工具](https://firmware.ardupilot.org/Tools/WebTools/ThrustExpo/) 拟合

---

## 5. 12S 电池监视

| 参数 | 值 | 说明 |
|------|-----|------|
| `Q_M_BAT_VOLT_MAX` | 50.4 | 12S 满电电压（12 × 4.2 V） |
| `Q_M_BAT_VOLT_MIN` | 42.0 | 12S 低压截止（12 × 3.5 V） |
| `Q_M_BAT_CURR_MAX` | 100 | 整机电流上限（A）；按电池 C 率调整 |
| `Q_M_BAT_CURR_TC` | 5 | 电流滤波时间常数（s） |
| `Q_M_BAT_IDX` | 0 | 使用 BATT 监视器 0 号电池 |
| `BATT_MONITOR` | 4 | 电压 + 电流传感器 |
| `BATT_CAPACITY` | 16000 | 电池容量（mAh），按实装填写 |
| `BATT_LOW_VOLT` | 42.0 | 低压报警（V） |
| `BATT_CRT_VOLT` | 39.6 | 严重低压（V） |
| `BATT_LOW_MAH` | 1280 | 剩余容量报警（mAh），约为 16000×8% |

---

## 6. 姿态控制（20 kg 首飞保守值）

| 参数 | 值 | 说明 |
|------|-----|------|
| `Q_A_ANG_RLL_P` | 5.0 | 滚转角度环 P；默认值略降，大惯量机体更稳 |
| `Q_A_ANG_PIT_P` | 5.0 | 俯仰角度环 P |
| `Q_A_ANG_YAW_P` | 4.0 | 偏航角度环 P |
| `Q_A_RAT_RLL_P` | 0.085 | 滚转角速率 P |
| `Q_A_RAT_RLL_I` | 0.085 | 滚转角速率 I |
| `Q_A_RAT_RLL_D` | 0.001 | 滚转角速率 D |
| `Q_A_RAT_PIT_P` | 0.085 | 俯仰角速率 P |
| `Q_A_RAT_PIT_I` | 0.080 | 俯仰角速率 I |
| `Q_A_RAT_PIT_D` | 0.001 | 俯仰角速率 D |
| `Q_A_RAT_YAW_P` | 0.160 | 偏航角速率 P |
| `Q_A_RAT_YAW_I` | 0.016 | 偏航角速率 I |
| `Q_A_RAT_YAW_D` | 0.000 | 偏航角速率 D；大桨偏航一般不用 D |
| `Q_A_ACCEL_R_MAX` | 28000 | 滚转最大角加速度（cd/s/s）；首飞保守 |
| `Q_A_ACCEL_P_MAX` | 28000 | 俯仰最大角加速度 |
| `Q_A_ACCEL_Y_MAX` | 7000 | 偏航最大角加速度 |
| `Q_A_INPUT_TC` | 0.25 | 遥控输入平滑时间常数（s）；大机体略加长 |

---

## 7. 高度与位置控制

| 参数 | 值 | 说明 |
|------|-----|------|
| `Q_P_ACCZ_P` | 0.55 | 垂直加速度环 P；20 kg 略高于默认 0.3 |
| `Q_P_ACCZ_I` | 1.0 | 垂直加速度环 I |
| `Q_P_ACCZ_IMAX` | 800 | 垂直加速度环积分限幅 |
| `Q_P_POSZ_P` | 1.0 | 高度位置环 P |
| `Q_P_VELZ_P` | 5.0 | 垂直速度环 P |
| `Q_PILOT_ACCEL_Z` | 2.0 | 飞行员模式最大垂直加速度（m/s²） |
| `Q_PILOT_SPD_UP` | 2.0 | 最大上升速度（m/s） |
| `Q_PILOT_SPD_DN` | 1.5 | 最大下降速度（m/s） |
| `Q_P_POSXY_P` | 0.5 | 水平位置环 P（默认） |
| `Q_P_VELXY_P` | 0.7 | 水平速度环 P（默认） |

---

## 8. 首飞安全限制

| 参数 | 值 | 说明 |
|------|-----|------|
| `Q_ANGLE_MAX` | 2500 | 最大倾角 25°（单位 0.01°） |
| `Q_LOIT_ANG_MAX` | 12 | LOITER 模式最大倾角（°） |
| `Q_LOIT_ACC_MAX` | 200 | LOITER 水平加速度上限（cm/s²）= 2 m/s² |
| `Q_LOIT_SPEED` | 300 | LOITER 水平速度上限（cm/s）= 3 m/s |
| `Q_LAND_FINAL_ALT` | 6 | 降落最后段高度（m） |
| `Q_LAND_FINAL_SPD` | 0.5 | 降落最后段速度（m/s） |
| `Q_RTL_ALT` | 20 | 返航高度（m） |
| `ROLL_LIMIT_DEG` | 40 | FBWA 最大横滚角（°） |

---

## 9. 固定翼空速与转换（与垂起相关）

| 参数 | 值 | 说明 |
|------|-----|------|
| `AIRSPEED_MIN` | 15 | 过渡完成最低空速（m/s），对齐失速 |
| `ARSPD_FBW_MIN` | 19 | FBW/TECS 最低空速（m/s） |
| `Q_ASSIST_SPEED` | 12 | Q Assist 启动空速（m/s），比失速速度低约 3 m/s |
| `AIRSPEED_CRUISE` / `TRIM_ARSP_CM` | 20 / 2000 | 巡航目标空速 20 m/s |
| `AIRSPEED_MAX` | 30 | 最大空速（m/s） |

---

## 10. IMU 基础低通滤波

| 参数 | 值 | 说明 |
|------|-----|------|
| `INS_GYRO_FILTER` | 20 | 陀螺仪低通截止频率（Hz）；须低于 `INS_HNTCH_FREQ` |
| `INS_ACCEL_FILTER` | 20 | 加速度计低通截止频率（Hz） |
| `INS_FAST_SAMPLE` | 1 | 启用快速 IMU 采样（H7 级飞控推荐） |

---

## 11. 谐波陷波滤波（G26 大桨必开）

悬停振动主频：**42 Hz**（电机基频）、**83 Hz**（两叶桨叶通过频率）。

### 11.1 方案 A：无 RPM 遥测 — 油门跟踪陷波（首飞推荐）

| 参数 | 值 | 说明 |
|------|-----|------|
| `INS_HNTCH_ENABLE` | 1 | 启用第一组谐波陷波 |
| `INS_HNTCH_MODE` | 1 | 油门跟踪模式，随油门变化调整陷波频率 |
| `INS_HNTCH_REF` | 0.55 | 参考油门点，对齐 `Q_M_THST_HOVER` |
| `INS_HNTCH_FREQ` | 35 | 陷波最低频率（Hz）；低于悬停 42 Hz，高于 `INS_GYRO_FILTER` |
| `INS_HNTCH_BW` | 14 | 陷波带宽（Hz），约为 `FREQ` 的 40% |
| `INS_HNTCH_FM_RAT` | 0.70 | 最高/最低频率比，覆盖 2000–4000 RPM 转速范围 |
| `INS_HNTCH_HMNCS` | 3 | 陷波谐波掩码：bit0+bit1 = 基频 + 2 次谐波（42/83 Hz） |
| `INS_HNTCH_ATT` | 40 | 陷波衰减深度（dB） |
| `INS_LOG_BAT_MASK` | 1 | 记录 IMU 批次数据，用于振动分析 |
| `INS_LOG_BAT_OPT` | 4 | 日志选项，配合 FFT/振动检查 |

### 11.2 方案 B：有 T-MOTOR DataLink RPM 遥测（后期升级）

| 参数 | 值 | 说明 |
|------|-----|------|
| `SERIAL2_PROTOCOL` | 46 | T-MOTOR DataLink 协议（按实际串口改 n） |
| `SERIAL2_BAUD` | 115200 | DataLink 波特率 |
| `RPM1_TYPE` | 5 | RPM 数据来自 ESC 遥测库 |
| `RPM1_ESC_MASK` | 15 | 使用 Motor1–4 的 RPM（bit0–3） |
| `INS_HNTCH_ENABLE` | 1 | 启用谐波陷波 |
| `INS_HNTCH_MODE` | 3 | ESC 遥测动态跟踪 RPM |
| `INS_HNTCH_REF` | 1 | 不缩放参考频率 |
| `INS_HNTCH_FREQ` | 35 | 最低跟踪频率（Hz） |
| `INS_HNTCH_BW` | 10 | 带宽收窄（用 `OPTS=2` 时防相位滞后） |
| `INS_HNTCH_HMNCS` | 3 | 基频 + 2 次谐波 |
| `INS_HNTCH_OPTS` | 2 | 每电机独立陷波（四旋翼推荐） |

### 11.3 方案 C：静态陷波（最简单，油门变化时效果差）

| 参数 | 值 | 说明 |
|------|-----|------|
| `INS_HNTCH_ENABLE` | 1 | 启用谐波陷波 |
| `INS_HNTCH_MODE` | 0 | 固定频率 |
| `INS_HNTCH_FREQ` | 42 | 悬停电机基频（Hz） |
| `INS_HNTCH_BW` | 21 | 带宽（Hz） |
| `INS_HNTCH_HMNCS` | 3 | 基频 + 2 次谐波 |
| `INS_HNTC2_ENABLE` | 1 | 可选第二组陷波 |
| `INS_HNTC2_FREQ` | 83 | 桨叶通过频率（Hz） |
| `INS_HNTC2_BW` | 25 | 第二组带宽（Hz） |

---

## 12. 角速率环滤波

| 参数 | 值 | 说明 |
|------|-----|------|
| `Q_A_RAT_RLL_FLTT` | 20 | 滚转目标角速率低通（Hz） |
| `Q_A_RAT_RLL_FLTD` | 12 | 滚转 D 项低通（Hz）；大桨噪声主要在 D 项，略高于默认 10 |
| `Q_A_RAT_RLL_FLTE` | 0 | 滚转不用加速度计误差馈入 |
| `Q_A_RAT_RLL_NTF` | 1 | 滚转目标路径应用 `INS_HNTCH` 陷波 |
| `Q_A_RAT_RLL_NEF` | 0 | 首飞不对滚转误差做陷波 |
| `Q_A_RAT_PIT_FLTT` | 20 | 俯仰目标角速率低通（Hz） |
| `Q_A_RAT_PIT_FLTD` | 12 | 俯仰 D 项低通（Hz） |
| `Q_A_RAT_PIT_FLTE` | 0 | 俯仰不用加速度计误差馈入 |
| `Q_A_RAT_PIT_NTF` | 1 | 俯仰目标路径应用谐波陷波 |
| `Q_A_RAT_PIT_NEF` | 0 | 首飞不对俯仰误差做陷波 |
| `Q_A_RAT_YAW_FLTT` | 20 | 偏航目标角速率低通（Hz） |
| `Q_A_RAT_YAW_FLTD` | 20 | 偏航 D 项低通（Hz） |
| `Q_A_RAT_YAW_FLTE` | 2.5 | 偏航加速度计辅助误差滤波（Hz） |
| `Q_A_RAT_YAW_NTF` | 0 | 偏航一般不对目标做陷波 |

---

## 13. 位置环滤波

| 参数 | 值 | 说明 |
|------|-----|------|
| `Q_P_ACCZ_FLTE` | 10 | 高度加速度环误差低通（Hz） |
| `Q_P_ACCZ_FLTD` | 0 | 高度加速度环 D 项滤波（不用） |
| `Q_P_ACCZ_FLTT` | 0 | 高度加速度环目标滤波（不用） |
| `Q_P_VELXY_FLTE` | 5 | 水平速度误差低通（Hz） |
| `Q_P_VELXY_FLTD` | 5 | 水平速度 D 项低通（Hz） |
| `Q_P_VELZ_FLTE` | 5 | 垂直速度误差低通（Hz） |
| `Q_P_VELZ_FLTD` | 5 | 垂直速度 D 项低通（Hz） |

---

## 14. Mission Planner 可导入参数块

复制以下内容 → Mission Planner → CONFIG → Full Parameter List → Load from file：

```text
# Transwing 20kg U8II+G26x8.5+ALPHA60A 首飞参数
# 2026-06-24

# --- QuadPlane 构型 ---
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

# --- 电机通道 ---
SERVO1_FUNCTION,33
SERVO2_FUNCTION,34
SERVO3_FUNCTION,35
SERVO4_FUNCTION,36
SERVO11_FUNCTION,41

# --- 电机 PWM / 推力 ---
Q_M_PWM_MIN,1100
Q_M_PWM_MAX,1940
Q_RC_SPEED,500
Q_M_SPIN_ARM,0.08
Q_M_SPIN_MIN,0.12
Q_M_SPIN_MAX,0.92
Q_M_THST_EXPO,0.60
Q_M_THST_HOVER,0.55
Q_M_HOVER_LEARN,2
Q_M_SPOOL_TIME,0.30
Q_M_YAW_HEADROOM,300

# --- 12S 电池 ---
Q_M_BAT_VOLT_MAX,50.4
Q_M_BAT_VOLT_MIN,42.0
Q_M_BAT_CURR_MAX,100
Q_M_BAT_CURR_TC,5

# --- 姿态控制 ---
Q_A_ANG_RLL_P,5.0
Q_A_ANG_PIT_P,5.0
Q_A_ANG_YAW_P,4.0
Q_A_RAT_RLL_P,0.085
Q_A_RAT_RLL_I,0.085
Q_A_RAT_RLL_D,0.001
Q_A_RAT_PIT_P,0.085
Q_A_RAT_PIT_I,0.080
Q_A_RAT_PIT_D,0.001
Q_A_RAT_YAW_P,0.160
Q_A_RAT_YAW_I,0.016
Q_A_RAT_YAW_D,0.000
Q_A_ACCEL_R_MAX,28000
Q_A_ACCEL_P_MAX,28000
Q_A_ACCEL_Y_MAX,7000
Q_A_INPUT_TC,0.25

# --- 高度位置 ---
Q_P_ACCZ_P,0.55
Q_P_ACCZ_I,1.0
Q_P_ACCZ_IMAX,800
Q_P_POSZ_P,1.0
Q_P_VELZ_P,5.0
Q_PILOT_ACCEL_Z,2.0
Q_PILOT_SPD_UP,2.0
Q_PILOT_SPD_DN,1.5

# --- 首飞限制 ---
Q_ANGLE_MAX,2500
Q_LOIT_ANG_MAX,12
Q_LOIT_ACC_MAX,200
Q_LOIT_SPEED,300
Q_LAND_FINAL_ALT,6
Q_LAND_FINAL_SPD,0.5
Q_RTL_ALT,20
ROLL_LIMIT_DEG,40

# --- 空速转换 ---
AIRSPEED_MIN,15
ARSPD_FBW_MIN,15
Q_ASSIST_SPEED,12
AIRSPEED_CRUISE,20
TRIM_ARSP_CM,2000
AIRSPEED_MAX,30

# --- IMU 低通 ---
INS_GYRO_FILTER,20
INS_ACCEL_FILTER,20

# --- 谐波陷波（油门跟踪）---
INS_HNTCH_ENABLE,1
INS_HNTCH_MODE,1
INS_HNTCH_REF,0.55
INS_HNTCH_FREQ,35
INS_HNTCH_BW,14
INS_HNTCH_FM_RAT,0.70
INS_HNTCH_HMNCS,3
INS_HNTCH_ATT,40
INS_LOG_BAT_MASK,1
INS_LOG_BAT_OPT,4

# --- 角速率滤波 ---
Q_A_RAT_RLL_FLTT,20
Q_A_RAT_RLL_FLTD,12
Q_A_RAT_RLL_FLTE,0
Q_A_RAT_RLL_NTF,1
Q_A_RAT_PIT_FLTT,20
Q_A_RAT_PIT_FLTD,12
Q_A_RAT_PIT_FLTE,0
Q_A_RAT_PIT_NTF,1
Q_A_RAT_YAW_FLTT,20
Q_A_RAT_YAW_FLTD,20
Q_A_RAT_YAW_FLTE,2.5

# --- 位置环滤波 ---
Q_P_ACCZ_FLTE,10
Q_P_VELXY_FLTE,5
Q_P_VELXY_FLTD,5
Q_P_VELZ_FLTE,5
Q_P_VELZ_FLTD,5
```

---

## 15. 首飞检查清单

1. **Motor Test**：确认 A/B/C/D 与物理位置、旋向一致。  
2. **折叠舵机**：QSTABILIZE 下 SERVO11 到悬停位（θ≈90°）后再加油门。  
3. **台架标定**：记录各油门点拉力，微调 `Q_M_THST_EXPO` 和 `Q_M_SPIN_MIN`。  
4. **悬停学习**：QHOVER 悬停 ≥30 s，检查 `Q_M_THST_HOVER` 是否收敛到 0.50–0.60。  
5. **振动检查**：日志中 VibeX/Y/Z < 30 m/s²；42/83 Hz 峰应被陷波抑制。  
6. **油门差异**：观察四路 `RCOU` 是否均衡；推力中心偏后 162.5 mm 可能导致俯仰微调。

---

## 16. 参考文档

- ArduPilot QuadPlane 调参：[VTOL Tuning Process](https://ardupilot.org/plane/docs/quadplane-vtol-tuning-process.html)
- 推力线性化：[Motor Thrust Scaling](https://ardupilot.org/plane/docs/motor-thrust-scaling.html)
- Thrust Expo 在线工具：[firmware.ardupilot.org/Tools/WebTools/ThrustExpo](https://firmware.ardupilot.org/Tools/WebTools/ThrustExpo/)
- 谐波陷波：[IMU Notch Filtering](https://ardupilot.org/plane/docs/common-imu-notch-filtering.html)
- 本仓库：`Transwing_实机固件与参数配置.md`、`当前建模数据汇总.md`

---

*本文档由 Transwing 项目参数讨论整理，首飞前请结合台架实测微调。*
