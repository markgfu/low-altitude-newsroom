from datetime import date, datetime, timezone
import re

from .workbooks import table_records

STATUSES = {"未执行", "已检有新增", "已检无合格新增", "已发现待核", "读取失败", "不在本轮计划"}
INSTRUCTION = re.compile(r"^(查数据库|结果少时|当地政府、公报|将行业日报|按原站|主检索与|先核|身份核实)")


def supplementary_steps(value: str) -> list[dict]:
    return [{"text": line.strip(), "kind": "instruction" if INSTRUCTION.search(line.strip()) else "query_or_entry", "status": "未执行"}
            for line in re.split(r"\r?\n|\\n", value) if line.strip()]


def is_due(frequency: str, day: date) -> bool:
    if frequency == "每日":
        return True
    match = re.fullmatch(r"每周([1-7])", frequency)
    if match:
        return int(match[1]) == day.isoweekday()
    if frequency in {"线索触发", "按需", "未启用"}:
        return False
    raise ValueError(f"未识别频率：{frequency}")


def build_plan(workbook: str, day: date, batch: str) -> dict:
    records = table_records(workbook, "检索任务", "任务ID")
    tasks = []
    for record in records:
        enabled = record.get("启用状态") == "启用"
        due = enabled and is_due(record["执行频率"], day)
        tasks.append({
            "task_id": record["任务ID"], "object_id": record["对象ID"],
            "keyword_id": record["词组ID"], "source_ids": record["关联信源ID"],
            "target": record["对象或地区"], "frequency": record["执行频率"],
            "due": due, "status": "未执行" if due else "不在本轮计划",
            "primary_query": record["主检索式（必做）"],
            "supplementary": supplementary_steps(record["补充检索式或原站路径"]),
            "verification_boundary": record["完成条件与核验边界"],
            "searches": [], "findings": None, "originals_read": None, "adopted_events": [],
        })
    return {"date": day.isoformat(), "batch": batch,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "note": "计划不是执行成果；搜索、原文、附件和分页分别记录。", "tasks": tasks}


def record_search(plan: dict, task_id: str, query: str, evidence: list[str], status: str,
                  originals: list[str], findings: int | None, note: str) -> None:
    if status not in STATUSES:
        raise ValueError("无效任务状态")
    task = next((x for x in plan["tasks"] if x["task_id"] == task_id), None)
    if task is None or not task["due"]:
        raise ValueError("任务不存在或不在本轮计划")
    if not query.strip() or INSTRUCTION.search(query.strip()):
        raise ValueError("必须记录实际查询式；执行说明不能充作查询")
    if not evidence and status != "读取失败":
        raise ValueError("缺少结果或实际入口链接")
    if status == "已检有新增" and not originals:
        raise ValueError("已检有新增必须关联已读原文；仅发现线索应记待核")
    if status in {"已检有新增", "已检无合格新增"} and not note.strip():
        raise ValueError("完成状态必须说明实际核验范围")
    if findings is not None and findings < 0:
        raise ValueError("发现数不可为负；未知使用空值")
    task["searches"].append({"time_utc": datetime.now(timezone.utc).isoformat(),
                             "query": query, "evidence_urls": evidence,
                             "original_urls": originals, "scope_and_gaps": note,
                             "status": status, "findings": findings})
    task["status"] = status
    task["findings"] = findings
    urls = {u for search in task["searches"] for u in search["original_urls"]}
    task["originals_read"] = len(urls) if urls else None
