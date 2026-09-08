# 数据契约

`questions.json` 是题目数组，题号从1连续；最低字段：

```json
[{"number":1,"module":"公共基础知识","secondary_type":"法律","core_concept":"具体主考点","difficulty":"中","stem":"完整题干","options":["选项一","选项二","选项三","选项四"],"answer":"B","explanation":"完整解析","material_group":null,"basis_ref":"报告第X页：题型模式","sources":[]}]
```

可添加 `graphic`、计算/推理步骤、实际长度、干扰机制、来源核验日期、选项 ID 和质量复核记录。图形选项也提供不同的可访问标签，不能四项均写“见图”。`basis_ref` 标识命题标准，`sources` 标识现实事实出处；二者不是同一件事。

`blueprint.json` 无需手工拼凑示意配额：默认复制 `standards/blueprint.json` 的完整100题蓝图。外部模式必须转换为相同结构。`modules` 的JSON顺序定义模块顺序；`secondary` 是每个模块到二级题型配额的完整映射；`materials` 是组ID到题数的映射，完整规格在 `material_specs`。

每题额外必填：`basis_ref`（例如baseline:slot-1）、`calculation_steps`、`reasoning_steps`；步骤为实际非负整数。按实际内容填写 `specialist_knowledge`、`strong_interference`、`requires_local_knowledge`。现实事实的 `sources` 至少含title/url，题目可另记verified_at。难度使用易/中/难。

任意原创图形采用：

```json
{"graphic":{"svg":"<svg xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 600 200\">…</svg>","choices_svg":["A的完整SVG","B的完整SVG","C的完整SVG","D的完整SVG"]}}
```

这只是格式说明，省略号不允许进入实际输出。一般几何配图只需svg，不需choices_svg。图形选项的options仍写四个不同可访问文字说明；调整选项时同步重排choices_svg。SVG只允许静态矢量元素、片段ID引用和表示属性，不用脚本、style属性、foreignObject或远程资源。

`materials.json` 是组ID到材料记录的映射：

- 所有材料：kind、title、note（明确包含“模拟数据”）。
- text：完整text。
- table：headers数组与rows二维数组，列数一致，标题/列名/注释包含单位。
- chart：完整svg，以及headers/rows提供与图完全同值的可访问数据表。M2六行年度、年份列+三个指标列；图需双轴清晰，不能依赖固定领域绘图函数。

命令参见SKILL.md。结构校验退出0仅说明格式与配额通过；质量记录检查也不证明学科正确性。图形渲染、事实、数学、唯一性与原创性仍需独立复核。
