import unittest
from unittest.mock import patch
from urllib.error import HTTPError

from lowalt_newsroom.social import capture, import_feed, inspect_html, probe
from lowalt_newsroom.planning import supplementary_steps


class SocialTests(unittest.TestCase):
    def record(self, **changes):
        return dict(platform="x", source_id="S1", route="browser_visible", sampling_method="selected_permalink",
                    captured_at="2026-10-19T19:00:00+08:00", url="https://x.com/example/status/123",
                    body="公开正文", **changes)

    def test_cannot_import_fact_verification_or_invent_year(self):
        result = capture(self.record(published_at_raw="10-19 08:00", fact_verified=True))
        self.assertFalse(result["fact_verified"])
        self.assertIsNone(result["published_at_utc"])
        self.assertEqual(result["available_at"], result["captured_at"])
        self.assertEqual(result["review_status"], "waiting_review")

    def test_body_hash_preserves_version_and_unknown_extent(self):
        first = capture(self.record())
        data = self.record(); data["body"] += "更正"
        second = capture(data)
        self.assertNotEqual(first["body_sha256"], second["body_sha256"])
        self.assertEqual(first["document_id"], second["document_id"])
        self.assertEqual(first["body_extent"], "unknown")

    def test_http_200_shell_never_counts_as_body(self):
        for platform in ["x", "xiaohongshu", "wechat"]:
            result = inspect_html('<html>登录后查看<script>fake body</script></html>', platform)
            self.assertIsNone(result["body"])
            self.assertIn("登录", result["status"])

    def test_wechat_extracts_only_article_container(self):
        result = inspect_html('<div id="js_name">账号</div><div id="js_content"><p>正文<img src="a">段落</p><script>隐蔽</script><p>后文</p></div><footer>导航</footer>', "wechat")
        self.assertIn("后文", result["body"])
        self.assertNotIn("隐蔽", result["body"])
        self.assertNotIn("导航", result["body"])
        self.assertEqual(result["author"], "账号")

    def test_werss_content_and_description_are_distinct(self):
        xml = b'<rss xmlns:content="http://purl.org/rss/1.0/modules/content/"><channel><item><title>A</title><link>https://mp.weixin.qq.com/s/a</link><description>Summary</description></item><item><link>https://mp.weixin.qq.com/s/b</link><content:encoded><![CDATA[<p>Body</p>]]></content:encoded></item></channel></rss>'
        rows = import_feed(xml, "wechat", "S1", "2026-10-19T00:00:00Z")
        self.assertIsNone(rows[0]["document"])
        self.assertEqual(rows[1]["document"]["body"], "Body")
        self.assertFalse(rows[1]["document"]["fact_verified"])
        self.assertEqual(rows[1]["document"]["body_extent"], "unknown")

    def test_http_restriction_stays_failure(self):
        with patch("lowalt_newsroom.social.urlopen", side_effect=HTTPError("https://x.com", 403, "Forbidden", {}, None)):
            result = probe("https://x.com", "x", "S1")
        self.assertEqual(result["http_status"], 403)
        self.assertIsNone(result["document"])
        self.assertEqual(result["status"], "访问受限")

    def test_reject_missing_capture_time_and_empty_body(self):
        for changes in [{"captured_at":"2026-10-19"}, {"body":""}]:
            row=self.record(); row.update(changes)
            with self.assertRaises(ValueError): capture(row)

    def test_source_instructions_not_queries(self):
        for line in ["只查编制方案及名单", "读取文章识别账号", "Crossref/OpenAlex/arXiv发现后读原文", "按监管、企业、运行拆分", "按官方列表追详情"]:
            self.assertEqual(supplementary_steps(line)[0]["kind"], "instruction")
