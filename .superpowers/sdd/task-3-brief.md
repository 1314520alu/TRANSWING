### Task 3: Dual-track theta_est + CONTROL gate + TWFB log

**Files:**
- Modify: `scripts/transwing_dynamic_mix.lua`锛坄update()`銆乣effective_mix_mode` / `can_takeover_motors`銆乣fold_slew_active`锛?- Modify: `transwing_lua_mix_model.test.mjs`锛堟柇瑷€ `TWFB`銆乣FB_REQ`銆乣theta_ol`锛?
**Interfaces:**
- Consumes: `poll_fold_mavlink`銆乣compute_fb_ok`銆乣fold_pct_to_theta`
- Produces: `theta_est` 鏉ユ簮閫夋嫨锛沗effective_mix_mode` 鍦?FB_REQ 鏃堕檷绾э紱`logger:write("TWFB", ...)`

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

锛坄TW_DEG` 鍙€夛紱鑻ュ疄鐜板垯鏂█ `send_named_float`銆傛渶灏戞柇瑷€ `TWFB` + `theta_ol` + `FB_REQ`銆傦級

- [ ] **Step 2: Run 鈥?expect FAIL**

- [ ] **Step 3: Introduce `theta_ol` and rewrite estimate updates in `update()`**

鐘舵€侊細

```lua
local theta_ol = 0
```

鍦?`update()` 涓紝鍙栧緱 `now_ms` / `dt` 涓?ENABLE 涔嬪悗锛?
```lua
poll_fold_mavlink(now_ms)
local fb_ok_now = compute_fb_ok(now_ms)
```

鏇挎崲鐜版湁涓ゅ绾紑鐜?`step_theta_estimate` 璧嬪€奸€昏緫涓哄弻杞細

1. **闈?fold_slew 璺緞**锛堝師 716鈥?18 闄勮繎锛夛細

```lua
theta_ol = step_theta_estimate(theta_ol, theta_target, dt, rate_up, rate_dn)
if fb_ok_now then
  theta_est = fold_pct_to_theta(fold_pct)
  theta_ol = theta_est
else
  theta_est = theta_ol
end
```

2. **fold_slew 璺緞**锛堝師 767鈥?68 鍦?`slew_target` 涔嬪悗锛夛細寮€鐜建璺?`slew_target`锛屽啀鎸?`fb_ok` 閫夋嫨锛?*鑻?`fb_ok`锛宖old 鑸垫満 PWM 杈撳嚭浠嶇敤鎸囦护杞?*锛堣涓嬶級锛?
```lua
theta_ol = step_theta_estimate(theta_ol, slew_target, dt, rate_up, rate_dn)
local theta_cmd_out = theta_ol
if fb_ok_now then
  theta_est = fold_pct_to_theta(fold_pct)
  theta_ol = theta_est
else
  theta_est = theta_ol
end
-- apply_fold_servo_output(..., theta_cmd_out, ...)  // 鍛戒护鐢ㄥ紑鐜?slew 鎸囦护瑙掞紝涓嶇敤鍙嶉瑙掑弽鍐?```

瑕佺偣锛坰pec 瀵归綈锛夛細

- **娣锋帶 / 瀹堝崼**鐢?`theta_est`锛堝弽棣堜紭鍏堬級
- **鍐欐姌鍙犺埖鏈?PWM**锛圕ONTROL slew锛夌敤鍚?`slew_target` 閫艰繎鐨?*鎸囦护瑙?* `theta_cmd_out`锛岄伩鍏嶇敤鍙嶉瑙掑綋鎸囦护閫犳垚姝ｅ弽棣?- `fold_cmd_init` 浠嶅彲鐢?PWM 鍒濆鍖?`theta_ol` / `theta_est`

- [ ] **Step 4: Gate CONTROL on FB_REQ**

鏀?`effective_mix_mode` 鎴栧湪鍏惰繑鍥炲悗绔嬪嵆闄嶇骇锛堟帹鑽愰泦涓嚱鏁帮級锛?
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

鎵€鏈?`effective_mix_mode()` 璋冪敤鏀逛负浼犲叆褰撳墠 `fb_ok_now`锛坅nnounce 璺緞鍙厛 `poll` 鍐嶇畻锛屾垨 announce 鐢?`compute_fb_ok(millis())`锛夈€?
`can_takeover_motors` 澧炲姞锛?
```lua
if P.FB_REQ:get() >= 0.5 and not fb_ok_flag then return false end
```

锛堥€氳繃鍙傛暟浼犲叆 `fb_ok_flag`锛岄伩鍏嶈鍏ㄥ眬闅愬紡鐘舵€併€傦級

`fold_slew_active`锛氫粎褰?*鏈夋晥** CONTROL锛堟湭琚?FB_REQ 闄嶇骇锛変负 true 鈥斺€?鍗冲熀浜?`effective_mix_mode(fb_ok)` 鐨勭粨鏋滐紝涓嶈鐢ㄥ師濮?`TW_MIX_MODE`銆?
- [ ] **Step 5: TWFB log + optional TW_DEG**

鍦ㄧ幇鏈?`logger:write("TWNG"...` 闄勮繎锛?
```lua
local src = fb_ok_now and 1 or 0
logger:write("TWFB", "Pct,Cnt,Flt,Hld,Ok,Src", "ffffff",
  fold_pct, fold_cnt, fold_flt, fold_hld, fb_ok_now and 1 or 0, src)

-- 鍙€夛紝绾?2 Hz锛氱敤 last_named_ms 鑺傛祦
if now_ms - (last_named_ms or 0) >= 500 then
  gcs:send_named_float("TW_DEG", theta_est)
  last_named_ms = now_ms
end
```

- [ ] **Step 6: Run all host tests 鈥?PASS**

```bash
node --test transwing_lua_mix_model.test.mjs
```

- [ ] **Step 7: Commit**

```bash
git add scripts/transwing_dynamic_mix.lua transwing_lua_mix_model.test.mjs
git commit -m "feat: drive TW theta_est from fold MAVLink feedback"
```

---

