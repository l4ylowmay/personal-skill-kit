#!/usr/bin/env python3
"""Validate an exam bank's structure; never certify semantic correctness."""
import argparse
import collections
import json
import pathlib
import sys


def validate(questions, blueprint, materials=None):
    errors, warnings = [], []
    if not isinstance(questions, list) or not isinstance(blueprint, dict):
        return {'errors': ['questions须为数组，blueprint须为对象'], 'warnings': []}
    def quotas(value, name):
        if not isinstance(value, dict) or any(not isinstance(k, str) or not k or type(v) is not int or v < 0 for k, v in value.items()):
            errors.append(name + '须为名称到非负整数的映射')
            return {}
        return value
    total = blueprint.get('total')
    if type(total) is not int or total <= 0:
        errors.append('total须为正整数')
        total = 0
    mods = quotas(blueprint.get('modules'), 'modules')
    diffs = quotas(blueprint.get('difficulty'), 'difficulty')
    groups = quotas(blueprint.get('materials'), 'materials')
    for name, counts in [('modules', mods), ('difficulty', diffs)]:
        if sum(counts.values()) != total:
            errors.append(name + '配额总数不等于total')
    secondary = blueprint.get('secondary')
    if not isinstance(secondary, dict):
        errors.append('缺少完整secondary配额'); secondary = {}
    if set(secondary) != set(mods):
        errors.append('secondary模块与modules不一致')
    expected_secondary = {}
    for mod, raw in secondary.items():
        counts = quotas(raw, 'secondary.' + str(mod))
        if sum(counts.values()) != mods.get(mod):
            errors.append(str(mod) + '二级题型之和不等于模块配额')
        expected_secondary.update({(mod, typ): n for typ, n in counts.items() if n})
    if sum(groups.values()) > total:
        errors.append('材料题总数超过整卷题数')
    if len(questions) != total:
        errors.append('实际题量不等于total')
    actual_mod, actual_diff, actual_sec, actual_group, answers = [collections.Counter() for _ in range(5)]
    seen, ordered, letters = {}, [], []
    longest_correct = longest_count = 0
    for position, q in enumerate(questions, 1):
        if not isinstance(q, dict):
            errors.append(f'第{position}条不是题目对象'); continue
        prefix = f'题{position}: '
        if type(q.get('number')) is not int or q['number'] != position:
            errors.append(prefix + '题号不连续或类型错误')
        for field in ['module', 'secondary_type', 'core_concept', 'difficulty', 'stem', 'explanation']:
            if not isinstance(q.get(field), str) or not q[field].strip():
                errors.append(prefix + field + '为空或类型错误')
        mod, typ, diff = (q.get(k) for k in ['module', 'secondary_type', 'difficulty'])
        if all(isinstance(v, str) for v in [mod, typ, diff]):
            actual_mod[mod] += 1; actual_diff[diff] += 1; actual_sec[(mod, typ)] += 1
            ordered.append(mod)
        group = q.get('material_group')
        if group is not None:
            if not isinstance(group, str) or group not in groups:
                errors.append(prefix + '未知材料组')
            else:
                actual_group[group] += 1
        if not q.get('basis_ref'):
            warnings.append(prefix + '未记录命题依据索引')
        options = q.get('options')
        valid_options = isinstance(options, list) and len(options) == 4 and all(isinstance(x, str) and x.strip() for x in options)
        if not valid_options:
            errors.append(prefix + '须有四个非空文本选项')
        elif len({x.strip() for x in options}) != 4:
            errors.append(prefix + '存在相同选项')
        ans = q.get('answer')
        if not isinstance(ans, str) or ans not in ['A', 'B', 'C', 'D']:
            errors.append(prefix + '答案须为A/B/C/D之一'); letters.append('?')
        else:
            answers[ans] += 1; letters.append(ans)
            if valid_options:
                lengths = [len(x.strip()) for x in options]
                if lengths.count(max(lengths)) == 1:
                    longest_count += 1
                    longest_correct += lengths['ABCD'.index(ans)] == max(lengths)
        stem = q.get('stem')
        if isinstance(stem, str) and valid_options:
            signature = (''.join(stem.split()), tuple(''.join(x.split()) for x in options))
            if signature in seen:
                errors.append(prefix + f'与题{seen[signature]}题干选项完全重复')
            seen[signature] = position
    for label, actual, expected in [('模块', actual_mod, mods), ('难度', actual_diff, diffs), ('二级题型', actual_sec, expected_secondary), ('材料组', actual_group, groups)]:
        if dict(actual) != {k: v for k, v in expected.items() if v}:
            errors.append(label + '实际配额与蓝图不一致')
    expected_order = [mod for mod, n in mods.items() for _ in range(n)]
    if ordered != expected_order:
        errors.append('模块题目顺序与蓝图不一致')
    run = maximum = 0; previous = None
    for ans in letters:
        run = run + 1 if ans == previous and ans != '?' else 1
        maximum = max(maximum, run); previous = ans
    if maximum >= 4:
        errors.append('存在连续四个及以上相同答案')
    if total >= 20 and any(answers[x] / total < .15 or answers[x] / total > .35 for x in 'ABCD'):
        warnings.append('答案位置分布偏斜，需人工审查；勿强行改答案')
    if longest_count >= 10 and longest_correct / longest_count > .6:
        warnings.append('唯一最长项正确率偏高，需审查选项提示性')
    if materials is None and groups:
        warnings.append('未读取materials文件，材料内容完整性未验证')
    elif materials is not None:
        if not isinstance(materials, dict) or set(materials) != set(groups):
            errors.append('材料文件组ID与蓝图不一致')
        elif any(not value for value in materials.values()):
            errors.append('材料文件包含空材料')
    return {'errors': errors, 'warnings': warnings, 'question_count': len(questions),
            'answers': dict(answers), 'max_answer_run': maximum,
            'unique_longest_correct': longest_correct, 'unique_longest_total': longest_count,
            'semantic_correctness': '未由本脚本验证'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('questions'); parser.add_argument('blueprint')
    parser.add_argument('--materials'); parser.add_argument('--out')
    args = parser.parse_args()
    try:
        read = lambda path: json.loads(pathlib.Path(path).read_text(encoding='utf-8'))
        result = validate(read(args.questions), read(args.blueprint), read(args.materials) if args.materials else None)
    except (OSError, ValueError) as exc:
        print('读取失败: ' + str(exc), file=sys.stderr); return 2
    encoded = json.dumps(result, ensure_ascii=False, indent=2)
    if args.out:
        pathlib.Path(args.out).write_text(encoded + '\n', encoding='utf-8')
    print(encoded)
    return 1 if result['errors'] else 0


if __name__ == '__main__':
    sys.exit(main())
