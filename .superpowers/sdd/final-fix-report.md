# Lua 折叠 MAVLink 全分支审查修复报告

## 状态

已修复本轮审查列出的 3 项 Critical 与 3 项 Important。

## TDD 证据

- RED：先扩展 `transwing_lua_mix_model.test.mjs`，完整测试按预期因 `flt=0.5/2` 仍被接受、缺少 `NAMED_VALUE_FLOAT` 模块文件、Lua 未使用独立 `theta_cmd` 而失败。
- GREEN：实现后运行反馈相关定向测试，4/4 通过。
- 完整命令 `node --test transwing_lua_mix_model.test.mjs`：20/36 通过；新增/相关测试全部通过。
- 剩余 16 项与修复前基线一致：15 项为 `evaluateTransition()` 在声明前访问 `asGuard`，1 项为旧源码断言仍查找已淘汰的 `set_output_pwm(32 + i, blended)`。

## 已验证

- 仓库新增 AP 风格 `scripts/modules/MAVLink/mavlink_msg_NAMED_VALUE_FLOAT.lua`；`pymavlink.dialects.v20.common` 确认 `crc_extra=170`。
- Lua 顶层不再直接加载消息模块；初始化在 `pcall` 内，失败后反馈路径保持禁用并仅告警一次。
- `mavlink:init(32, 1)` 两参数均为整数；decode 使用 `{ [251] = "NAMED_VALUE_FLOAT" }` 映射表。
- `theta_cmd` 与会被反馈校正的 `theta_ol` 分离，AP 目标跟踪及舵机输出均使用命令角。
- `fold_flt` / `fold_hld` 以 `>=0.5` 判故障；`TW_FB_EN` 关闭时仍清空 RX 队列，重新开启时清除旧反馈状态。
- 两份部署文档均说明消息模块复制路径、降级行为及正确 API 用法。

## 未验证

- 本机未安装 `lua` / `luac`，未做 Lua 解释器语法检查。
- 尚未进行 SITL 或实机串口联调。
