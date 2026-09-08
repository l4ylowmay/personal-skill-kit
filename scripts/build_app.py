#!/usr/bin/env python3
"""Build a portable, self-contained exam after evidence checks."""
import argparse
import datetime
import html
import json
import pathlib
import re
import xml.etree.ElementTree as ET
from quality_gate import check, digest

ROOT = pathlib.Path(__file__).resolve().parents[1]


def validate_svg(source):
    if not isinstance(source, str) or '<!DOCTYPE' in source.upper() or '<!ENTITY' in source.upper():
        raise ValueError('SVG必须为无DTD的内嵌文本')
    element = ET.fromstring(source)
    allowed = {'svg', 'g', 'path', 'rect', 'circle', 'ellipse', 'line', 'polyline', 'polygon', 'text', 'tspan', 'title', 'desc', 'defs', 'clipPath', 'mask', 'linearGradient', 'radialGradient', 'stop', 'use', 'symbol', 'marker'}
    if element.tag.split('}')[-1] != 'svg' or 'viewBox' not in element.attrib:
        raise ValueError('SVG须有viewBox')
    for node in element.iter():
        if node.tag.split('}')[-1] not in allowed:
            raise ValueError('不允许的SVG元素')
        for key, value in node.attrib.items():
            key = key.split('}')[-1].lower()
            if key.startswith('on') or key in {'style', 'src'}:
                raise ValueError('SVG不允许脚本、内联CSS或外部资源')
            if key == 'href' and not value.startswith('#'):
                raise ValueError('SVG引用须为片段ID')
            if re.search(r'url\s*\(', value, re.I) and not re.fullmatch(r'url\(#[A-Za-z0-9_-]+\)', value):
                raise ValueError('SVG不允许远程或可执行URL')
    return source


def render(qs, materials, bp, fact_cutoff):
    for q in qs:
        if q.get('graphic'):
            graphic = q['graphic']; validate_svg(graphic['svg'])
            if 'choices_svg' in graphic:
                if len(graphic['choices_svg']) != 4: raise ValueError('图形必须有四个候选')
                for value in graphic['choices_svg']: validate_svg(value)
        for source in q.get('sources', []):
            if not re.match(r'^https?://', source['url']): raise ValueError('来源链接须为HTTP(S)')
    for key, m in materials.items():
        if not re.fullmatch(r'[A-Za-z][A-Za-z0-9_-]*', key): raise ValueError('材料ID格式不安全')
        if m.get('kind') not in {'text', 'chart', 'table'}: raise ValueError('未知材料类型')
        if '模拟数据' not in m.get('note', ''): raise ValueError('资料须注明模拟数据')
        if not m.get('title'): raise ValueError('材料须有标题')
        if m['kind'] == 'chart': validate_svg(m['svg'])
        if m['kind'] in {'chart', 'table'}:
            if not m.get('headers') or not m.get('rows') or any(len(row) != len(m['headers']) for row in m['rows']):
                raise ValueError('表格或图中同值数据表必须完整')
    count, minutes = len(qs), bp.get('minutes', 90)
    if type(minutes) is not int or minutes <= 0: raise ValueError('分钟数须为正整数')
    data = {'version': digest({'questions': qs, 'materials': materials, 'blueprint': bp})[:20],
            'minutes': minutes, 'fact_cutoff': fact_cutoff, 'modules': list(bp['modules']), 'questions': qs, 'materials': materials}
    assets = ROOT / 'assets' / 'app'
    modules = ''.join('<div><span class="index">' + str(i + 1).zfill(2) + '</span><strong>' + html.escape(name) + '</strong><small>' + str(n) + '题</small></div>' for i, (name, n) in enumerate(bp['modules'].items()))
    replacements = {'STYLE': (assets / 'style.css').read_text(encoding='utf-8'), 'SCRIPT': (assets / 'app.js').read_text(encoding='utf-8'),
                    'DATA': json.dumps(data, ensure_ascii=False).replace('<', '\\u003c'), 'MODULES': modules,
                    'MINUTES': str(minutes), 'TOTAL': str(count), 'POINTS': format(100 / count, '.4g'),
                    'FACT_CUTOFF': html.escape(fact_cutoff), 'BASIS_LABEL': html.escape(bp.get('basis_label', '依据随包深圳行测命题基准原创编写。')),
                    'PROFILE_NOTE': html.escape(bp.get('profile_note', '本卷采用历史主流结构仿真，不代表最新官方考试大纲。'))}
    template = (assets / 'template.html').read_text(encoding='utf-8')
    return re.sub(r'__([A-Z_]+)__', lambda match: replacements[match[1]], template)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ['questions', 'materials', 'blueprint', 'review', 'out']: parser.add_argument('--' + key, required=True)
    parser.add_argument('--fact-cutoff', default=datetime.date.today().isoformat())
    args = parser.parse_args()
    read = lambda x: json.loads(pathlib.Path(x).read_text(encoding='utf-8'))
    q, m, b, r = [read(x) for x in [args.questions, args.materials, args.blueprint, args.review]]
    result = check(q, b, r, m, pathlib.Path(args.review).parent)
    if result['errors']:
        print(json.dumps(result, ensure_ascii=False, indent=2)); return 1
    content = render(q, m, b, args.fact_cutoff)
    target = pathlib.Path(args.out); target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding='utf-8')
    print(json.dumps({'file': str(target), 'question_count': len(q), 'warnings': result['warnings'],
                      'next_step': '必须对生成HTML做实际浏览器与视觉验收'}, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
