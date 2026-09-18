# Transwing Lua Fold MAVLink Feedback Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 `scripts/transwing_dynamic_mix.lua` 中用折叠执行器 `NAMED_VALUE_FLOAT`（`fold_pct`）实测角驱动 `theta_est`，失效时回退开环，并用 `TW_FB_REQ` 禁止无反馈进入 CONTROL。

**Architecture:** 同文件双轨：每 tick 更新开环 `theta_ol`；MAVLink 收五字段维护状态；`fb_ok` 时 `theta_est = fold_pct→deg` 并对齐 `theta_ol`，否则 `theta_est = theta_ol`。纯逻辑先在 `transwing_lua_mix_model.mjs` 用单测锁定，再改 Lua。

**Tech Stack:** ArduPilot Lua scripting（`mavlink` + `MAVLink/mavlink_msgs`）、Node `node:test`、现有 TW_ 参数表。

**Spec:** `docs/superpowers/specs/2026-09-18-transwing-lua-fold-mavlink-feedback-design.md`

## Global Constraints

- 交付：原地改 `scripts/transwing_dynamic_mix.lua`，不新建主混控脚本
- 主反馈：仅 `fold_pct`；`fold_cnt` 只日志
- `fb_ok`：`FB_EN=1` ∧ 已收到过 `fold_pct` ∧ 未 STALE ∧ `fold_flt≠1` ∧ `fold_hld≠1`
- 失效：立即回退开环；反馈有效时把 `theta_ol` 对齐到 `theta_est`
- 默认：`TW_FB_EN=1`，`TW_FB_REQ=1`，`TW_FB_STALE=1000`，`TW_THETA_MAX=90`
- `TW_FB_REQ=1` 且 `fb_ok=false` → 禁止有效 CONTROL（降为 MIRROR）
- 不改板端协议；SITL 无板时靠 `FB_EN=0` 或 `FB_REQ=0`
- 首飞惯例不变：`Q_FRAME_CLASS=1` 时仍可不启动态混控

---

## File map

| File | Role |
|------|------|
| `transwing_lua_mix_model.mjs` | 纯函数：`fbOk`、`foldPctToTheta`、`selectThetaEst` |
| `transwing_lua_mix_model.test.mjs` | 上述单测 + Lua 源码字符串断言（参数名 / mavlink 注册） |
| `scripts/transwing_dynamic_mix.lua` | 收包、双轨、门控、`TWFB` 日志 |
| `Transwing_折叠执行器_MAVLink回传说明.md` | 标记 Lua 已对接 |
| `Transwing_Lua_动态混控仿真说明.md` | 新参数与 `theta_est` 来源 |
| `knowledge-base/README.md` / `index.yaml` | 若缺条目则补链（已有回传说明则核对） |

---

### Task 1: Host-side fbOk / selectThetaEst (TDD)

**Files:**
- Modify: `transwing_lua_mix_model.mjs`
- Modify: `transwing_lua_mix_model.test.mjs`

**Interfaces:**
- Produces:
  - `fbOk({ en, havePct, lastRxMs, nowMs, staleMs, flt, hld }) → boolean`
  - `foldPctToTheta(foldPct, thetaMax) → number`（pct clamp 0–100）
  - `selectThetaEst({ fbOk, foldPct, thetaMax, thetaOl }) → { thetaEst, thetaOl }`（fb 时对齐 ol）

- [ ] **Step 1: Write failing tests**

Append to `transwing_lua_mix_model.test.mjs`:

```js
import { fbOk, foldPctToTheta, selectThetaEst } from "./transwing_lua_mix_model.mjs";

test("fbOk requires enable, havePct, fresh rx, and clear flt/hld", () => {
  const base = { en: true, havePct: true, lastRxMs: 1000, nowMs: 1500, staleMs: 1000, flt: 0, hld: 0 };
  assert.equal(fbOk(base), true);
  assert.equal(fbOk({ ...base, en: false }), false);
  assert.equal(fbOk({ ...base, havePct: false }), false);
  assert.equal(fbOk({ ...base, nowMs: 2501 }), false);
  assert.equal(fbOk({ ...base, flt: 1 }), false);
  assert.equal(fbOk({ ...base, hld: 1 }), false);
});

test("foldPctToTheta maps 0-100 onto thetaMax", () => {
  assert.equal(foldPctToTheta(0, 90), 0);
  assert.equal(foldPctToTheta(50, 90), 45);
  assert.equal(foldPctToTheta(100, 90), 90);
  assert.equal(foldPctToTheta(-10, 90), 0);
  assert.equal(foldPctToTheta(120, 90), 90);
});

test("selectThetaEst uses feedback and aligns open-loop when fbOk", () => {
  const withFb = selectThetaEst({ fbOk: true, foldPct: 50, thetaMax: 90, thetaOl: 10 });
  assert.equal(withFb.thetaEst, 45);
  assert.equal(withFb.thetaOl, 45);

  const ol = selectThetaEst({ fbOk: false, foldPct: 50, thetaMax: 90, thetaOl: 12 });
  assert.equal(ol.thetaEst, 12);
  assert.equal(ol.thetaOl, 12);
});
```

- [ ] **Step 2: Run tests — expect FAIL**

```bash
node --test transwing_lua_mix_model.test.mjs
```

Expected: FAIL（`fbOk` / `foldPctToTheta` / `selectThetaEst` not exported）

- [ ] **Step 3: Implement pure functions**

Add to `transwing_lua_mix_model.mjs`:

```js
export function fbOk({ en, havePct, lastRxMs, nowMs, staleMs, flt, hld }) {
  if (!en) return false;
  if (!havePct) return false;
  if (lastRxMs == null || nowMs == null) return false;
  if ((nowMs - lastRxMs) > staleMs) return false;
  if (Number(flt) === 1) return false;
  if (Number(hld) === 1) return false;
  return true;
}

export function foldPctToTheta(foldPct, thetaMax) {
  const pct = clamp(Number(foldPct), 0, 100);
  return (pct / 100) * thetaMax;
}

export function selectThetaEst({ fbOk: ok, foldPct, thetaMax, thetaOl }) {
  if (!ok) {
    return { thetaEst: thetaOl, thetaOl };
  }
  const thetaEst = foldPctToTheta(foldPct, thetaMax);
  return { thetaEst, thetaOl: thetaEst };
}
```

- [ ] **Step 4: Run tests — expect PASS**

```bash
node --test transwing_lua_mix_model.test.mjs
```

Expected: PASS（含新测例）

- [ ] **Step 5: Commit**

```bash
git add transwing_lua_mix_model.mjs transwing_lua_mix_model.test.mjs
git commit -m "test: add fold MAVLink feedback theta selection helpers"
```

---

### Task 2: Lua params + MAVLink RX state

**Files:**
- Modify: `scripts/transwing_dynamic_mix.lua`（参数表、`mavlink` 初始化、收包循环）
- Modify: `transwing_lua_mix_model.test.mjs`（源码断言）

**Interfaces:**
- Consumes: Task 1 语义（Lua 内联等价逻辑，不 require JS）
- Produces: 全局状态 `fold_pct, fold_cnt, fold_flt, fold_pwm_fb, fold_hld, fold_have_pct, fold_last_rx_ms`；函数 `poll_fold_mavlink()`、`compute_fb_ok(now_ms)`

- [ ] **Step 1: Write failing Lua-source assertions**

```js
test("lua declares FB params and registers NAMED_VALUE_FLOAT", () => {
  const lua = readFileSync(new URL("./scripts/transwing_dynamic_mix.lua", import.meta.url), "utf8");
  assert.match(lua, /add_param\(TABLE_KEY,\s*30,\s*"FB_EN"/);
  assert.match(lua, /add_param\(TABLE_KEY,\s*31,\s*"FB_REQ"/);
  assert.match(lua, /add_param\(TABLE_KEY,\s*32,\s*"FB_STALE"/);
  assert.match(lua, /add_param\(TABLE_KEY,\s*33,\s*"THETA_MAX"/);
  assert.match(lua, /register_rx_msgid/);
  assert.match(lua, /NAMED_VALUE_FLOAT|msgid.*251|MSG_ID/);
  assert.match(lua, /fold_pct/);
});
```

- [ ] **Step 2: Run — expect FAIL**

```bash
node --test transwing_lua_mix_model.test.mjs
```

- [ ] **Step 3: Expand TW_ table and add params**

Replace table creation（原 `29` → `33`）并追加：

```lua
assert(param:add_table(TABLE_KEY, "TW_", 33), "could not add TW_ parameter table")
-- ... existing 1..29 unchanged ...
assert(param:add_param(TABLE_KEY, 30, "FB_EN", 1), "could not add TW_FB_EN")
assert(param:add_param(TABLE_KEY, 31, "FB_REQ", 1), "could not add TW_FB_REQ")
assert(param:add_param(TABLE_KEY, 32, "FB_STALE", 1000), "could not add TW_FB_STALE")
assert(param:add_param(TABLE_KEY, 33, "THETA_MAX", 90), "could not add TW_THETA_MAX")
```

在 `P` 的 name 列表末尾加入 `"FB_EN", "FB_REQ", "FB_STALE", "THETA_MAX"`。

- [ ] **Step 4: Add mavlink RX module state + poll**

在脚本顶部（参数绑定后）加入：

```lua
local mavlink_msgs = require("MAVLink/mavlink_msgs")
local NVF_MSG_ID = mavlink_msgs.get_msgid("NAMED_VALUE_FLOAT")

local fold_pct = 0
local fold_cnt = 0
local fold_flt = 0
local fold_pwm_fb = 0
local fold_hld = 0
local fold_have_pct = false
local fold_last_rx_ms = nil
local mavlink_rx_ready = false
local warned_fb_req = false

local function ensure_mavlink_rx()
  if mavlink_rx_ready then return true end
  local ok = pcall(function()
    mavlink:init(32, false)
    mavlink:register_rx_msgid(NVF_MSG_ID)
  end)
  mavlink_rx_ready = ok
  return ok
end

local function nvf_name(raw)
  if raw == nil then return "" end
  return tostring(raw):match("^[^%z]*") or ""
end

local function poll_fold_mavlink(now_ms)
  if P.FB_EN:get() < 0.5 then return end
  if not ensure_mavlink_rx() then return end
  local msg = mavlink:receive_chan()
  while msg do
    local ok, decoded = pcall(mavlink_msgs.decode, msg, NVF_MSG_ID)
    if ok and decoded then
      local name = nvf_name(decoded.name)
      local value = decoded.value
      if name == "fold_pct" then
        fold_pct = value
        fold_have_pct = true
        fold_last_rx_ms = now_ms
      elseif name == "fold_cnt" then
        fold_cnt = value
        fold_last_rx_ms = now_ms
      elseif name == "fold_flt" then
        fold_flt = value
        fold_last_rx_ms = now_ms
      elseif name == "fold_pwm" then
        fold_pwm_fb = value
        fold_last_rx_ms = now_ms
      elseif name == "fold_hld" then
        fold_hld = value
        fold_last_rx_ms = now_ms
      end
    end
    msg = mavlink:receive_chan()
  end
end

local function compute_fb_ok(now_ms)
  if P.FB_EN:get() < 0.5 then return false end
  if not fold_have_pct then return false end
  if fold_last_rx_ms == nil then return false end
  if (now_ms - fold_last_rx_ms) > P.FB_STALE:get() then return false end
  if fold_flt == 1 then return false end
  if fold_hld == 1 then return false end
  return true
end

local function fold_pct_to_theta(pct)
  local p = clamp(pct, 0, 100)
  return (p / 100.0) * P.THETA_MAX:get()
end
```

注意：`pwm_to_theta_target` 仍用硬编码 90 映射指令 PWM；实测角用 `THETA_MAX`。若后续要对齐指令映射，另开任务，本 plan 不改 PWM↔指令角公式（避免改变现有舵机标定）。

- [ ] **Step 5: Run source assertions — expect PASS**

```bash
node --test transwing_lua_mix_model.test.mjs
```

- [ ] **Step 6: Commit**

```bash
git add scripts/transwing_dynamic_mix.lua transwing_lua_mix_model.test.mjs
git commit -m "feat: receive fold NAMED_VALUE_FLOAT state in TW Lua"
```

---

### Task 3: Dual-track theta_est + CONTROL gate + TWFB log

**Files:**
- Modify: `scripts/transwing_dynamic_mix.lua`（`update()`、`effective_mix_mode` / `can_takeover_motors`、`fold_slew_active`）
- Modify: `transwing_lua_mix_model.test.mjs`（断言 `TWFB`、`FB_REQ`、`theta_ol`）

**Interfaces:**
- Consumes: `poll_fold_mavlink`、`compute_fb_ok`、`fold_pct_to_theta`
- Produces: `theta_est` 来源选择；`effective_mix_mode` 在 FB_REQ 时降级；`logger:write("TWFB", ...)`

- [ ] **Step 1: Failing assertions for integration hooks**

```js
test("lua selects theta from feedback and gates CONTROL on FB_REQ", () => {
  const lua = readFileSync(new URL("./scripts/transwing_dynamic_mix.lua", import.meta.url), "utf8");
  assert.match(lua, /theta_ol/);
  assert.match(lua, /compute_fb_ok/);
  assert.match(lua, /logger:write\("TWFB"/);
  assert.match(lua, /FB_REQ/);
  assert.match(lua, /fold estimate timeout|TW_DEG|TW_DEG/);
});
```

（`TW_DEG` 可选；若实现则断言 `send_named_float`。最少断言 `TWFB` + `theta_ol` + `FB_REQ`。）

- [ ] **Step 2: Run — expect FAIL**

- [ ] **Step 3: Introduce `theta_ol` and rewrite estimate updates in `update()`**

状态：

```lua
local theta_ol = 0
```

在 `update()` 中，取得 `now_ms` / `dt` 且 ENABLE 之后：

```lua
poll_fold_mavlink(now_ms)
local fb_ok_now = compute_fb_ok(now_ms)
```

替换现有两处纯开环 `step_theta_estimate` 赋值逻辑为双轨：

1. **非 fold_slew 路径**（原 716–718 附近）：

```lua
theta_ol = step_theta_estimate(theta_ol, theta_target, dt, rate_up, rate_dn)
if fb_ok_now then
  theta_est = fold_pct_to_theta(fold_pct)
  theta_ol = theta_est
else
  theta_est = theta_ol
end
```

2. **fold_slew 路径**（原 767–768 在 `slew_target` 之后）：开环轨跟 `slew_target`，再按 `fb_ok` 选择；**若 `fb_ok`，fold 舵机 PWM 输出仍用指令轨**（见下）：

```lua
theta_ol = step_theta_estimate(theta_ol, slew_target, dt, rate_up, rate_dn)
local theta_cmd_out = theta_ol
if fb_ok_now then
  theta_est = fold_pct_to_theta(fold_pct)
  theta_ol = theta_est
else
  theta_est = theta_ol
end
-- apply_fold_servo_output(..., theta_cmd_out, ...)  // 命令用开环/slew 指令角，不用反馈角反写
```

要点（spec 对齐）：

- **混控 / 守卫**用 `theta_est`（反馈优先）
- **写折叠舵机 PWM**（CONTROL slew）用向 `slew_target` 逼近的**指令角** `theta_cmd_out`，避免用反馈角当指令造成正反馈
- `fold_cmd_init` 仍可用 PWM 初始化 `theta_ol` / `theta_est`

- [ ] **Step 4: Gate CONTROL on FB_REQ**

改 `effective_mix_mode` 或在其返回后立即降级（推荐集中函数）：

```lua
local function effective_mix_mode(fb_ok_now)
  local mode = math.floor(P.MIX_MODE:get() + 0.5)
  if mode < MIX_MODE_OBSERVE then mode = MIX_MODE_OBSERVE end
  if mode > MIX_MODE_CONTROL then mode = MIX_MODE_CONTROL end
  if P.LOG_ONLY:get() < 0.5 and mode == MIX_MODE_OBSERVE then
    mode = MIX_MODE_MIRROR
  end
  if mode == MIX_MODE_CONTROL and P.FB_REQ:get() >= 0.5 and not fb_ok_now then
    if not warned_fb_req then
      gcs:send_text(MAV_SEVERITY_WARNING, SCRIPT_NAME .. ": FB_REQ blocks CONTROL (no fold feedback)")
      warned_fb_req = true
    end
    return MIX_MODE_MIRROR
  end
  if fb_ok_now then warned_fb_req = false end
  return mode
end
```

所有 `effective_mix_mode()` 调用改为传入当前 `fb_ok_now`（announce 路径可先 `poll` 再算，或 announce 用 `compute_fb_ok(millis())`）。

`can_takeover_motors` 增加：

```lua
if P.FB_REQ:get() >= 0.5 and not fb_ok_flag then return false end
```

（通过参数传入 `fb_ok_flag`，避免读全局隐式状态。）

`fold_slew_active`：仅当**有效** CONTROL（未被 FB_REQ 降级）为 true —— 即基于 `effective_mix_mode(fb_ok)` 的结果，不要用原始 `TW_MIX_MODE`。

- [ ] **Step 5: TWFB log + optional TW_DEG**

在现有 `logger:write("TWNG"...` 附近：

```lua
local src = fb_ok_now and 1 or 0
logger:write("TWFB", "Pct,Cnt,Flt,Hld,Ok,Src", "ffffff",
  fold_pct, fold_cnt, fold_flt, fold_hld, fb_ok_now and 1 or 0, src)

-- 可选，约 2 Hz：用 last_named_ms 节流
if now_ms - (last_named_ms or 0) >= 500 then
  gcs:send_named_float("TW_DEG", theta_est)
  last_named_ms = now_ms
end
```

- [ ] **Step 6: Run all host tests — PASS**

```bash
node --test transwing_lua_mix_model.test.mjs
```

- [ ] **Step 7: Commit**

```bash
git add scripts/transwing_dynamic_mix.lua transwing_lua_mix_model.test.mjs
git commit -m "feat: drive TW theta_est from fold MAVLink feedback"
```

---

### Task 4: Docs sync

**Files:**
- Modify: `Transwing_折叠执行器_MAVLink回传说明.md`
- Modify: `Transwing_Lua_动态混控仿真说明.md`
- Modify: `knowledge-base/README.md` / `knowledge-base/index.yaml`（仅当索引未链到回传说明或反馈参数时）

- [ ] **Step 1: Update MAVLink 回传说明 §4 / §6**

- §4 表：「接板后目标」改为「已实现于 `transwing_dynamic_mix.lua`（`TW_FB_*`）」
- §6 验收清单：把 Lua 工程项标为脚本侧已支持，台架项保留人工勾选

- [ ] **Step 2: Update Lua 仿真说明**

增加参数表行：

| `TW_FB_EN` | 1 | 启用折叠加馈 |
| `TW_FB_REQ` | 1 | 无反馈禁止 CONTROL |
| `TW_FB_STALE` | 1000 | 反馈超时 ms |
| `TW_THETA_MAX` | 90 | pct→度满行程 |

写明：`theta_est` 优先 `fold_pct`；失效回退 `TW_RATE_*` 开环；CONTROL 写舵机仍用指令 slew 角。

- [ ] **Step 3: Commit**

```bash
git add "Transwing_折叠执行器_MAVLink回传说明.md" "Transwing_Lua_动态混控仿真说明.md" knowledge-base/README.md knowledge-base/index.yaml
git commit -m "docs: document Lua fold MAVLink feedback path"
```

---

## Spec coverage checklist

| Spec 项 | Task |
|---------|------|
| 原地改脚本 + 双轨 | 2–3 |
| `fold_pct` 主反馈 | 2–3 |
| STALE / flt / hld → 开环 | 1, 3 |
| 对齐 `theta_ol` | 1, 3 |
| `TW_FB_EN/REQ/STALE/THETA_MAX` | 2 |
| FB_REQ 禁 CONTROL | 3 |
| `TWFB` 日志 | 3 |
| 可选 `TW_DEG` | 3 |
| JS 单测 | 1 |
| 文档 | 4 |
| 不改板协议 | （无任务） |

## Manual bench (after Task 3, not automated)

1. `SERIALn_PROTOCOL=1`，`BAUD=115`，接板 USART3  
2. 加载脚本：MP 看 `TW_DEG` / 日志 `TWFB`  
3. 动翼：`Src=1`，`Est` 跟目视  
4. 拔线：`Src=0`；`MIX_MODE=2` 且 `FB_REQ=1` → 实际为 MIRROR 并有警告  
