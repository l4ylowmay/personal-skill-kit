---
name: shenzhen-xingce-html
description: 自包含的深圳行测原创命题与离线 HTML 刷题应用技能。内置报告派生标准、100题蓝图、19类底层模板及校验工具，换设备无需原报告即可工作；也支持以用户报告或八套真题替换基准。优先保证命题质量。
---

# 深圳行测原创命题与 HTML 应用

本包是可迁移的命题标准与执行工具，不是已生成试卷。不得依赖历史聊天、本机路径或未随包提供的文件。读取资源时以本 `SKILL.md` 所在目录为根；运行脚本使用 `python3` 或系统提供的 Python 3，不硬编码运行时路径。

迁移后先运行 `python3 scripts/verify_package.py` 校验随包资源完整性；该校验不需联网或第三方依赖。

## 入口与依据

**默认直接使用随包的报告派生基准**。它来自原《深圳市行测真题命题规律分析报告》的命题规范，另一台设备无需该 PDF 或八套扫描卷。不再向用户索取本包已经提供的标准。

出题前读取 [完整命题基准](standards/baseline.md)、[100题逐位蓝图](standards/blueprint.json) 和 [19类底层模板](standards/templates.json)。统计对比需要 [源样本指标](standards/source-metrics.json)，来源和局限见 [来源清单](standards/source-manifest.json)。JSON 是固定配额的机器依据，baseline.md 解释规则、题材可变范围和质量要求；若两者矛盾，先修复，不能任选一边。

用户明确提供新依据时，可用**报告或八套真题二选一**替换内置基准，按 [来源与蓝图](references/source-and-blueprint.md) 工作。不要把外部样本与内置配额静默混合；另存 profile ID、来源和适配记录。原始文件只是可选更新来源，不是内置模式的启动依赖。

## 执行顺序

1. **选择考点并冻结题位。** 默认100题、90分钟、100分，模块20/20/15/30/15，易中难28/67/5；这是名为 `sz-historical-modal-v1` 的历史仿真基准，不是当前官方大纲。二级配额及每题长度、计算强度、材料组见内置蓝图。先读取 [考点轮换与专项质量检查](references/diversity-and-blueprint.md)，比较可用旧卷，选择本卷考点及解法组合；内置细考点是示例，不是固定重复菜单。完成选择后写入本次 `work/blueprint.json` 并记录哈希，不能只记总题量。
2. **编写新题。** 阅读 [题目质量](references/question-quality.md) 与 [数据契约](references/data-contract.md)。每题关联题位，按材料负担、设问和干扰机制原创；不要只换旧题数字。模板是底层解法，不是唯一指定题面。用户可见解析默认尽量覆盖 A/B/C/D 四项，说明正确项成立依据及各错项排除理由；具体要求见题目质量规范。地方/时政的实际事实在本次命题时核验，不继承2026年的事实有效性。
3. **独立复核。** 导出不含答案解析的视图，重新作答后再比较；所有计算另写独立求解脚本，逻辑按适用情形枚举，事实逐项核对，选项逐项排查双解。运行结构及质量记录检查，修正错误后复验。参考 [校准与复核契约](references/calibration-and-review.md)，另保存图形难度、排序泄题及跨卷解法重复的 `work/diversity-review.json`。不能把填写“通过”或脚本通过当作答案正确的证明。
4. **构建应用。** 使用内置 `assets/app/`，运行 `scripts/build_app.py`，生成单文件离线 HTML。模板接受新题、任意原创内嵌 SVG 和表格，不局限于旧卷五种图形。详细规则见 [HTML验收](references/html-and-acceptance.md)。提交前隐藏答案和考点；交卷后题下显示解析；90分钟绝对截止计时，支持保存、恢复及自动交卷。
5. **最终验收。** 检查结构、质量证据、实际浏览器行为和渲染。通过 `tests/test_tools.py` 只能证明工具在测试条件下工作，不能代替新题验证。未解决正确性或歧义问题时，不交付为“合格卷”。

## 命令与输出

在任意项目目录调用包内脚本（`SKILL_DIR` 指当前技能包位置；路径含空格要引号）：

```sh
python3 "$SKILL_DIR/scripts/validate_bank.py" work/questions.json work/blueprint.json --materials work/materials.json --out work/bank_check.json
python3 "$SKILL_DIR/scripts/quality_gate.py" work/questions.json work/blueprint.json work/review.json --materials work/materials.json --out work/quality_check.json
python3 "$SKILL_DIR/scripts/build_app.py" --questions work/questions.json --materials work/materials.json --blueprint work/blueprint.json --review work/review.json --out app/index.html
```

默认交付 `app/index.html`，底稿留 `work/`。实际浏览器对最终路径测试，并记录文件哈希；检查项见 HTML 验收参考。新的题库要与本次可用原题和以前生成卷比较；没有原卷时诚实标注“未做原卷全文查重”，内置模板并不能代替原题库。

质量优先级：答案正确 > 无歧义 > 依据匹配 > 仿真结构与难度 > 交互与排版。不能为了凑难度比例直接改标签、为了均衡字母改答案、为了省界面工作删除图形或复杂材料。

这个包使不同设备共享同一基准、模板和验收流程；模型能力与复核执行仍决定成品质量，不承诺任何模型自动生成同等质量。最终只报告实际完成的检查、采用的 profile 和成品链接。
