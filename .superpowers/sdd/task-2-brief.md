### Task 2: Lua params + MAVLink RX state

**Files:**
- Modify: `scripts/transwing_dynamic_mix.lua`锛堝弬鏁拌〃銆乣mavlink` 鍒濆鍖栥€佹敹鍖呭惊鐜級
- Modify: `transwing_lua_mix_model.test.mjs`锛堟簮鐮佹柇瑷€锛?
**Interfaces:**
- Consumes: Task 1 璇箟锛圠ua 鍐呰仈绛変环閫昏緫锛屼笉 require JS锛?- Produces: 鍏ㄥ眬鐘舵€?`fold_pct, fold_cnt, fold_flt, fold_pwm_fb, fold_hld, fold_have_pct, fold_last_rx_ms`锛涘嚱鏁?`poll_fold_mavlink()`銆乣compute_fb_ok(now_ms)`

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

- [ ] **Step 2: Run 鈥?expect FAIL**

```bash
node --test transwing_lua_mix_model.test.mjs
```

- [ ] **Step 3: Expand TW_ table and add params**

Replace table creation锛堝師 `29` 鈫?`33`锛夊苟杩藉姞锛?
```lua
assert(param:add_table(TABLE_KEY, "TW_", 33), "could not add TW_ parameter table")
-- ... existing 1..29 unchanged ...
assert(param:add_param(TABLE_KEY, 30, "FB_EN", 1), "could not add TW_FB_EN")
assert(param:add_param(TABLE_KEY, 31, "FB_REQ", 1), "could not add TW_FB_REQ")
assert(param:add_param(TABLE_KEY, 32, "FB_STALE", 1000), "could not add TW_FB_STALE")
assert(param:add_param(TABLE_KEY, 33, "THETA_MAX", 90), "could not add TW_THETA_MAX")
```

鍦?`P` 鐨?name 鍒楄〃鏈熬鍔犲叆 `"FB_EN", "FB_REQ", "FB_STALE", "THETA_MAX"`銆?
- [ ] **Step 4: Add mavlink RX module state + poll**

鍦ㄨ剼鏈《閮紙鍙傛暟缁戝畾鍚庯級鍔犲叆锛?
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

娉ㄦ剰锛歚pwm_to_theta_target` 浠嶇敤纭紪鐮?90 鏄犲皠鎸囦护 PWM锛涘疄娴嬭鐢?`THETA_MAX`銆傝嫢鍚庣画瑕佸榻愭寚浠ゆ槧灏勶紝鍙﹀紑浠诲姟锛屾湰 plan 涓嶆敼 PWM鈫旀寚浠よ鍏紡锛堥伩鍏嶆敼鍙樼幇鏈夎埖鏈烘爣瀹氾級銆?
- [ ] **Step 5: Run source assertions 鈥?expect PASS**

```bash
node --test transwing_lua_mix_model.test.mjs
```

- [ ] **Step 6: Commit**

```bash
git add scripts/transwing_dynamic_mix.lua transwing_lua_mix_model.test.mjs
git commit -m "feat: receive fold NAMED_VALUE_FLOAT state in TW Lua"
```

---

