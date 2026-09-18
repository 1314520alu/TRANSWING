# 折叠执行器 → 飞控 MAVLink 回传说明

**用途**：在另一工程开发 ArduPilot Lua 时，按本文对接 STM32 **折叠翼执行器**回传的实测折叠位置。  
**板端固件仓**：`firmware/wing_fold_actuator`（STM32F103，非 ArduPilot）。  
**板端协议细节**：固件仓 `docs/PROTOCOL_NOTES.md`（USART3 / `FC_MAVLINK`）。  
**现有混控 Lua**：`scripts/transwing_dynamic_mix.lua`（**已对接** `TW_FB_*` 参数，优先用 `fold_pct` 作 `theta_est`）。

**状态（2026-09-18）**：`FcMavlink` 固件已在 USART3 实测通过（PC 嗅探 COM37：五字段各约 5 Hz）。

---

## 1. 系统角色（不要搞反）

```text
飞控 SERVO(折叠通道) ──PWM──► 执行器 PA0          （指令：目标位置）
执行器 USART3 TX     ──MAVLink──► 飞控 SERIALn RX （反馈：实测位置）
执行器 USB CDC       ──ASCII CLI──► PC            （调试，非飞控）
```

| 方向 | 信号 | 含义 |
|------|------|------|
| 飞控 → 板 | PWM 1000–2000 µs | 折叠**指令** |
| 板 → 飞控 | `NAMED_VALUE_FLOAT` | 折叠**反馈**（编码器标定行程） |

Lua 里：`theta_target` 仍可来自折叠通道 PWM；**`theta_est` 应改为用反馈角**（或反馈校正开环估计）。

---

## 2. 硬件与串口

| 项 | 值 |
|----|-----|
| 板端端口 | USART3：PB10 TX / PB11 RX |
| 波特率 | **115200 8N1** |
| 飞控侧 | 任意空闲 UART（例：cUAV V6X **UART4** → 通常 `SERIAL4`） |
| 接线 | 板 TX→飞控 RX，板 RX→飞控 TX（若需双向；当前板端以 **TX 上报为主**），共地 |
| 调试 USB | 板载 USB CDC = CLI（与 MAVLink **不是同一口**） |

飞控参数示例（按实际 `SERIALn` 改）：

```text
SERIALn_PROTOCOL = 1      # MAVLink1（板发 v1；也可用 2，多数版本仍能收 v1）
SERIALn_BAUD     = 115    # 115200
SCR_ENABLE       = 1
```

烧录板端：预设 **`FcMavlink`**（同时开 USB CDC + MAVLink）  
→ `build/FcMavlink/wing_fold_actuator-htd.hex`（HTD）或 `-ak70`。

---

## 3. 协议

- **MAVLink v1**，msgid **251** = `NAMED_VALUE_FLOAT`
- **sysid** = 1，**compid** = 191（`MAV_COMP_ID_ONBOARD_COMPUTER`）
- 帧间隔 **40 ms**（总帧率 **25 Hz**）
- **五个 name 轮询**，每个字段约 **5 Hz**（同一时刻不会五帧齐发）

| name | 类型语义 | 范围 / 单位 | Lua 用途 |
|------|----------|-------------|----------|
| `fold_pct` | 标定行程百分比 | **0–100** | **主反馈**：`theta_deg = fold_pct / 100 * THETA_MAX` |
| `fold_cnt` | 编码器 count | 原始计数 | 标定核对 / 备份 |
| `fold_flt` | 舵机故障闩锁 | 0 正常 / 1 故障 | 故障时勿信角度 |
| `fold_pwm` | 板捕获的指令 PWM | µs，无效可为 0 | 与飞控输出对照，非反馈角 |
| `fold_hld` | HOLD | 0 跟控 / 1 HOLD | HOLD 时机构未跟指令 |

### 角度换算（推荐）

板端 **不发度数**，只发相对 NVM 端点 `count_a`→`count_b` 的百分比：

\[
\theta_{\mathrm{est}} = \frac{\texttt{fold\_pct}}{100}\times\theta_{\max}
\]

Transwing 满行程默认 **\(\theta_{\max}=90^\circ\)**（与混控表 0…90 一致）。若实机行程不是 90°，在 Lua 里改常量，**不要**假设板端会改。

由 count（需与板 NVM 一致）：

\[
\theta_{\mathrm{est}} = \frac{\texttt{fold\_cnt}-\texttt{count\_a}}{\texttt{count\_b}-\texttt{count\_a}}\times\theta_{\max}
\]

### 时效与品质

- 单字段约 5 Hz → Lua 判丢失建议 **> 500–1000 ms** 无任一反馈帧
- `fold_flt == 1` 或 `fold_hld == 1`：反馈仍可显示，但转换/守卫应降级（Hold / 开环 / Abort 策略自定）
- name 最长 **10** 字符；解码后需去掉 `\0` 填充

---

## 4. 与现有 `transwing_dynamic_mix.lua` 的对接状态

| 项 | 开环（`TW_FB_EN=0`） | 已实现于 `transwing_dynamic_mix.lua`（`TW_FB_*`） |
|----|---------------------|--------------------------------------------------|
| `theta_est` | PWM + `TW_RATE_*` 开环 | 优先 **`fold_pct` → 度**（`TW_THETA_MAX`） |
| 传感器 | 无 | F103 编码器闭环位置（MAVLink 251） |
| 失效 fallback | — | 超时 / `fold_flt` / `fold_hld` → 回退 `TW_RATE_*` 开环 |
| 混控 CONTROL | 不强制反馈 | `TW_FB_REQ=1` 且无有效反馈时 **禁止** `MIX_MODE=2` 接管 |
| 日志 | — | DataFlash **`TWFB`**（`Pct,Cnt,Flt,Hld,Ok,Src`） |

参数与行为细节见 **[Transwing_Lua_动态混控仿真说明.md](./Transwing_Lua_动态混控仿真说明.md)** §4.2（`TW_FB_EN/REQ/STALE/THETA_MAX`）。

独立验证仍可用 §5 小脚本或 `tools/fc_mavlink_sniff.py` 在接飞控前嗅探板端五字段。

---

## 5. Lua 接收要点（另一工程可直接用）

```lua
local mavlink_msgs = require("MAVLink/mavlink_msgs")
local MSG_ID = mavlink_msgs.get_msgid("NAMED_VALUE_FLOAT")  -- 251

local THETA_MAX_DEG = 90.0
local STALE_MS = 1000

mavlink:init(32, false)
mavlink:register_rx_msgid(MSG_ID)

-- 在 update() 里：
-- local msg = mavlink:receive_chan()
-- while msg do
--   local d = mavlink_msgs.decode(msg, MSG_ID)
--   local name = (d.name or ""):match("^[^%z]*")
--   -- 按 name 填 fold_pct / fold_cnt / fold_flt / fold_pwm / fold_hld
--   msg = mavlink:receive_chan()
-- end
-- theta_est = (fold_pct / 100.0) * THETA_MAX_DEG   -- 当 fresh 且 flt/hld 正常
```

注意：

- 必须先 `register_rx_msgid(251)`，否则收不到  
- 不要假设每帧都是 `fold_pct`（轮询五名字）  
- `gcs:send_named_float` 只方便地面站看，**不能**代替本脚本内的状态变量  

PC 侧验证板端（不经飞控）：

```powershell
pip install pymavlink
python tools/fc_mavlink_sniff.py COMx
```

（工具在固件仓 `wing_fold_actuator/tools/`。）

---

## 6. 验收清单

### 6.1 台架 / 接线（人工勾选）

- [ ] `SERIALn` 接板 USART3，115200，PROTOCOL MAVLink  
- [ ] 指令 PWM（飞控输出）与 `fold_pwm`（板捕获）在接好 PA0 时可对照  

### 6.2 脚本侧（`transwing_dynamic_mix.lua` 已支持）

- [x] 收 `NAMED_VALUE_FLOAT`（251），轮询解析五字段  
- [x] `fold_pct` 有效时 `theta_est = fold_pct/100 × TW_THETA_MAX`  
- [x] 超过 `TW_FB_STALE` ms 无帧，或 `fold_flt`/`fold_hld` → 回退开环，不再信旧角  
- [x] `TW_FB_REQ=1` 且无有效反馈 → 禁止 `MIX_MODE=2` CONTROL（降为 MIRROR + GCS 告警）  
- [x] DataFlash **`TWFB`** 记录反馈品质  

### 6.3 联调（人工勾选）

- [ ] 手动动折叠：`fold_pct` 随行程变；`TWNG.Est` / `TWTR.Est` 与机构目视一致  
- [ ] 断线或停发：日志 `TWFB.Ok=0`，`theta_est` 切回开环  
- [ ] `fold_flt=1` 时守卫/混控有明确降级（`TWFB.Flt=1`，`Ok=0`）  

---

## 7. 源码索引（板端）

| 文件 | 内容 |
|------|------|
| `App/fc_link.c` | 40 ms 轮询发送五字段 |
| `App/mavlink_nvf.c` | 手搓 MAVLink v1 `NAMED_VALUE_FLOAT` |
| `CMakePresets.json` → `FcMavlink` | `FC_MAVLINK` + `USB_CDC_DEBUG` |
| `docs/PROTOCOL_NOTES.md` | 板端协议笔记 |

检索关键词：`fold_pct`、`NAMED_VALUE_FLOAT`、`FC_MAVLINK`、`FcMavlink`。
