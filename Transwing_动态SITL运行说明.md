# Transwing 动态 SITL 运行说明

这版已经在 ArduPilot SITL 里新增了一个自定义机型：

```text
quadplane-transwing
```

它和默认 `quadplane-tilt` 的区别是：默认机型只倾转推力方向，电机安装位置是固定的；`quadplane-transwing` 会按折叠角查表插值，同时改变电机位置、力臂和推力方向。

## 1. 当前约定

| 项目 | 当前值 | 说明 |
|---|---:|---|
| 固件 | `ArduPlane` | 使用原生 QuadPlane/Tiltrotor 控制 |
| SITL 机型 | `quadplane-transwing` | 新增的动态几何模型 |
| 悬停构型 | Quad X | `Q_FRAME_CLASS=1`, `Q_FRAME_TYPE=1` |
| 电机输出 | `SERVO1-4` | `Motor1-4`，函数 `33/34/35/36` |
| 折叠输出 | `SERVO11` | `SERVO11_FUNCTION=41`，原生 `TiltMotorsFront` |
| 折叠几何 | `0/15/30/45/60/75/90 deg` | 来自 `折叠角分配表.csv` |
| 90 deg | 悬停 | 推力向上 |
| 0 deg | 固定翼 | 推力向前 |

## 2. 启动可视化仿真

在 Windows PowerShell 里运行：

```powershell
wsl bash /mnt/c/Users/alu/Desktop/TRANSWING/tools/start_transwing_dynamic_sitl_mp.sh
```

Mission Planner 连接方式：

```text
UDP
端口 14550
```

如果 14550 被占用，可以换端口：

```powershell
wsl bash -lc "MP_PORT=14560 bash /mnt/c/Users/alu/Desktop/TRANSWING/tools/start_transwing_dynamic_sitl_mp.sh"
```

Mission Planner 也要用 UDP 14560。

## 3. 启动后检查

在 MAVProxy 里检查：

```text
param show Q_ENABLE
param show Q_TILT_ENABLE
param show Q_TILT_TYPE
param show Q_TILT_MASK
param show SERVO1_FUNCTION
param show SERVO2_FUNCTION
param show SERVO3_FUNCTION
param show SERVO4_FUNCTION
param show SERVO11_FUNCTION
```

期望值：

```text
Q_ENABLE          1
Q_TILT_ENABLE     1
Q_TILT_TYPE       0
Q_TILT_MASK       15
SERVO1_FUNCTION   33
SERVO2_FUNCTION   34
SERVO3_FUNCTION   35
SERVO4_FUNCTION   36
SERVO11_FUNCTION  41
```

SITL 启动日志里应出现：

```text
Loaded Transwing QuadPlane SITL dynamic geometry
```

## 4. 起飞验证

第一步只验证悬停：

```text
mode QSTABILIZE
arm throttle
servo output 页面确认 SERVO11 逐步走到 1000 附近
rc 3 1500
rc 3 1600
rc 3 1700
```

注意：当前折叠/展开执行器全行程约 20 s，`Q_TILT_RATE_UP/DN=4.5`。如果刚从 MANUAL/FBWA 或默认前飞状态切入 `QSTABILIZE/QHOVER`，不要马上加油门；先等 `SERVO11` 从 2000 附近走到 1000 附近。未折叠到悬停角时，推力仍有很大前向分量，SITL 里会表现为贴地滑动或反复 `SIM Hit ground`。

如果 1700 仍不起飞，再看：

```text
status
servo
param show ARMING_CHECK
param show Q_M_PWM_MIN
param show Q_M_PWM_MAX
param show Q_M_SPIN_ARM
param show Q_M_SPIN_MIN
```

第二步验证基础转换：

```text
mode QLOITER
arm throttle
rc 3 1700
```

爬到安全高度后切到固定翼模式，例如：

```text
mode FBWA
```

观察 `SERVO11` 是否从悬停侧向固定翼侧变化，飞机是否逐步获得向前速度。

## 5. 当前模型限制

这是第一版工程仿真模型，目标是先跑通控制链路。质量、惯量、推力曲线、旋翼反扭矩还不是实机标定值。后续需要用实测重量、重心、惯量、桨电机推力表和折叠执行器实际 PWM 曲线继续收敛。
