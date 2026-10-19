from datetime import date
from pathlib import Path
import base64
import tempfile
import unittest
from unittest.mock import patch
from urllib.error import HTTPError

from lowalt_newsroom.feeds import fetch_feed, parse_feed, publication_time
from lowalt_newsroom.planning import build_plan, is_due, record_search, supplementary_steps
from lowalt_newsroom.rendering import check_draft, inline, render_markdown
from lowalt_newsroom.workbooks import table_records

ROOT = Path(__file__).resolve().parents[1]


class PlanningTests(unittest.TestCase):
    def test_weekday_is_iso_not_sunday_zero(self):
        monday = date(2026, 10, 19)
        self.assertTrue(is_due('每周1', monday))
        self.assertFalse(is_due('每周7', monday))
        self.assertFalse(is_due('线索触发', monday))
        with self.assertRaises(ValueError):
            is_due('每周八', monday)

    def test_instructions_are_not_queries_and_literal_newlines_split(self):
        steps = supplementary_steps('上海 无人机\\n查数据库和期刊原站\n按原站目录追正文')
        self.assertEqual([x['kind'] for x in steps], ['query_or_entry', 'instruction', 'instruction'])

    def test_snapshot_reads_all_rows_outside_old_excel_filter(self):
        sources = table_records(ROOT / 'data/source_registry.xlsx', '信源清单', 'ID')
        tasks = table_records(ROOT / 'data/search_checklist.xlsx', '检索任务', '任务ID')
        self.assertEqual(len(sources), 117)
        self.assertEqual(len(tasks), 240)
        self.assertIn('EC12', {x['任务ID'] for x in tasks})

    def test_plan_is_not_execution(self):
        plan = build_plan(ROOT / 'data/search_checklist.xlsx', date(2026, 10, 19), 'unit')
        self.assertEqual(sum(x['due'] for x in plan['tasks']), 187)
        self.assertTrue(all(x['searches'] == [] and x['findings'] is None for x in plan['tasks']))
        self.assertTrue(all(x['status'] == '未执行' for x in plan['tasks'] if x['due']))

    def test_new_finding_requires_read_original(self):
        p = {'tasks': [{'task_id': 'T1', 'due': True, 'searches': []}]}
        with self.assertRaises(ValueError):
            record_search(p, 'T1', '上海 低空', ['https://example.org/'], '已检有新增', [], None, 'only search')

    def test_gap_record_keeps_unknown_count_and_query_time(self):
        p = {'tasks': [{'task_id': 'T1', 'due': True, 'searches': []}]}
        record_search(p, 'T1', '上海 低空', ['https://example.org/'], '已发现待核', [], None, '正文未读')
        task = p['tasks'][0]
        self.assertIsNone(task['findings'])
        self.assertIsNone(task['originals_read'])
        self.assertIn('+00:00', task['searches'][0]['time_utc'])
        with self.assertRaises(ValueError):
            record_search(p, 'T1', '按原站目录追正文', ['https://example.org/'], '未执行', [], None, '')


class FeedTests(unittest.TestCase):
    def test_http_failure_retains_status_without_claiming_read(self):
        with patch('lowalt_newsroom.feeds.urlopen', side_effect=HTTPError('https://example.org/feed', 403, 'Forbidden', {}, None)):
            result = fetch_feed('https://example.org/feed')
        self.assertEqual(result['http_status'], 403)
        self.assertEqual(result['status'], '读取失败')
        self.assertEqual(result['items'], [])

    def test_rss_is_a_lead_not_read_full_text(self):
        items = parse_feed(b'<rss version="2.0"><channel><item><title>Demo</title><link>https://example.org/a</link><pubDate>Mon, 19 Oct 2026 08:00:00 +0800</pubDate></item></channel></rss>')
        self.assertEqual(items[0]['publication_utc'], '2026-10-19T00:00:00+00:00')
        self.assertFalse(items[0]['full_text_read'])

    def test_atom_update_is_not_publication(self):
        data = b'<feed xmlns="http://www.w3.org/2005/Atom"><entry><title>Demo</title><link href="https://example.org/a"/><updated>2026-10-19T08:00:00Z</updated></entry></feed>'
        row = parse_feed(data)[0]
        self.assertIsNone(row['publication_utc'])
        self.assertEqual(row['updated_raw'], '2026-10-19T08:00:00Z')

    def test_naive_or_unknown_date_stays_unknown(self):
        self.assertIsNone(publication_time('2026-10-19T08:00:00'))
        self.assertIsNone(publication_time('无法识别'))
        self.assertEqual(parse_feed(b'<rss><channel/></rss>'), [])

    def test_html_or_entities_not_claimed_as_feed(self):
        for data in [b'<html><body>login</body></html>', b'<!DOCTYPE rss><rss/>']:
            with self.assertRaises(ValueError):
                parse_feed(data)


class RenderingTests(unittest.TestCase):
    def test_native_bold_and_escaped_html(self):
        self.assertEqual(inline('**今日总结**：<script>'), '<strong>今日总结</strong>：&lt;script&gt;')
        with self.assertRaises(ValueError):
            inline('[unsafe](javascript:alert)')

    def test_images_are_embedded_and_outside_paths_rejected(self):
        temporary_root = ROOT / 'runtime' / 'test-temp'
        temporary_root.mkdir(parents=True, exist_ok=True)
        # Windows沙箱的系统临时目录可能不可写；临时文件始终限制在仓库内。
        with tempfile.TemporaryDirectory(dir=temporary_root) as temp:
            folder = Path(temp)
            self.assertTrue(folder.resolve().is_relative_to(temporary_root.resolve()))
            (folder / 'figure.png').write_bytes(b'\x89PNG\r\n\x1a\nexample')
            (folder / 'daily.md').write_text('# 标题\n\n**今日总结**：示例\n\n![图](figure.png)', encoding='utf-8')
            output = render_markdown(folder / 'daily.md')
            self.assertIn('data:image/png;base64,' + base64.b64encode(b'\x89PNG\r\n\x1a\nexample').decode(), output)
            (folder / 'daily.md').write_text('![图](../secret.png)', encoding='utf-8')
            with self.assertRaises(ValueError):
                render_markdown(folder / 'daily.md')

    def test_internal_metadata_rejected(self):
        result = check_draft('# 标题\n\n**今日总结**：说明\n\nsource_level: A')
        self.assertTrue(result['errors'])

    def test_real_six_article_draft_and_one_embedded_figure(self):
        source = ROOT / 'examples/2026-10-19/daily.md'
        result = check_draft(source.read_text(encoding='utf-8'))
        self.assertEqual(result['articles'], 6)
        self.assertEqual(result['errors'], [])
        rendered = render_markdown(source)
        self.assertEqual(rendered.count('data:image/png;base64,'), 1)
        self.assertIn('<strong>今日总结</strong>：', rendered)


if __name__ == '__main__':
    unittest.main()
