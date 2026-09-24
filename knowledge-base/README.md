# Transwing 知识库

**推荐架构**：本仓库（GitHub 私有仓）为唯一数据源 → [MaxKB](https://maxkb.cn/) 做团队 AI 问答与 API → 可选飞书 Wiki 同步给人看。

| 层级 | 工具 | 用途 |
|------|------|------|
| 源数据 | 本 Git 仓库 | 版本管理、PR、精确 params/csv |
| 队友协作 | MaxKB 网页 / 可选飞书 Wiki | 浏览、AI 问答 |
| 开发调用 | Cursor Skill + `tools/search_kb.py` | Agent / 脚本检索 |
| ArduPilot 官方全站 | Obsidian 库 `C:\Users\alu\Documents\ArduPilot Wiki` | 离线查阅 Copter/Plane/QuadPlane/Common 等 wiki |

---

## ArduPilot 全站 Obsidian 库

官方 wiki 镜像（CC BY-SA 3.0），与 Transwing 精确参数库**分离**：

| 项目 | 路径 / 命令 |
|------|-------------|
| Obsidian 库 | `C:\Users\alu\Documents\ArduPilot Wiki` |
| 首次 / 全量同步 | `python tools/sync_ardupilot_wiki_obsidian.py` |
| 增量更新 | `python tools/sync_ardupilot_wiki_obsidian.py --update` |
| 仅重建内链 | `python tools/sync_ardupilot_wiki_obsidian.py --relink-only` |
| 同步清单 | `outputs/ardupilot-obsidian-sync/manifest.json` |

源仓库缓存：`.cache/ardupilot_wiki`（Git `ArduPilot/ardupilot_wiki`）。  
**注意**：部分 Parameters 页由 Sphinx 构建时动态生成，纯 RST 导入可能不完整；精确参数仍以 Mission Planner / `.params` 为准。

---

## 快速入口

| 我想… | 看这里 |
|-------|--------|
| 查电机编号、坐标、通道 | [当前建模数据汇总.md](../当前建模数据汇总.md) |
| 理解 RAW vs SIM 坐标 | [docs/transwing_coordinate_chain.md](../docs/transwing_coordinate_chain.md) |
| 首飞 / 实机参数 | [Transwing_实机固件与参数配置.md](../Transwing_实机固件与参数配置.md) |
| 多旋翼动力与滤波 | [docs/Transwing_多旋翼动力与滤波参数配置.md](../docs/Transwing_多旋翼动力与滤波参数配置.md) |
| QuadPlane 倾转通用参数 | [ArduPilot_QuadPlane_TiltRotor_参数配置.md](../ArduPilot_QuadPlane_TiltRotor_参数配置.md) |
| 模式转换与保护 | [Transwing_模式转换与保护说明.md](../Transwing_模式转换与保护说明.md) |
| 守卫动作 TW_* | [Transwing_守卫动作说明.md](../Transwing_守卫动作说明.md) |
| 吹风展开 / 参数调整表 | [docs/Transwing_展开测试参数调整表.md](../docs/Transwing_展开测试参数调整表.md)（[PDF](../docs/Transwing_展开测试参数调整表.pdf)） |
| SITL 运行 | [Transwing_动态SITL运行说明.md](../Transwing_动态SITL运行说明.md) |
| Lua 动态混控 | [Transwing_Lua_动态混控仿真说明.md](../Transwing_Lua_动态混控仿真说明.md) |
| ArduPilot patch 说明 | [patches/ardupilot-transwing-lua-motors-dynamic.md](../patches/ardupilot-transwing-lua-motors-dynamic.md) |

---

## 目录结构（按主题）

### 机体与建模

| 文件 | 说明 |
|------|------|
| [当前建模数据汇总.md](../当前建模数据汇总.md) | 坐标系、Motor A/B/C/D 映射、折叠角模型 |
| [docs/transwing_coordinate_chain.md](../docs/transwing_coordinate_chain.md) | RAW_MOTORS / SIM_MOTORS、衍生表清单 |
| [电机位置数据.csv](../电机位置数据.csv) | 实机测量坐标（RAW） |
| [折叠转轴数据.csv](../折叠转轴数据.csv) | 左右翼转轴 |
| [折叠角分配表.csv](../折叠角分配表.csv) | 各 θ 下位置/推力/力矩 |
| [电机混控因子.csv](../电机混控因子.csv) | 各 θ 混控因子 |
| [输出通道建议.csv](../输出通道建议.csv) | SERVO 通道建议 |

### 固件与参数

| 文件 | 说明 |
|------|------|
| [Transwing_实机固件与参数配置.md](../Transwing_实机固件与参数配置.md) | 实机固件与参数总览 |
| [docs/Transwing_多旋翼动力与滤波参数配置.md](../docs/Transwing_多旋翼动力与滤波参数配置.md) | 首飞动力、滤波、陷波 |
| [docs/Transwing_展开测试参数调整表.md](../docs/Transwing_展开测试参数调整表.md) | 吹风展开 / 首飞参数调整表（[PDF](../docs/Transwing_展开测试参数调整表.pdf)） |
| [ArduPilot_QuadPlane_TiltRotor_参数配置.md](../ArduPilot_QuadPlane_TiltRotor_参数配置.md) | QuadPlane 倾转通用说明 |
| [transwing_hover_motor_filter.params](../transwing_hover_motor_filter.params) | 悬停滤波参数集 |
| [transwing_lua_sitl.params](../transwing_lua_sitl.params) | Lua SITL 参数 |
| [transwing_lua_sitl_control.params](../transwing_lua_sitl_control.params) | Lua SITL 控制参数 |
| [transwing_sitl_mp.params](../transwing_sitl_mp.params) | Mission Planner SITL |
| [transwing_sitl_startup.params](../transwing_sitl_startup.params) | SITL 启动参数 |
| [transwing_sitl_observe.params](../transwing_sitl_observe.params) | SITL 观测参数 |

### SITL、Lua 与混控

| 文件 | 说明 |
|------|------|
| [Transwing_动态SITL运行说明.md](../Transwing_动态SITL运行说明.md) | 动态 SITL 启动与诊断 |
| [Transwing_Lua_动态混控仿真说明.md](../Transwing_Lua_动态混控仿真说明.md) | Lua 混控仿真 |
| [scripts/transwing_dynamic_mix.lua](../scripts/transwing_dynamic_mix.lua) | 动态混控 Lua 脚本 |
| [Transwing_模式转换与保护说明.md](../Transwing_模式转换与保护说明.md) | 模式转换逻辑 |
| [Transwing_守卫动作说明.md](../Transwing_守卫动作说明.md) | TW_* 守卫参数与动作 |

### 设计与计划（内部）

| 文件 | 说明 |
|------|------|
| [docs/superpowers/specs/2026-06-21-transwing-sitl-channel-and-lua-control-design.md](../docs/superpowers/specs/2026-06-21-transwing-sitl-channel-and-lua-control-design.md) | SITL 通道与 Lua 设计 |
| [docs/superpowers/plans/2026-06-21-transwing-sitl-channel-and-lua-control.md](../docs/superpowers/plans/2026-06-21-transwing-sitl-channel-and-lua-control.md) | 实施计划 |
| [docs/superpowers/plans/2026-06-18-transwing-lua-dynamic-mix-sitl.md](../docs/superpowers/plans/2026-06-18-transwing-lua-dynamic-mix-sitl.md) | Lua 动态混控 SITL 计划 |

---

## 命令行检索

```bash
# 关键词搜索（md / csv / params / lua）
python tools/search_kb.py Q_M_THST_HOVER
python tools/search_kb.py TW_BLEND_AS --category guard
python tools/search_kb.py motor --json
```

机器可读目录：[index.yaml](./index.yaml)

---

## MaxKB 部署（队友 + AI API）

1. Docker 部署 MaxKB：<https://maxkb.cn/docs/v2/quick_start/>
2. 创建知识库「Transwing」，上传本仓库中的 md 与 params（或配置 Git 定期导出）
3. 给队友开账号；生成 API Key 供 Cursor / 脚本调用
4. 精确参数以 Git 源文件为准；MaxKB 用于语义问答与 onboarding

## 飞书（可选）

若团队已在飞书：详见 **[FEISHU_GUIDE.md](./FEISHU_GUIDE.md)**。

```bash
python tools/prepare_feishu_kb.py --open   # 按分类导出到 outputs/feishu-kb-export/
```

Wiki 手动建目录分类；上传后飞书云端自动切片向量化。精确参数仍以 Git 源文件为准。

---

*索引版本：2026-09-24。新增文档时请同步更新 `index.yaml` 与本 README。ArduPilot Obsidian 库见上文「ArduPilot 全站 Obsidian 库」。*
