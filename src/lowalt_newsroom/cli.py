import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import date
import json
from pathlib import Path
import sys

from .feeds import fetch_feed, public_url
from .planning import STATUSES, build_plan, record_search
from .rendering import check_draft, render_markdown
from .workbooks import table_records
from .topic_cli import add_commands, run as run_topic


def write_json(path: str, value: dict) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    # 同目录原子替换；并发编辑同一记录不受支持，应使用不同批次文件。
    temporary = target.with_name(target.name + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(target)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="多主题新闻收集、核查与待审稿辅助工具")
    commands = parser.add_subparsers(dest="command", required=True)
    add_commands(commands)
    inventory = commands.add_parser("inventory", help="列出信源与搜索任务数量")
    inventory.add_argument("--sources", default="data/source_registry.xlsx")
    inventory.add_argument("--checklist", default="data/search_checklist.xlsx")
    plan = commands.add_parser("plan", help="生成计划，不标记任务完成")
    plan.add_argument("--checklist", default="data/search_checklist.xlsx")
    plan.add_argument("--date", required=True, type=date.fromisoformat)
    plan.add_argument("--batch", required=True)
    plan.add_argument("--output", required=True)
    record = commands.add_parser("record", help="登记实际执行，保留原查询与时间")
    record.add_argument("--plan", required=True)
    record.add_argument("--task-id", required=True)
    record.add_argument("--query", required=True)
    record.add_argument("--evidence", action="append", default=[])
    record.add_argument("--original", action="append", default=[])
    record.add_argument("--status", required=True, choices=sorted(STATUSES))
    record.add_argument("--findings", type=int)
    record.add_argument("--note", required=True)
    rss = commands.add_parser("rss", help="仅取得RSS/Atom线索，不宣称原文已读")
    rss.add_argument("--url", action="append", required=True)
    rss.add_argument("--timeout", type=float, default=12)
    rss.add_argument("--output", required=True)
    render = commands.add_parser("render", help="生成图片内嵌、原生加粗HTML")
    render.add_argument("input", type=Path)
    render.add_argument("--output", required=True, type=Path)
    check = commands.add_parser("check", help="检查公开稿格式与内部标签")
    check.add_argument("input", type=Path)
    args = parser.parse_args(argv)
    try:
        if args.command == "topic":
            result, code = run_topic(args)
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return code
        elif args.command == "inventory":
            result = {"sources": len(table_records(args.sources, "信源清单", "ID")),
                      "tasks": len(table_records(args.checklist, "检索任务", "任务ID")),
                      "objects": len(table_records(args.checklist, "覆盖对象", "对象ID"))}
        elif args.command == "plan":
            result = build_plan(args.checklist, args.date, args.batch)
            write_json(args.output, result)
            result = {"tasks": len(result["tasks"]), "due": sum(x["due"] for x in result["tasks"]),
                      "output": args.output, "actual_searches": 0}
        elif args.command == "record":
            result = json.loads(Path(args.plan).read_text(encoding="utf-8-sig"))
            for url in args.evidence + args.original:
                public_url(url)
            record_search(result, args.task_id, args.query, args.evidence, args.status,
                          args.original, args.findings, args.note)
            write_json(args.plan, result)
            result = {"task_id": args.task_id, "status": args.status, "output": args.plan}
        elif args.command == "rss":
            if not 0 < args.timeout <= 60:
                raise ValueError("超时应大于0且不超过60秒")
            with ThreadPoolExecutor(max_workers=min(4, len(args.url))) as pool:
                feeds = list(pool.map(lambda url: fetch_feed(url, args.timeout), args.url))
            write_json(args.output, {"feeds": feeds, "boundary": "摘要是线索，原文仍须独立核验"})
            result = {"feeds": len(feeds), "parsed": sum(x["status"] == "已解析订阅样本" for x in feeds), "output": args.output}
        elif args.command == "render":
            if args.input.resolve() == args.output.resolve():
                raise ValueError("输出不能覆盖Markdown原稿")
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(render_markdown(args.input), encoding="utf-8")
            result = {"output": str(args.output), "published": False}
        else:
            result = check_draft(args.input.read_text(encoding="utf-8-sig"))
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 1 if result["errors"] else 0
    except (OSError, ValueError, KeyError) as error:
        print(f"错误：{error}", file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0
