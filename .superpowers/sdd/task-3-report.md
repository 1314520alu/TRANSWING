# Task 3 实施报告

## 状态

已完成并提交 Task 3：双轨 `theta_est`、`FB_REQ` CONTROL 门控和 `TWFB` 日志。

## 提交

- `d6813bf feat: drive TW theta_est from fold MAVLink feedback`
- 提交仅包含 `scripts/transwing_dynamic_mix.lua` 与 `transwing_lua_mix_model.test.mjs`。

## 实现

- `update()` 每轮在 ENABLE 检查后轮询折叠 MAVLink，并计算本轮 `fb_ok_now`。
- 新增独立开环轨 `theta_ol`：反馈有效时 `theta_est` 取 `fold_pct` 映射值并对齐 `theta_ol`；反馈无效时 `theta_est = theta_ol`。
- CONTROL slew 先从 `theta_ol` 生成 `theta_cmd_out`，随后才用反馈更新 `theta_est`；折叠舵机 PWM 明确使用 `theta_cmd_out`，混控和守卫继续使用 `theta_est`。
- `effective_mix_mode(fb_ok_now)` 在 `FB_REQ=1` 且反馈无效时把 CONTROL 降为 MIRROR，并发送一次节流告警；`fold_slew_active` 使用该有效模式。
- `can_takeover_motors` 增加显式反馈有效性门控。
- 新增 `TWFB(Pct,Cnt,Flt,Hld,Ok,Src)` 日志；未实现可选 `TW_DEG`。

## TDD 与测试

- RED：新增源码集成断言后运行测试，断言按预期因缺少 `theta_ol` 失败。
- GREEN：任务 3 定向测试通过：1/1。
- 全量命令：`node --test transwing_lua_mix_model.test.mjs`，20/36 通过。
- 剩余 16 项为任务开始前已存在的基线失败：15 项由 `transwing_lua_mix_model.mjs` 中 `asGuard` 在声明前访问导致；1 项为旧断言仍查找 `SRV_Channels:set_output_pwm(32 + i, blended)`，而当前 Lua 已使用超时输出 API。

## 自审

- 已确认 `apply_fold_servo_output` 接收的是反馈覆盖前保存的 `theta_cmd_out`，未把 `theta_est` 反馈角回灌为本轮 PWM 命令。
- 已确认因 `FB_REQ` 降级后，折叠 slew、动态电机控制和接管回退路径均不会按 CONTROL 执行。
- 未修改或提交工作区内其他用户文件。

## 关注点

- 全量主机测试当前无法全绿，原因是上述既有基线缺陷，不属于 Task 3 指定的两个修改文件范围。
- 本任务只做了主机源码断言验证，尚未进行 SITL/实机 MAVLink 回传联调。
