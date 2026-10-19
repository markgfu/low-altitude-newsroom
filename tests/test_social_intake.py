import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest

from lowalt_newsroom.cli import main
from lowalt_newsroom.social import import_intake


class IntakeTests(unittest.TestCase):
    def record(self, **changes):
        row = dict(schema_version="social-capture-v1", platform="xiaohongshu",
                   source_url="https://www.xiaohongshu.com/explore/0123456789abcdef01234567",
                   capture_method="browser_visible", observed_at="2026-10-19T22:29:00+08:00",
                   text="测试材料：讨论算力的融资与交付。", body_complete=None,
                   evidence={"body": "synthetic unit-test fixture"}, simulation=True,
                   published={"display": "10-19", "at": None, "date": None,
                              "precision": "unknown", "kind": "unknown"},
                   interactions={"like_count": {"display": "1.2万", "value": None},
                                 "collect_count": {"display": "12", "value": 12}})
        row.update(changes)
        return row

    def ingest(self, row, policy=None):
        return import_intake(json.dumps(row).encode(), "SOC-TEST", policy)

    def test_dates_counters_and_no_automatic_promotion(self):
        doc = self.ingest(self.record())["documents"][0]
        self.assertIsNone(doc["published_at_utc"])
        self.assertEqual(doc["published"]["display"], "10-19")
        self.assertIsNone(doc["interactions"]["like_count"]["value"])
        self.assertEqual(doc["interactions"]["collect_count"]["value"], 12)
        self.assertEqual(doc["heat"]["status"], "unconfigured")
        for key in ("fact_verified", "metric_eligible", "quote_eligible", "daily_eligible"):
            self.assertFalse(doc[key])
        self.assertTrue(doc["simulation"])

    def test_current_version_is_not_first_publication(self):
        stamp = {"display": "2026-10-19 22:00", "at": "2026-10-19T22:00:00+08:00",
                 "precision": "minute", "kind": "current_version", "basis": "test"}
        self.assertIsNone(self.ingest(self.record(published=stamp))["documents"][0]["published_at_utc"])
        stamp["kind"] = "published"
        self.assertIsNotNone(self.ingest(self.record(published=stamp))["documents"][0]["published_at_utc"])

    def test_reject_secret_hash_and_approximate_exact_count(self):
        bad = [self.record(text_sha256="wrong"),
               self.record(interactions={"like_count": {"display": "1.2万", "value": 12000}}),
               self.record(source_url=self.record()["source_url"] + "?xsec_token=private-test"),
               self.record(evidence={"body": "test", "cookies": "private-test"})]
        for row in bad:
            with self.assertRaises(ValueError) as error:
                self.ingest(row)
            self.assertNotIn("private-test", str(error.exception))

    def test_tags_and_heat_remain_separate_from_valid_discussion(self):
        doc = self.ingest(self.record(text="#算力金融 #算力"),
                          {"platforms": {"xiaohongshu": {"collect_count": 10}}})["documents"][0]
        self.assertEqual(doc["heat"]["status"], "pass")
        self.assertEqual(doc["content_review"], "missing_independent_discussion")
        self.assertFalse(doc["daily_eligible"])
        emoji = self.ingest(self.record(text="🚀🚀 #低空经济"))["documents"][0]
        self.assertEqual(emoji["content_review"], "missing_independent_discussion")

    def test_browser_observation_preserves_provenance_and_collection(self):
        row = dict(schema_version="social-browser-observation-v1", platform="xiaohongshu",
                   page_status="captured", source_url=self.record()["source_url"],
                   body="仅供单元测试的正文", observed_at=self.record()["observed_at"],
                   engagement={"bookmarks": 12}, engagement_raw={"bookmarks": "12"},
                   publication_raw="昨天", edited_raw="编辑于 10-19", simulation=True,
                   observed_interval={"start": "2026-10-19T22:28:00+08:00", "end": "2026-10-19T22:29:00+08:00"},
                   actual_dom_observed_at=None, gaps=["图片未读"])
        doc = self.ingest(row)["documents"][0]
        self.assertEqual(doc["observed_interval"], row["observed_interval"])
        self.assertIsNone(doc["actual_dom_observed_at"])
        self.assertEqual(doc["edited"]["kind"], "edited")
        self.assertEqual(doc["interactions"]["collect_count"]["value"], 12)
        self.assertIn("图片未读", doc["gaps"])

    def test_empty_failed_pack_is_not_success(self):
        row = dict(schema_version="social-intake-batch-v1", records=[],
                   status="browser_unavailable", coverage_complete=False,
                   candidates=[{"title": "仅卡片"}], failures=[{"reason": "timeout"}])
        result = self.ingest(row)
        self.assertEqual(result["documents"], [])
        self.assertFalse(result["accepted"])
        self.assertFalse(result["source_coverage_complete"])
        self.assertEqual(result["failures"], row["failures"])
        self.assertEqual(result["candidates"], row["candidates"])

    def test_cli_archive_cannot_be_overwritten(self):
        Path("runtime").mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir="runtime") as directory:
            source, target = Path(directory) / "input.json", Path(directory) / "archive.json"
            source.write_text(json.dumps(self.record()), encoding="utf-8")
            args = ["social", "intake", "--source-id", "SOC-TEST", "--input", str(source), "--output", str(target)]
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(main(args), 0)
                before = target.read_bytes()
                self.assertNotEqual(main(args), 0)
                self.assertEqual(target.read_bytes(), before)
