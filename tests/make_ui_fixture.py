"""Create obviously artificial UI stress data; never use as an exam bank."""
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from build_app import render


def make(target):
    bp = json.loads((ROOT / 'standards/blueprint.json').read_text(encoding='utf-8'))
    bp['basis_label'] = '仅用于界面自动化测试，不是可作答模拟卷。'
    qs = []
    image = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 600 160" role="img" aria-label="测试几何图"><rect x="10" y="10" width="580" height="140" fill="none" stroke="black"/><circle cx="100" cy="80" r="40" fill="none" stroke="black"/><text x="200" y="90" font-size="24">测试图形 / 标签可读</text></svg>'
    for s in bp['slots']:
        q = dict(s, stem=f"第{s['number']}题是界面测试占位，不构成学科试题。" + '这是用于检测长文字换行、题号定位和题下解析的测试段落。' * 6,
                 options=['选项甲：测试文本', '选项乙：用于检查换行的较长文字' * 4, '选项丙：测试文本', '选项丁：测试文本'], answer='ABCD'[(s['number'] - 1) % 4],
                 explanation='工具测试解析，不是学科解答。' * 15, sources=[])
        if 21 <= s['number'] <= 25:
            q['graphic'] = {'svg': image, 'choices_svg': [image.replace('测试图形', f'候选{x}') for x in 'ABCD']}
        qs.append(q)
    materials = {
        'M1': {'kind': 'text', 'title': '测试文字材料', 'note': '模拟数据，仅为UI测试', 'text': '这是一份用于测试资料排版的文字。' * 40},
        'M2': {'kind': 'chart', 'title': '测试图表', 'note': '模拟数据，仅为UI测试', 'svg': image, 'headers': ['年', '量甲', '量乙', '平均量'], 'rows': [[2020 + i, 170 + i, 60 + i, 22.5] for i in range(6)]},
        'M3': {'kind': 'table', 'title': '测试宽表', 'note': '模拟数据，仅为UI测试', 'headers': ['主体', '2024数量', '2025数量', '2024金额', '2025金额', '2024能耗', '2025能耗'], 'rows': [[f'主体{i}', 1765.4, 1987.3, 6547.6, 6766.4, 564.7, 643.9] for i in range(8)]}
    }
    pathlib.Path(target).parent.mkdir(parents=True, exist_ok=True)
    pathlib.Path(target).write_text(render(qs, materials, bp, '测试日期'), encoding='utf-8')


if __name__ == '__main__':
    make(sys.argv[1])
