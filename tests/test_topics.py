from pathlib import Path
import tempfile
import unittest

from lowalt_newsroom.cli import main
from lowalt_newsroom.planning import record_search
from lowalt_newsroom.topic_cli import import_lowalt
from lowalt_newsroom.topics import TopicStore, blank_config, read_json, validate, write_json

ROOT = Path(__file__).resolve().parents[1]
URL = "https://example.org/original"


def fixture(slug="test"):
    config = blank_config(slug, "测试主题", "仅供单元测试的新闻")
    config["sources"] = [{"id": "S1", "name": "测试来源", "type": "official", "entry": "https://example.org/", "method": "原站", "status": "candidate"}]
    config["keywords"] = [{"id": "K1", "terms": ["算力", "智算中心"]}]
    config["tasks"] = [{"id": "T1", "keyword_ids": ["K1"], "source_ids": ["S1"], "queries": ["{term} 融资"], "frequency": "每日", "enabled": True, "verification": "核对原文、日期和融资状态"}]
    return config


def complete(path, original=URL):
    plan = read_json(path)
    for task in plan["tasks"]:
        if task["due"]:
            for query in task["queries"]:
                record_search(plan, task["task_id"], query, ["https://example.org/search"],
                              "已检有新增" if original else "已检无合格新增", [original] if original else [],
                              1 if original else 0, "测试夹具；不是真实检索")
    write_json(path, plan)


class TopicTests(unittest.TestCase):
    def setUp(self):
        temporary_root = ROOT / "runtime" / "test-topics"
        temporary_root.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=temporary_root)
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.store = TopicStore(self.root, "test")

    def initialize(self):
        self.store.create(fixture())

    def accept(self, batch="trial", cutoff="2026-10-19T08:30:00+08:00"):
        path = self.store.plan(batch, cutoff, trial=True)["plan"]
        complete(path)
        self.store.accept(path, "测试覆盖与噪声")
        return path

    def test_initialization_gate_and_id_paths(self):
        self.store.create(blank_config("test", "测试"))
        self.assertFalse(self.store.check()["ready"])
        with self.assertRaises(ValueError):
            self.store.plan("first", trial=True)
        with self.assertRaises(ValueError):
            TopicStore(self.root, "../other")
        with self.assertRaises(ValueError):
            self.store.create(fixture())

    def test_keyword_expansion_and_actual_execution_required(self):
        self.initialize()
        with self.assertRaises(ValueError):
            self.store.plan("formal")
        path = self.store.plan("trial", trial=True)["plan"]
        plan = read_json(path)
        self.assertEqual(plan["tasks"][0]["queries"], ["算力 融资", "智算中心 融资"])
        with self.assertRaises(ValueError):
            self.store.accept(path, "尚未执行")
        record_search(plan, "T1", "算力 融资", [URL], "已检有新增", [URL], 1, "仅第一式完成")
        write_json(path, plan)
        with self.assertRaises(ValueError):
            self.store.accept(path, "漏执行扩展词")
        complete(path)
        self.store.accept(path, "全部词组核验")
        self.assertTrue(self.store.check()["ready"])

    def test_revision_conflict_and_invalidation(self):
        self.initialize()
        path = self.accept()
        updated = fixture()
        updated["keywords"][0]["terms"].append("data center")
        with self.assertRaises(ValueError):
            self.store.update(updated, 0, "旧版本")
        self.store.update(updated, 1, "补英文词")
        self.assertFalse(self.store.check()["ready"])
        with self.assertRaises(ValueError):
            self.store.accept(path, "不能用旧版试检")
        next_path = self.store.plan("trial2", trial=True)["plan"]
        self.assertIn("data center 融资", read_json(next_path)["tasks"][0]["queries"])

    def test_feedback_requires_linked_revision_and_retrieval(self):
        self.initialize()
        feedback = self.store.feedback(URL, "遗漏重要新闻")
        with self.assertRaises(ValueError):
            self.store.resolve(feedback["id"], "unknown", [URL], "尚未定位")
        with self.assertRaises(ValueError):
            self.store.resolve(feedback["id"], "keyword", [URL], "只补当期不修配置")
        updated = fixture()
        updated["keywords"][0]["terms"].append("GPU")
        self.store.update(updated, 1, "补主体词", feedback["id"])
        path = self.store.plan("recheck", trial=True)["plan"]
        complete(path, "https://example.org/other")
        self.store.accept(path, "未找回遗漏原文")
        with self.assertRaises(ValueError):
            self.store.resolve(feedback["id"], "keyword", [URL], "不能假关闭")
        complete(path)
        self.store.accept(path, "找回原文及同类样本，检查无关结果")
        result = self.store.resolve(feedback["id"], "keyword", [URL], "关键词修复并回查")
        self.assertEqual(result["status"], "resolved")
        self.assertEqual(result["resolved_version"], 2)

    def test_transient_execution_failure_can_be_retried_without_config_churn(self):
        self.initialize()
        feedback = self.store.feedback(URL, "上轮页面读取失败")
        self.accept()
        result = self.store.resolve(feedback["id"], "execution", [URL], "重新执行读取成功，配置无需变更")
        self.assertEqual(result["status"], "resolved")
        self.assertEqual(self.store.load()["version"], 1)

    def test_out_of_scope_feedback_keeps_reason_without_polluting_terms(self):
        self.initialize()
        feedback = self.store.feedback(URL, "疑似不相关")
        self.store.resolve(feedback["id"], "out_of_scope", [URL], "读原文后确认不符合主题范围")
        self.assertEqual(self.store.state()["feedback"][0]["status"], "dismissed")
        self.assertEqual(self.store.load()["version"], 1)

    def test_topic_isolation_and_successful_cutoff(self):
        self.initialize()
        self.accept()
        other = TopicStore(self.root, "other")
        other.create(fixture("other"))
        path = self.store.plan("daily", "2026-10-20T08:30:00+08:00")["plan"]
        complete(path, original=None)
        self.store.finish(path, None, [])
        followup = self.store.plan("next", "2026-10-21T08:30:00+08:00")["plan"]
        self.assertEqual(read_json(followup)["window_start"], "2026-10-20T08:30:00+08:00")
        self.assertEqual(other.state()["runs"], [])
        self.assertFalse(other.check()["ready"])
        with self.assertRaises(ValueError):
            other.accept(path, "跨主题记录不可采用")
        with self.assertRaises(ValueError):
            self.store.plan("next", "2026-10-22T08:30:00+08:00")

    def test_draft_handoff_tracks_events_and_rejects_duplicates(self):
        self.initialize()
        self.accept()
        draft = self.root / "daily.md"
        draft.write_text(f"# 测试\n\n**今日总结**：测试\n\n### 1. 测试事件\n\n用于测试的正文。\n\n来源：[测试]({URL})｜2026-10-20\n", encoding="utf-8")
        events = [{"event_id": "project:funding:2026-10-20", "source_url": URL}]
        path = self.store.plan("daily", "2026-10-20T08:30:00+08:00")["plan"]
        complete(path)
        self.store.finish(path, draft, events)
        next_path = self.store.plan("next", "2026-10-21T08:30:00+08:00")["plan"]
        self.assertEqual(read_json(next_path)["previous_events"], events)
        complete(next_path)
        with self.assertRaises(ValueError):
            self.store.finish(next_path, draft, events)

    def test_missing_refs_and_manual_tampering_fail(self):
        config = fixture()
        config["tasks"][0]["source_ids"] = ["missing"]
        with self.assertRaises(ValueError):
            validate(config)
        self.initialize()
        doc = self.store.load()
        doc["config"]["scope"] = "直接改主题"
        write_json(self.store.path, doc)
        with self.assertRaises(ValueError):
            self.store.check()

    def test_plan_cannot_skip_tasks_or_hide_failed_retries(self):
        self.initialize()
        path = self.store.plan("trial", trial=True)["plan"]
        complete(path)
        plan = read_json(path)
        record_search(plan, "T1", "算力 融资", [], "读取失败", [], None, "再次读取失败")
        record_search(plan, "T1", "智算中心 融资", [URL], "已检有新增", [URL], 1, "另一查询完成")
        write_json(path, plan)
        with self.assertRaises(ValueError):
            self.store.accept(path, "不能掩盖失败重试")
        plan["tasks"] = []
        write_json(path, plan)
        with self.assertRaises(ValueError):
            self.store.accept(path, "不能删除任务后验收")

    def test_legacy_import_preserves_ids_and_does_not_claim_execution(self):
        config = import_lowalt(ROOT, "lowalt")
        validate(config, ready=True)
        self.assertEqual(len(config["sources"]), 117)
        self.assertEqual(len(config["tasks"]), 246)
        self.assertEqual(len(config["legacy_objects"]), 207)
        self.assertIn("EC12", {x["id"] for x in config["tasks"]})
        self.assertEqual(sum(x["enabled"] and x["frequency"] in {"每日", "每周1"} for x in config["tasks"]), 193)
        self.assertIn("FC04", {x["id"] for x in config["tasks"]})
        self.assertTrue(all(x["status"] == "candidate" for x in config["sources"]))

    def test_cli_initialization_and_gate_exit_codes(self):
        base = ["topic", "--root", str(self.root)]
        self.assertEqual(main(base + ["init", "--id", "esg", "--name", "ESG"]), 0)
        self.assertEqual(main(base + ["check", "--id", "esg"]), 1)
        self.assertEqual(main(base + ["plan", "--id", "esg", "--batch", "first"]), 2)


if __name__ == "__main__":
    unittest.main()
