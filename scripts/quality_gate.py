#!/usr/bin/env python3
"""Check coverage and integrity of review evidence, not its semantic truth."""
import argparse
import hashlib
import json
import pathlib
from validate_bank import validate


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def chars(value):
    return len(''.join(str(value).split()))


def check(qs, bp, review, materials, base):
    result = validate(qs, bp, materials)
    errors, warnings = result['errors'], result['warnings']
    if errors:
        return result
    if not isinstance(review, dict):
        errors.append('review必须为对象'); return result
    for key, actual in [('bank_sha256', digest({'questions': qs, 'materials': materials})), ('blueprint_sha256', digest(bp))]:
        if review.get(key) != actual:
            errors.append(key + '不匹配，题库或基准改动后必须重新复核')
    if review.get('unresolved') != []:
        errors.append('未明确记录零未解决问题')
    if not review.get('method'):
        errors.append('缺少独立复核方法说明')
    records = review.get('records', [])
    if not isinstance(records, list) or len(records) != len(qs):
        errors.append('复核记录未覆盖全部题目'); return result
    by_number = {}
    for record in records:
        if not isinstance(record, dict) or type(record.get('number')) is not int:
            errors.append('复核记录题号无效'); continue
        if record['number'] in by_number:
            errors.append('复核记录题号重复')
        by_number[record['number']] = record
    artifacts = review.get('artifacts', {})
    if not isinstance(artifacts, dict):
        artifacts = {}; errors.append('artifacts必须为对象')
    for key, artifact in artifacts.items():
        try:
            relative = pathlib.Path(artifact['path'])
            path = (base / relative).resolve()
            if relative.is_absolute() or not path.is_relative_to(base.resolve()):
                raise ValueError('校验底稿路径必须位于review所在目录内')
            if hashlib.sha256(path.read_bytes()).hexdigest() != artifact['sha256']:
                raise ValueError('文件哈希不匹配')
            if not artifact.get('executed_at'):
                raise ValueError('未记录执行时间')
        except (KeyError, OSError, ValueError, TypeError) as exc:
            errors.append(f'底稿{key}: {exc}')
    slots = {s['number']: s for s in bp.get('slots', [])}
    raw_grades = {}; total_reading = 0
    for q in qs:
        n = q['number']; prefix = f'题{n}: '; r = by_number.get(n, {})
        if r.get('question_sha256') != digest(q):
            errors.append(prefix + '复核题目哈希缺失或过期')
        if r.get('blind_answer') != q['answer']:
            errors.append(prefix + '独立答案不一致')
        for field in ['reasoning', 'source_fit', 'originality', 'difficulty_reason']:
            if not isinstance(r.get(field), str) or not r[field].strip():
                errors.append(prefix + '缺少复核证据 ' + field)
        wrong = r.get('wrong_option_reasons', {})
        if not isinstance(wrong, dict) or set(wrong) != set('ABCD') - {q['answer']} or not all(isinstance(v, str) and v.strip() for v in wrong.values()):
            errors.append(prefix + '须逐一说明三个错误项为什么不成立')
        if r.get('unique_best_answer') is not True:
            errors.append(prefix + '唯一最佳答案检查未通过')
        if not q.get('basis_ref'):
            errors.append(prefix + '缺少命题标准索引')
        slot = slots.get(n)
        if slot:
            for field in ['module', 'secondary_type', 'difficulty', 'material_group']:
                if q.get(field) != slot.get(field):
                    errors.append(prefix + '题位字段不匹配 ' + field)
            lo, hi = slot['stem_length_target']
            if not lo <= chars(q['stem']) <= hi and not r.get('length_deviation_reason'):
                errors.append(prefix + '题干长度超出题位范围且未解释')
        calc, reasoning = q.get('calculation_steps'), q.get('reasoning_steps')
        if any(type(v) is not int or v < 0 for v in [calc, reasoning]):
            errors.append(prefix + '须标注实际计算/推理宏步骤'); continue
        if slot:
            lo, hi = slot['calculation_steps_target']
            if not lo <= calc <= hi and not r.get('calculation_deviation_reason'):
                errors.append(prefix + '实际计算强度与题位不同，缺少理由')
        length = chars(q['stem']) + sum(chars(x) for x in q['options']); total_reading += length
        raw = (0 if length < 180 else 1 if length < 350 else 2) + (0 if reasoning <= 1 else 1 if reasoning <= 3 else 2) + (0 if calc == 0 else 1 if calc <= 2 else 2)
        raw += int(bool(q.get('specialist_knowledge'))) + int(bool(q.get('strong_interference'))) + (2 if q.get('graphic') and q['module'] == '判断推理' else 0)
        grade = '易' if raw <= 1 else '中' if raw <= 4 else '难'
        raw_grades[n] = {'score': raw, 'difficulty': grade}
        if grade != q['difficulty'] and not r.get('difficulty_calibration_reason'):
            errors.append(prefix + '原始评分与目标不同，须有独立校准理由')
        if calc or q['module'] in ['数量关系', '资料分析']:
            proof = r.get('calculation_artifact')
            if proof not in artifacts:
                errors.append(prefix + '缺少独立计算底稿引用')
        if q.get('graphic') and not r.get('graphic_visual_review'):
            errors.append(prefix + '未记录原图及选项的实际渲染复核')
        if q['module'] == '公共基础知识':
            fact = r.get('fact_check')
            if not isinstance(fact, dict) or not fact.get('reason'):
                errors.append(prefix + '缺少知识依据检查')
            elif fact.get('mode') == 'verified':
                if not q.get('sources') or not fact.get('verified_at'):
                    errors.append(prefix + '事实核验无来源或日期')
            elif fact.get('mode') != 'conceptual':
                errors.append(prefix + '知识依据状态无效')
    for m in materials.values():
        total_reading += chars(m.get('text', '')) + sum(chars(x) for x in m.get('headers', [])) + sum(chars(x) for row in m.get('rows', []) for x in row)
    deviations = review.get('deviations', {})
    if not isinstance(deviations, dict):
        deviations = {}; errors.append('deviations须为对象')
    target = bp.get('total_reading_target')
    if target and not target[0] <= total_reading <= target[1]:
        if not deviations.get('total_reading'):
            errors.append('整卷阅读量偏离目标且无实际差值解释')
        warnings.append('整卷阅读量偏离目标，须人工确认解释充分')
    for field, predicate in [('local_knowledge_count', lambda q: q.get('requires_local_knowledge') is True), ('current_affairs_count', lambda q: q['secondary_type'] == '时政')]:
        if field in bp and sum(predicate(q) for q in qs) != bp[field]:
            errors.append(field + '不符合基准')
    for spec in bp.get('material_specs', []):
        m = materials[spec['id']]
        if spec.get('characters'):
            lo, hi = spec['characters']
            if not lo <= chars(m.get('text', '')) <= hi:
                errors.append(spec['id'] + '文字材料长度不合格')
        if spec.get('rows') and len(m.get('rows', [])) != spec['rows']:
            errors.append(spec['id'] + '资料表主体行数不合格')
        if spec.get('numeric_columns') and any(len(row) - 1 != spec['numeric_columns'] for row in m.get('rows', [])):
            errors.append(spec['id'] + '资料表列数不合格')
        if spec.get('periods') and len(m.get('rows', [])) != spec['periods']:
            errors.append(spec['id'] + '统计图数据年份数不合格')
        if spec.get('indicators') and len(m.get('headers', [])) - 1 != spec['indicators']:
            errors.append(spec['id'] + '统计图数据指标数不合格')
    result.update({'raw_difficulty': raw_grades, 'reading_characters': total_reading,
                   'evidence_coverage': len(by_number), 'semantic_correctness': '本工具检查证据结构与完整性，不证明证据内容真实或答案正确'})
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for arg in ['questions', 'blueprint', 'review']: p.add_argument(arg)
    p.add_argument('--materials', required=True); p.add_argument('--out')
    args = p.parse_args()
    read = lambda x: json.loads(pathlib.Path(x).read_text(encoding='utf-8'))
    result = check(read(args.questions), read(args.blueprint), read(args.review), read(args.materials), pathlib.Path(args.review).parent)
    output = json.dumps(result, ensure_ascii=False, indent=2)
    if args.out: pathlib.Path(args.out).write_text(output, encoding='utf-8')
    print(output)
    return int(bool(result['errors']))


if __name__ == '__main__':
    raise SystemExit(main())
