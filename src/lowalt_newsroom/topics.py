"""主题配置、试检、反馈和运行交接。仅记录实际执行，不代替联网核验。"""

from datetime import date, datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import re

from .feeds import public_url
from .planning import is_due
from .rendering import check_draft

LOCAL_TIME = timezone(timedelta(hours=8))
CAUSES = ("source", "keyword", "execution", "filter", "time_window", "unknown", "out_of_scope")
COMPLETE = {"已检有新增", "已检无合格新增"}


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def write_json(path, value):
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_name(target.name + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(target)


def identifier(value):
    if not isinstance(value, str) or not re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,63}", value):
        raise ValueError("主题和批次ID须为1—64位小写英文、数字、短横线或下划线")
    return value


def fingerprint(config):
    raw = json.dumps(config, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def now():
    return datetime.now(LOCAL_TIME).isoformat()


def timestamp(value):
    stamp = datetime.fromisoformat(value)
    if stamp.tzinfo is None:
        raise ValueError("时间必须带时区，如2026-10-19T08:30:00+08:00")
    return stamp.astimezone(LOCAL_TIME)


def strings(values, label, required=True):
    if not isinstance(values, list) or any(not isinstance(x, str) or not x.strip() for x in values):
        raise ValueError(f"{label}必须是非空字符串组成的数组")
    if required and not values:
        raise ValueError(f"缺少{label}")


def rows(config, key):
    values = config.get(key)
    if not isinstance(values, list) or any(not isinstance(x, dict) for x in values):
        raise ValueError(f"{key}必须是对象数组")
    ids = [x.get("id") for x in values]
    if any(not isinstance(x, str) or not x.strip() for x in ids) or len(set(ids)) != len(ids):
        raise ValueError(f"{key}含空ID或重复ID")
    return {x["id"]: x for x in values}


def queries(task, keywords):
    """只展开明确标注的词组；同义词分别查询，不拼成AND长串。"""
    result = []
    for template in task["queries"]:
        if "{term}" in template:
            for key in task["keyword_ids"]:
                result.extend(template.replace("{term}", term) for term in keywords[key]["terms"])
        else:
            result.append(template)
    return list(dict.fromkeys(result))


def validate(config, ready=False):
    if not isinstance(config, dict):
        raise ValueError("主题配置须为JSON对象")
    identifier(config.get("id"))
    for key in ("name", "scope", "audience"):
        if not isinstance(config.get(key), str) or (ready and not config[key].strip()):
            raise ValueError(f"缺少主题字段：{key}")
    if config.get("timezone") != "Asia/Shanghai":
        raise ValueError("当前版本统一使用Asia/Shanghai")
    for key in ("regions", "languages", "sections", "editorial_checks"):
        strings(config.get(key), key, ready)
    strings(config.get("exclude"), "exclude", False)
    for key in ("initial_hours", "lookback_days", "academic_days"):
        value = config.get("window", {}).get(key)
        if type(value) is not int or value <= 0:
            raise ValueError(f"window.{key}须为正整数")
    sources, keywords, tasks = (rows(config, key) for key in ("sources", "keywords", "tasks"))
    if ready:
        for key, values in (("信源清单", sources), ("检索词表", keywords), ("检索任务", tasks)):
            if not values:
                raise ValueError(f"请先填写{key}")
    for source in sources.values():
        for key in ("name", "type", "entry", "method", "status"):
            if not isinstance(source.get(key), str) or not source[key].strip():
                raise ValueError(f"信源{source['id']}缺少{key}")
        if source["entry"].startswith(("http:", "https:")):
            public_url(source["entry"])
        if source["status"] not in {"candidate", "readable", "limited", "failed"}:
            raise ValueError("信源status须为candidate/readable/limited/failed")
        if source["status"] == "readable" and not source.get("verification_note", "").strip():
            raise ValueError("可读信源须记录核验说明，不能把候选入口当作已接入")
    for keyword in keywords.values():
        strings(keyword.get("terms"), f"{keyword['id']}.terms")
    active = []
    for task in tasks.values():
        if type(task.get("enabled")) is not bool:
            raise ValueError("任务enabled须为布尔值")
        is_due(task.get("frequency", ""), date(2026, 10, 19))
        strings(task.get("keyword_ids"), "keyword_ids")
        strings(task.get("source_ids"), "source_ids", False)
        if set(task["keyword_ids"]) - keywords.keys() or set(task["source_ids"]) - sources.keys():
            raise ValueError(f"任务{task['id']}引用了不存在的信源或词组")
        strings(task.get("queries"), "queries")
        for query in task["queries"]:
            if "{" in query.replace("{term}", "") or "}" in query.replace("{term}", ""):
                raise ValueError("查询模板只支持{term}占位符")
        if not isinstance(task.get("verification"), str) or not task["verification"].strip():
            raise ValueError(f"任务{task['id']}缺少核验要求")
        if task["enabled"]:
            active.append(task)
    if ready and not active:
        raise ValueError("没有启用的检索任务")
    return sources, keywords, tasks


def blank_config(slug, name, scope=""):
    return {"id": identifier(slug), "name": name, "scope": scope, "audience": "行业研究与业务人员",
            "timezone": "Asia/Shanghai", "regions": ["中国", "海外"], "languages": ["中文", "英文"],
            "exclude": [], "sections": ["政策与监管", "企业与项目", "研究与报告", "行业机会"],
            "editorial_checks": ["读原文并核对主体、日期、数字、状态和限制", "只收实质新增信息，按事件去重，不凑条数"],
            "window": {"initial_hours": 24, "lookback_days": 7, "academic_days": 30},
            "sources": [], "keywords": [], "tasks": []}


class TopicStore:
    def __init__(self, root, slug):
        self.root = Path(root).resolve()
        self.slug = identifier(slug)
        self.path = self.root / "topics" / self.slug / "topic.json"
        self.runtime = self.root / "runtime" / self.slug
        if not self.path.resolve().is_relative_to(self.root) or not self.runtime.resolve().is_relative_to(self.root):
            raise ValueError("主题或运行目录超出项目根目录")

    def load(self):
        doc = read_json(self.path)
        validate(doc["config"])
        if doc["config"]["id"] != self.slug or doc["config_hash"] != fingerprint(doc["config"]):
            raise ValueError("主题配置被直接改动；请通过topic update记录版本")
        return doc

    def state(self):
        path = self.runtime / "state.json"
        return read_json(path) if path.exists() else {"trial": None, "feedback": [], "runs": []}

    def save_state(self, state):
        write_json(self.runtime / "state.json", state)

    def create(self, config):
        validate(config)
        if config["id"] != self.slug or self.path.exists() or self.runtime.exists():
            raise ValueError("主题ID不匹配，或已有配置/历史；拒绝覆盖")
        doc = {"schema_version": 1, "version": 1, "config_hash": fingerprint(config),
               "config": config, "changes": [{"version": 1, "time": now(), "reason": "初始化；尚未试检"}]}
        write_json(self.path, doc)
        return {"topic": self.slug, "version": 1, "next": "填写信源，再填写检索词与任务，执行试检"}

    def update(self, config, expected_version, reason, feedback_id=None):
        doc = self.load()
        validate(config)
        if config["id"] != self.slug or doc["version"] != expected_version:
            raise ValueError("主题ID或版本冲突，请重新读取当前配置")
        if not reason.strip() or fingerprint(config) == doc["config_hash"]:
            raise ValueError("请提供修改原因和实际配置变更")
        if feedback_id:
            self.feedback_item(self.state(), feedback_id)
        version = doc["version"] + 1
        change = {"version": version, "time": now(), "reason": reason,
                  "before_hash": doc["config_hash"], "after_hash": fingerprint(config)}
        # 只留本地反馈编号；新闻链接与私人备注保存在被Git忽略的runtime中。
        if feedback_id:
            change["feedback_id"] = feedback_id
        doc.update(version=version, config=config, config_hash=fingerprint(config))
        doc["changes"].append(change)
        write_json(self.path, doc)
        return {"topic": self.slug, "version": version, "next": "配置已变更，须重新试检"}

    def check(self):
        doc, state = self.load(), self.state()
        config = doc["config"]
        try:
            sources, keywords, tasks = validate(config, ready=True)
        except ValueError as error:
            return {"topic": self.slug, "ready": False, "next": str(error), "version": doc["version"]}
        trial = state["trial"]
        accepted = bool(trial and trial["config_hash"] == doc["config_hash"])
        linked = {s for task in tasks.values() if task["enabled"] for s in task["source_ids"]}
        warnings = [f"{len(set(sources) - linked)}个信源未关联启用任务"] if set(sources) - linked else []
        warnings += [f"{sum(s['status'] != 'readable' for s in sources.values())}个信源尚有候选或访问限制；不得宣称全覆盖"]
        return {"topic": self.slug, "version": doc["version"], "ready": accepted,
                "next": "可生成正式采集计划" if accepted else "执行topic plan --trial，再登记真实查询并topic accept",
                "sources": len(sources), "keywords": len(keywords), "tasks": len(tasks), "warnings": warnings}

    def plan(self, batch, cutoff=None, trial=False):
        identifier(batch)
        doc = self.load()
        config = doc["config"]
        _, keywords, _ = validate(config, ready=True)
        if not trial and not self.check()["ready"]:
            raise ValueError("当前配置尚未通过试检，请先使用--trial")
        end = timestamp(cutoff or now())
        state = self.state()
        start = timestamp(state["runs"][-1]["cutoff"]) if state["runs"] else end - timedelta(hours=config["window"]["initial_hours"])
        if end <= start:
            raise ValueError("本次截止须晚于最近成功截止")
        path = self.runtime / "runs" / batch / "plan.json"
        if path.exists():
            raise ValueError("批次已存在，请使用新的批次ID，避免覆盖执行记录")
        tasks = []
        for task in config["tasks"]:
            due = task["enabled"] and is_due(task["frequency"], end.date())
            expanded = queries(task, keywords)
            tasks.append({"task_id": task["id"], "target": task.get("target", task["id"]),
                          "keyword_ids": task["keyword_ids"], "source_ids": task["source_ids"],
                          "frequency": task["frequency"], "due": due,
                          "status": "未执行" if due else "不在本轮计划",
                          "primary_query": expanded[0], "queries": expanded,
                          "verification_boundary": task["verification"], "instructions": task.get("instructions", []),
                          "searches": [], "findings": None, "originals_read": None, "adopted_events": []})
        if not any(x["due"] for x in tasks):
            raise ValueError("本日无到期任务；可调整频率或选择适合的截止日期")
        plan = {"topic": self.slug, "config_version": doc["version"], "config_hash": doc["config_hash"],
                "config_snapshot": config, "date": end.date().isoformat(), "batch": batch, "trial": trial,
                "generated_at": now(), "cutoff": end.isoformat(), "window_start": start.isoformat(),
                "lookback_days": config["window"]["lookback_days"], "academic_days": config["window"]["academic_days"],
                "previous_events": [event for run in state["runs"] for event in run["events"]],
                "note": "计划不是执行成果；缺口不得记为无新增；扩展查询须逐条执行。", "tasks": tasks}
        write_json(path, plan)
        return {"plan": str(path), "topic": self.slug, "due": sum(x["due"] for x in tasks), "actual_searches": 0}

    def executed_plan(self, path):
        plan, doc = read_json(path), self.load()
        expected_path = self.runtime / "runs" / identifier(plan["batch"]) / "plan.json"
        if Path(path).resolve() != expected_path.resolve():
            raise ValueError("计划须来自本主题runtime目录")
        if (plan.get("topic") != self.slug or plan.get("config_hash") != doc["config_hash"]
                or plan.get("config_version") != doc["version"]):
            raise ValueError("计划不属于当前主题配置版本，请重新试检或生成计划")
        expected = {x["id"]: x for x in doc["config"]["tasks"]}
        actual = {x["task_id"]: x for x in plan["tasks"]}
        if len(actual) != len(plan["tasks"]) or actual.keys() != expected.keys():
            raise ValueError("计划任务有缺失或重复")
        keywords = rows(doc["config"], "keywords")
        originals = set()
        due_count = 0
        for task_id, definition in expected.items():
            task = actual[task_id]
            due = definition["enabled"] and is_due(definition["frequency"], timestamp(plan["cutoff"]).date())
            if task["due"] != due or task["queries"] != queries(definition, keywords):
                raise ValueError("计划频率或查询被改动，请重新生成计划")
            if not due:
                continue
            due_count += 1
            latest = {x["query"]: x for x in task["searches"]}
            completed = {x["query"] for x in latest.values() if x.get("status") in COMPLETE and x.get("evidence_urls") and x.get("scope_and_gaps", "").strip()}
            if task["status"] not in COMPLETE or set(task["queries"]) - completed:
                raise ValueError(f"任务{task_id}尚未完成全部计划查询与核验；保留缺口后继续执行")
            originals.update(url for x in task["searches"] for url in x["original_urls"])
        if not due_count:
            raise ValueError("计划中没有到期任务")
        return plan, originals

    def accept(self, path, note):
        plan, originals = self.executed_plan(path)
        if not plan["trial"] or not originals or not note.strip():
            raise ValueError("试检验收须使用试检计划，关联至少一篇已读原文并说明覆盖与噪声检查")
        state = self.state()
        state["trial"] = {"config_hash": plan["config_hash"], "version": plan["config_version"],
                          "batch": plan["batch"], "accepted_at": now(), "note": note, "originals": sorted(originals)}
        self.save_state(state)
        return {"topic": self.slug, "accepted": True, "boundary": "依据编辑登记的实际执行验收，不自动证明事实正确或全网无遗漏"}

    def feedback_item(self, state, feedback_id):
        item = next((x for x in state["feedback"] if x["id"] == feedback_id), None)
        if item is None or item["status"] != "open":
            raise ValueError("反馈不存在或已关闭")
        return item

    def feedback(self, url, note):
        public_url(url)
        if not note.strip():
            raise ValueError("请说明遗漏内容和重要性")
        doc, state = self.load(), self.state()
        item = {"id": f"F{len(state['feedback']) + 1:04d}", "url": url, "note": note,
                "created_at": now(), "version": doc["version"], "status": "open", "cause": "unknown"}
        state["feedback"].append(item)
        self.save_state(state)
        return item

    def resolve(self, feedback_id, cause, evidence, note):
        if cause not in CAUSES or cause == "unknown" or not evidence or not note.strip():
            raise ValueError("须有已定位原因、证据和说明；原因不明的反馈保持open")
        for url in evidence:
            public_url(url)
        doc, state = self.load(), self.state()
        item = self.feedback_item(state, feedback_id)
        if cause != "out_of_scope":
            linked = [x for x in doc["changes"] if x.get("feedback_id") == feedback_id and x["version"] > item["version"]]
            trial = state["trial"]
            if (not trial or trial["config_hash"] != doc["config_hash"]
                    or timestamp(trial["accepted_at"]) <= timestamp(item["created_at"])):
                raise ValueError("须在反馈后完成当前版本试检")
            if not linked and cause != "execution":
                raise ValueError("须先用topic update --feedback关联修正，再通过当前版本试检")
            if item["url"] not in trial["originals"]:
                raise ValueError("回查未关联该遗漏新闻的原始链接；请在试检记录中补齐")
        item.update(status="dismissed" if cause == "out_of_scope" else "resolved", cause=cause,
                    evidence=evidence, resolution=note, resolved_at=now(), resolved_version=doc["version"],
                    trial_batch=None if cause == "out_of_scope" else state["trial"]["batch"])
        self.save_state(state)
        return item

    def finish(self, path, draft, events):
        plan, originals = self.executed_plan(path)
        if plan["trial"] or not self.check()["ready"]:
            raise ValueError("试检不推进正式采集截止；正式运行须通过当前配置试检")
        state = self.state()
        if state["runs"] and timestamp(plan["window_start"]) != timestamp(state["runs"][-1]["cutoff"]):
            raise ValueError("已有较新成功批次，请重新生成增量计划")
        if any(x["batch"] == plan["batch"] for x in state["runs"]):
            raise ValueError("该批次已交接")
        if not isinstance(events, list):
            raise ValueError("事件文件须为数组")
        if events:
            if not draft:
                raise ValueError("有采用事件时须提供待审稿")
            text = Path(draft).read_text(encoding="utf-8-sig")
            checked = check_draft(text)
            if checked["errors"] or checked["articles"] != len(events):
                raise ValueError("待审稿格式或新闻条数与事件清单不匹配")
        elif draft:
            raise ValueError("无合格新增时不提供新闻稿，以空事件清单交接")
        ids = set()
        previous = {x["event_id"] for run in state["runs"] for x in run["events"]}
        for event in events:
            if not isinstance(event, dict) or not isinstance(event.get("event_id"), str) or not event["event_id"].strip():
                raise ValueError("每个事件须有非空event_id和source_url")
            if event["event_id"] in ids or event["event_id"] in previous:
                raise ValueError("事件ID重复；同项目新阶段须使用新的规范事件键")
            if event.get("source_url") not in originals or event["source_url"] not in text:
                raise ValueError("事件来源须在已读原文及待审稿中出现")
            ids.add(event["event_id"])
        state["runs"].append({"batch": plan["batch"], "cutoff": plan["cutoff"], "events": events,
                              "config_hash": plan["config_hash"], "finished_at": now(), "published": False})
        self.save_state(state)
        return {"topic": self.slug, "cutoff": plan["cutoff"], "events": len(events), "published": False}
