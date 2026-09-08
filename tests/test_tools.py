"""Run with Python 3.10+; fixtures test tools, not exam quality."""
import copy
import importlib.util
import json
import pathlib
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from validate_bank import validate
from quality_gate import check, digest
from build_app import render, validate_svg


def fixture():
    qs = [{'number': i, 'module': '测试', 'secondary_type': '格式测试', 'core_concept': '仅用于工具测试', 'difficulty': '易',
           'stem': f'工具测试题{i}：这里不作为可交付的学科题目。', 'options': ['甲', '乙', '丙', '丁'], 'answer': 'ABCD'[i - 1],
           'explanation': '测试展示与状态机，不认证学科正确性。', 'basis_ref': 'fixture', 'calculation_steps': 0, 'reasoning_steps': 0} for i in range(1, 5)]
    bp = {'total': 4, 'minutes': 90, 'modules': {'测试': 4}, 'difficulty': {'易': 4}, 'secondary': {'测试': {'格式测试': 4}}, 'materials': {}}
    review = {'bank_sha256': digest({'questions': qs, 'materials': {}}), 'blueprint_sha256': digest(bp), 'unresolved': [], 'method': '测试夹具，不是真题复核', 'records': []}
    for q in qs:
        review['records'].append({'number': q['number'], 'question_sha256': digest(q), 'blind_answer': q['answer'], 'reasoning': '测试证据字段',
                                  'wrong_option_reasons': {x: '测试错项理由' for x in 'ABCD' if x != q['answer']}, 'unique_best_answer': True,
                                  'source_fit': '测试基准', 'originality': '测试夹具', 'difficulty_reason': '测试难度字段'})
    return qs, bp, review


class ToolTests(unittest.TestCase):
    def setUp(self):
        self.q, self.b, self.r = fixture()

    def gate(self):
        return check(self.q, self.b, self.r, {}, ROOT)

    def test_valid_structure(self): self.assertEqual(validate(self.q, self.b)['errors'], [])
    def test_valid_evidence(self): self.assertEqual(self.gate()['errors'], [])
    def test_missing_option(self):
        self.q[0]['options'].pop(); self.assertTrue(validate(self.q, self.b)['errors'])
    def test_invalid_answer(self):
        self.q[0]['answer'] = 'E'; self.assertTrue(validate(self.q, self.b)['errors'])
    def test_duplicate_number(self):
        self.q[1]['number'] = 1; self.assertTrue(validate(self.q, self.b)['errors'])
    def test_wrong_quota(self):
        self.q[0]['difficulty'] = '难'; self.assertTrue(validate(self.q, self.b)['errors'])
    def test_run_four(self):
        for q in self.q: q['answer'] = 'A'
        self.assertTrue(validate(self.q, self.b)['errors'])
    def test_stale_review(self):
        self.q[0]['stem'] += '修改'; self.assertTrue(self.gate()['errors'])
    def test_missing_review(self):
        self.r['records'].pop(); self.assertTrue(self.gate()['errors'])
    def test_disagreeing_answer(self):
        self.r['records'][0]['blind_answer'] = 'D'; self.assertTrue(self.gate()['errors'])
    def test_missing_wrong_option_reason(self):
        self.r['records'][0]['wrong_option_reasons'].pop('D'); self.assertTrue(self.gate()['errors'])
    def test_missing_calculation_proof(self):
        self.q[0]['calculation_steps'] = 1; self.assertTrue(self.gate()['errors'])
    def test_missing_artifact(self):
        self.r['artifacts'] = {'proof': {'path': 'does-not-exist.py', 'sha256': 'bad', 'executed_at': 'test'}}
        self.assertTrue(self.gate()['errors'])
    def test_unresolved_issue(self):
        self.r['unresolved'] = ['双解']; self.assertTrue(self.gate()['errors'])
    def test_blueprint_consistency(self):
        b = json.loads((ROOT / 'standards/blueprint.json').read_text(encoding='utf-8'))
        self.assertEqual(sum(b['modules'].values()), 100)
        self.assertEqual([s['number'] for s in b['slots']], list(range(1, 101)))
        q = []
        for s in b['slots']:
            q.append(dict(s, stem=f"一致性测试{s['number']}", options=['甲', '乙', '丙', '丁'], answer='ABCD'[(s['number'] - 1) % 4], explanation='仅检验蓝图一致性'))
        self.assertEqual(validate(q, b)['errors'], [])
        self.assertEqual(len(json.loads((ROOT / 'standards/templates.json').read_text(encoding='utf-8'))), 19)
    def test_script_injection_escaped(self):
        self.q[0]['stem'] = '</script><script>alert(1)</script>'
        page = render(self.q, {}, self.b, '测试日期')
        self.assertNotIn(self.q[0]['stem'], page)
        self.assertIn('\\u003c/script>', page)
    def test_svg_safe(self): validate_svg('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10"><circle cx="5" cy="5" r="2"/></svg>')
    def test_svg_script_rejected(self):
        with self.assertRaises(ValueError): validate_svg('<svg viewBox="0 0 10 10"><script>alert(1)</script></svg>')
    def test_svg_external_rejected(self):
        with self.assertRaises(ValueError): validate_svg('<svg viewBox="0 0 10 10"><use href="https://example.org/image.svg"/></svg>')
    def test_render_no_placeholders(self):
        page = render(self.q, {}, self.b, '测试日期')
        self.assertNotIn('__DATA__', page)
        self.assertNotIn('/Users/', page)
        self.assertNotIn('2026-09-08', page)
    def test_material_missing(self):
        self.q[0]['material_group'] = 'MISSING'; self.assertTrue(validate(self.q, self.b, {})['errors'])


if __name__ == '__main__':
    unittest.main()
