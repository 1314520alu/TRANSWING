# Transwing ArduPilot QuadPlane/Tilt-Rotor 参数配置

本文档用于第一阶段配置目标：先使用 ArduPilot 原生 `QuadPlane` / `Tilt-Rotor` 能力完成悬停、姿态控制和基础转换验证。后续再用 Lua 或 C++ 处理 Transwing 特有的动态混控，也就是电机位置、力臂、推力方向随折叠角一起变化。

**实机试飞固件选择与完整参数导入清单**见 **`Transwing_实机固件与参数配置.md`**。

## 1. 构型结论

当前 Transwing 最接近的 ArduPilot 构型是：

```text
ArduPlane
  -> QuadPlane
     -> Tilt-Rotor / Tilt-Wing
        -> Quad X hover layout
        -> four motors tilt together
```

不要按 tailsitter 配置。该机垂起时机身不是整体竖直姿态，固定翼和垂起之间主要通过机翼/电机折叠改变推力方向。

## 2. 基础 QuadPlane 参数

| 参数 | 建议值 | 说明 |
|---|---:|---|
| `Q_ENABLE` | `1` | 启用 QuadPlane |
| `Q_FRAME_CLASS` | `1` | Quad，四旋翼悬停布局 |
| `Q_FRAME_TYPE` | `1` | X 构型 |
| `Q_TILT_ENABLE` | `1` | 启用 Tilt-Rotor |
| `Q_TILT_MASK` | `15` | 四个电机都参与倾转，bit0-bit3 = Motor1-Motor4 |
| `Q_TILT_TYPE` | `0` | 连续倾转。若机构只能两档锁定，才改为 `1` Binary |
| `Q_TILT_MAX` | `90` | 原生倾转上限；折叠角约 `90 - Q_TILT_MAX`。设太小会卡在 1333/1500；55°/30° 由 Lua 守卫 |
| `Q_TILT_RATE_UP` | `4.5` | 初始向垂直方向转换速率，单位 deg/s；按 90 deg / 20 s 执行器速度匹配 |
| `Q_TILT_RATE_DN` | `4.5` | 初始向前飞方向转换速率，单位 deg/s；若为 `0` 则跟随 `Q_TILT_RATE_UP` |
| `Q_TILT_FIX_GAIN` | `0` | 第一阶段不使用固定翼模式下的倾转辅助控制 |
| `Q_TILT_FIX_ANGLE` | `0` | 第一阶段不使用固定翼模式下的倾转辅助控制 |
| `Q_TILT_YAW_ANGLE` | `0` | 第一阶段不做 vectored yaw |
| `Q_TRANSITION_MS` | `25000` | SITL 前飞转换时间窗口，匹配慢速折叠机构 |

第一阶段的重点是让飞控把 90 deg 折叠状态当作标准 Quad X 来悬停，并用 ArduPilot 原生倾转流程完成基础转换。不要在同一阶段同时打开倾转辅助、矢量偏航和自定义动态混控。

### 2.1 前飞转换模式建议

SITL 与试飞数据表明：

| 模式 | 行为 | 转换建议 |
|---|---|---|
| **FBWB**（Mode 6） | 油门手控，TECS 不强制俯仰 | **默认用于前飞转换**，空速 ≥11 m/s 再启动 |
| **FBWA**（Mode 5） | TECS 管空速/俯仰 | 低空速易俯仰过大触发守卫；仅在高空速巡航段使用 |

Lua 守卫参数（`transwing_sitl_mp.params`）建议：

```text
TW_BLEND_AS = 11
TW_FW_AS = 15
TW_ACCEL_MIN = 55
TW_BLEND_MIN = 30
TW_GUARD_FBWA = 1
```

## 3. 电机编号与旋向

当前按 Quad X 映射：

| ArduPilot 电机 | Mission Planner Motor Test | 物理位置，90 deg 悬停状态 | 旋向 |
|---|---|---|---|
| `MOTOR 1` | `A` | 右前 | CCW |
| `MOTOR 2` | `C` | 左后 | CCW |
| `MOTOR 3` | `D` | 左前 | CW |
| `MOTOR 4` | `B` | 右后 | CW |

Mission Planner Motor Test 按 `A -> B -> C -> D` 测试时，实际响应顺序应为：

```text
MOTOR 1 -> MOTOR 4 -> MOTOR 2 -> MOTOR 3
```

## 4. 输出通道配置

ArduPilot QuadPlane 默认通常把固定翼舵面放在输出 1-4，把 Quad X 电机放在输出 5-8。当前 Transwing 资料已经按 12 路重新整理为 1-4 电机、5-12 舵机/作动器，因此需要手动设置 `SERVOx_FUNCTION`。

### 4.1 当前建议通道表

| 输出 | `SERVOx_FUNCTION` | 功能 | 连接对象 | 备注 |
|---:|---:|---|---|---|
| `SERVO1` | `33` | `Motor1` | 右前 ESC | Motor Test A，CCW |
| `SERVO2` | `34` | `Motor2` | 左后 ESC | Motor Test C，CCW |
| `SERVO3` | `35` | `Motor3` | 左前 ESC | Motor Test D，CW |
| `SERVO4` | `36` | `Motor4` | 右后 ESC | Motor Test B，CW |
| `SERVO5` | `4` | Aileron | 左副翼舵机 | 方向需地面检查 |
| `SERVO6` | `4` | Aileron | 右副翼舵机 | 可独立设置反向、行程和中位 |
| `SERVO7` | `19` | Elevator | 左水平尾翼舵机 | 方向需地面检查 |
| `SERVO8` | `19` | Elevator | 右水平尾翼舵机 | 可独立设置反向、行程和中位 |
| `SERVO9` | `21` | Rudder | 左方向舵舵机 | 方向需地面检查 |
| `SERVO10` | `21` | Rudder | 右方向舵舵机 | 可独立设置反向、行程和中位 |
| `SERVO11` | `41` | TiltMotorsFront | 机翼折叠/倾转作动器 | Tilt-wing 用法，控制整套折叠机构 |
| `SERVO12` | `19` 或 `0` | Elevator 或 Disabled | 中间升降舵/AUX | 第一阶段建议先 `0`，确认机构后再参与俯仰 |

如果左右机翼折叠有两个独立舵机，但第一阶段仍希望它们同步动作，可以先让两个输出都使用 `SERVOn_FUNCTION = 41`，再分别调整 `SERVOn_MIN`、`SERVOn_MAX`、`SERVOn_TRIM` 和 `SERVOn_REVERSED`。如果后续要左右差动控制折叠角，再改为 Lua 控制或 vectored tilt 方案。

### 4.2 倾转舵机范围

以 `SERVO11` 为例：

| 参数 | 初始建议 | 说明 |
|---|---:|---|
| `SERVO11_FUNCTION` | `41` | TiltMotorsFront / tilt-wing 控制 |
| `SERVO11_MIN` | 实测值 | 固定翼展开位置，电机推力朝前 |
| `SERVO11_TRIM` | 实测中位 | 机械中点，不一定对应 45 deg |
| `SERVO11_MAX` | 实测值 | 悬停折叠位置，电机推力朝上 |
| `SERVO11_REVERSED` | 实测确定 | 确保 QSTABILIZE 为垂直、MANUAL 为向前 |

地面检查标准：

```text
MANUAL / FBWA: 电机应处于固定翼推进方向
QSTABILIZE / QHOVER: 电机应处于垂直升力方向
```

当前中间执行器从垂直悬停位置到机翼完全展开约需 20 s，因此完整 90 deg 行程对应约 `4.5 deg/s`。第一阶段 `Q_TILT_RATE_UP` 和 `Q_TILT_RATE_DN` 都按 `4.5` 起步，避免飞控指令速度明显快于机构实际速度。

如果地面实测发现“展开”和“折叠”速度不同，应分别设置：

```text
Q_TILT_RATE_DN = 90 / 展开耗时_s
Q_TILT_RATE_UP = 90 / 折叠耗时_s
```

20 s 属于很慢的转换机构，基础转换试飞时要把过渡当成长时间状态，而不是短促动作。初次转换应保持足够高度、空速和电池余量；如果过渡中俯仰力矩明显，不要先加快机构，而是先缩小转换范围、降低油门变化率，并记录折叠角对应的姿态变化。

## 5. 固定翼控制面配置

第一阶段先用普通固定翼控制面，不做复杂联动：

| 控制面 | 推荐函数 | 说明 |
|---|---:|---|
| 左/右副翼 | `4` Aileron | 通过每路 `SERVOx_REVERSED` 和行程调平 |
| 左/右升降舵 | `19` Elevator | 通过每路 `SERVOx_REVERSED` 和行程调平 |
| 左/右方向舵 | `21` Rudder | 通过每路 `SERVOx_REVERSED` 和行程调平 |
| 中间升降舵 | `0` Disabled 或 `19` Elevator | 第一阶段建议先禁用，避免多一组未验证俯仰力矩 |

若左右副翼或左右尾翼存在机械方向相反，不要改飞控姿态方向参数，优先用对应输出的 `SERVOx_REVERSED`、`SERVOx_MIN`、`SERVOx_MAX`、`SERVOx_TRIM` 处理。

## 6. 初始调试顺序

### 6.1 参数写入后

1. 写入基础参数并重启飞控。
2. 确认 `Q_FRAME_CLASS = 1`、`Q_FRAME_TYPE = 1`、`Q_TILT_ENABLE = 1` 生效。
3. 在 Mission Planner Servo Output 页面确认 1-4 是 `Motor1` 到 `Motor4`。
4. 在不装桨状态下做 Motor Test，确认 `A/B/C/D` 与电机物理位置一致。
5. 检查每个 ESC 的旋向，必须符合表格。
6. 检查 QSTABILIZE 模式下机翼/电机折叠到垂直升力位置。
7. 检查 MANUAL 或 FBWA 模式下机翼/电机展开到固定翼推进位置。

### 6.2 首次悬停

1. 第一阶段只在 90 deg 悬停构型验证。
2. 使用 QSTABILIZE 或 QHOVER，低高度、短时间、可随时切断。
3. 若起飞即快速翻滚，优先检查电机编号、旋向、桨方向、飞控朝向。
4. 若缓慢漂移，先记录，不要急着改混控；悬停位置的推力线、重心和机翼姿态都会影响漂移。

### 6.3 基础转换

1. 悬停稳定后再做 QSTABILIZE 到 **FBWB** 的转换检查（推荐），或 FBWA / MANUAL 的地面倾转动作检查。
2. 初始转换速率按执行器实测速度设置，当前先取 `4.5 deg/s`，对应完整展开约 20 s。
3. 前飞转换启动前确保空速 ≥11 m/s；`Q_TRANSITION_MS=25000` 给慢机构足够时间。
4. 初次转换应在足够高度和空旷区域进行，并预期会经历较长的半倾转状态。
5. 若过渡阶段俯仰力矩明显，先缩小转换范围、限制油门变化和记录折叠角，再考虑 Lua 动态补偿。

## 7. 第一阶段不建议打开的功能

| 功能 | 暂不启用原因 |
|---|---|
| Vectored yaw | 需要左右倾转差动或额外几何验证，先用四电机差速偏航 |
| Tilt assist in fixed-wing | 会让固定翼段控制变量增加，先调通基础转换 |
| Lua 动态混控 | 需要先建立原生 QuadPlane 基线，否则问题难定位 |
| 中间升降舵混控 | 俯仰力矩未验证前容易引入额外耦合 |
| 自动任务转换 | 先手动模式验证悬停和转换 |

## 8. 后续 Lua 动态混控预留

Transwing 的特殊点是折叠角变化时，电机不是只改变推力方向，还会改变：

```text
1. 电机位置 r(theta)
2. 推力方向 F_dir(theta)
3. 相对重心的力臂 r(theta) x F(theta)
4. yaw drag 符号和推力偏航力矩
```

已有数据文件可作为 Lua 或 C++ 动态混控的输入参考：

| 文件 | 用途 |
|---|---|
| `折叠角分配表.csv` | 各角度下电机位置、推力方向、力矩 |
| `电机混控因子.csv` | 各角度归一化混控因子 |
| `折叠转轴数据.csv` | 后续刚体旋转模型输入 |
| `输出通道建议.csv` | 输出映射 |

后续 Lua 方案建议按三层做：

| 层级 | 目标 | 第一版实现方式 |
|---|---|---|
| 折叠角状态估计 | 得到当前 `theta` | 先用舵机目标 PWM 反算，后续改传感器闭环 |
| 混控表插值 | 查 `theta` 对应电机因子 | 使用 0/15/30/45/60/75/90 deg 表格线性插值 |
| 输出修正 | 对电机和舵面做补偿 | 先只限制/补偿过渡段，悬停和固定翼端点保持原生控制 |

第一版 Lua 不建议完全接管 ArduPilot 的姿态控制。更稳妥的路径是：先让 ArduPilot 原生 QuadPlane 负责主控制，Lua 只读取模式、折叠角和输出状态，逐步增加过渡段补偿。

当前已经提供 Lua 脚本与完整参数说明：

| 文件 | 说明 |
|---|---|
| `scripts/transwing_dynamic_mix.lua` | ArduPilot Lua 脚本（28 个 `TW_*` 参数） |
| `Transwing_Lua_动态混控仿真说明.md` | **TW 参数详解、过渡守卫、日志格式、实测配置** |
| `transwing_sitl_observe.params` | 实机第一阶段：只守卫/记录，不接管电机 |
| `transwing_sitl_mp.params` | SITL 动态混控接管（`Q_FRAME_CLASS=17`） |
| `transwing_lua_mix_model.mjs` | 与 Lua 同逻辑的本地数学模型 |
| `transwing_lua_mix_model.test.mjs` | 开环角度估算和混控插值测试 |

Lua 参数（守卫门槛、折叠 PWM 映射、混控模式等）的逐项说明见 **`Transwing_Lua_动态混控仿真说明.md` 第 3–4 节**。

因为当前折叠机构是开环 PWM 控制，没有角度传感器，所以脚本内的 `theta_est` 是基于 PWM 目标和执行器速度的估算值，不是真实折叠角。实机动态混控前应优先增加角度反馈、行程开关或执行器状态检测。

## 9. 参数写入清单

以下是第一阶段最小写入集：

```text
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
```

`SERVOx_MIN/MAX/TRIM/REVERSED` 不应直接套模板，必须根据实机舵机方向、机械行程、ESC 校准和安全限位逐项实测。

## 10. 参考依据

- ArduPilot Plane: QuadPlane frame setup
- ArduPilot Plane: Tilt Rotor Planes
- ArduPilot Plane: Autopilot Output Functions
- 本仓库：`当前建模数据汇总.md`
- 本仓库：`输出通道建议.csv`
- 本仓库：`折叠角分配表.csv`
