"""多主题CLI；保留旧命令供原有低空工作流兼容使用。"""

import re

from .planning import supplementary_steps
from .topics import CAUSES, TopicStore, blank_config, read_json, write_json
from .workbooks import table_records


def add_commands(commands):
    topic = commands.add_parser("topic", help="新建主题、配置检查、试检、反馈修正与交接")
    topic.add_argument("--root", default=".", help="项目根目录，默认当前目录")
    actions = topic.add_subparsers(dest="action", required=True)
    for name, help_text in (
        ("init", "新建空白主题，可带算力金融或ESG建议"),
        ("import-lowalt", "从现有Excel迁移低空配置，保留全部ID与说明"),
        ("export", "导出可编辑配置；用update保存版本"),
        ("update", "保存配置修订并使旧试检失效"),
        ("check", "检查配置及本机试检状态"),
        ("plan", "按主题生成采集或试检计划"),
        ("accept", "按真实查询记录验收试检"),
        ("feedback", "登记遗漏，尚不推断原因"),
        ("resolve", "以修订与回查证据关闭遗漏反馈"),
        ("status", "查看本主题运行与反馈记录"),
        ("finish", "交接成功批次、采集截止和事件记录"),
    ):
        command = actions.add_parser(name, help=help_text)
        command.add_argument("--id", required=True, help="主题ID，如lowalt/esg/compute-finance")
        if name == "init":
            command.add_argument("--name", required=True)
            command.add_argument("--scope", default="")
            command.add_argument("--preset", choices=["generic", "esg", "compute-finance"], default="generic")
        elif name == "export":
            command.add_argument("--output", required=True)
        elif name == "update":
            command.add_argument("--config", required=True)
            command.add_argument("--expected-version", required=True, type=int)
            command.add_argument("--reason", required=True)
            command.add_argument("--feedback", help="关联本机未关闭反馈ID")
        elif name == "plan":
            command.add_argument("--batch", required=True)
            command.add_argument("--cutoff", help="带时区的截止时间，默认当前北京时间")
            command.add_argument("--trial", action="store_true")
        elif name == "accept":
            command.add_argument("--plan", required=True)
            command.add_argument("--note", required=True, help="实际检查的覆盖、相关性与噪声")
        elif name == "feedback":
            command.add_argument("--url", required=True)
            command.add_argument("--note", required=True)
        elif name == "resolve":
            command.add_argument("--feedback", required=True)
            command.add_argument("--cause", required=True, choices=CAUSES)
            command.add_argument("--evidence", action="append", required=True)
            command.add_argument("--note", required=True)
        elif name == "finish":
            command.add_argument("--plan", required=True)
            command.add_argument("--draft")
            command.add_argument("--events", required=True, help="事件数组JSON；无合格新增时使用[]")


def import_lowalt(root, slug):
    config = blank_config(slug, "低空经济", "低空装备、基础设施、运行保障与应用；国内与海外，上海及长三角深入")
    config["sections"] = ["低空政策动态", "低空标准动态", "低空企业动态", "基础设施与项目建设", "低空应用动态", "国外动态", "低空学术", "行业机会"]
    config["editorial_checks"] += ["沿用docs/editorial_rules.md及docs/agent_runbook.md低空专业规则",
                                    "31省专项与综合政策分别查；企业、学术、标准、采购和海外分别查"]
    checklist = root / "data/search_checklist.xlsx"
    sources = table_records(root / "data/source_registry.xlsx", "信源清单", "ID")
    config["sources"] = [{"id": x["ID"], "name": x["信源名称"], "type": x["信源类型"],
                          "entry": x["入口URL"] or x["入口定位"] or "待定位入口",
                          "method": x["建议发现方式"] or "开放搜索后追溯原文", "status": "candidate",
                          "verification_note": "历史状态见legacy；迁移不代表本机已重新验收", "legacy": x} for x in sources]
    config["keywords"] = [{"id": x["词组ID"], "label": x["主题"],
                           "terms": [t.strip() for t in x["主体与同义词"].split("；") if t.strip()],
                           "legacy": x} for x in table_records(checklist, "词库与规则", "词组ID") if re.fullmatch(r"K\d+", x["词组ID"])]
    config["tasks"] = []
    for x in table_records(checklist, "检索任务", "任务ID"):
        steps = supplementary_steps(x["补充检索式或原站路径"])
        config["tasks"].append({"id": x["任务ID"], "target": x["对象或地区"],
                                "keyword_ids": [s for s in re.split(r"[;；]", x["词组ID"]) if s],
                                "source_ids": [s for s in re.split(r"[;；]", x["关联信源ID"]) if s],
                                "queries": [x["主检索式（必做）"]] + [s["text"] for s in steps if s["kind"] != "instruction"],
                                "instructions": [s["text"] for s in steps if s["kind"] == "instruction"],
                                "frequency": x["执行频率"], "enabled": x["启用状态"] == "启用",
                                "verification": x["完成条件与核验边界"], "legacy": x})
    config["legacy_objects"] = table_records(checklist, "覆盖对象", "对象ID")
    config["migration_note"] = "原Excel保持只读快照；本主题迁移后以JSON为运行配置。较新主表应核对差异后用update更新，不覆盖修订历史。"
    return config


def run(args):
    store = TopicStore(args.root, args.id)
    if args.action == "init":
        config = blank_config(args.id, args.name, args.scope)
        if args.preset != "generic":
            suggestions = read_json(store.root / "templates" / f"{args.preset}.json")
            config["suggestions"] = suggestions
            if not args.scope:
                config["scope"] = suggestions["proposed_scope"]
        return store.create(config), 0
    if args.action == "import-lowalt":
        return store.create(import_lowalt(store.root, args.id)), 0
    if args.action == "export":
        from pathlib import Path
        output = Path(args.output).resolve()
        if output.is_relative_to((store.root / "topics").resolve()) or output == (store.runtime / "state.json").resolve():
            raise ValueError("请导出到runtime下独立草稿文件，不能覆盖正式主题或状态文件")
        doc = store.load()
        write_json(output, doc["config"])
        return {"output": str(output), "version": doc["version"]}, 0
    if args.action == "update":
        return store.update(read_json(args.config), args.expected_version, args.reason, args.feedback), 0
    if args.action == "check":
        result = store.check()
        return result, 0 if result["ready"] else 1
    if args.action == "plan":
        return store.plan(args.batch, args.cutoff, args.trial), 0
    if args.action == "accept":
        return store.accept(args.plan, args.note), 0
    if args.action == "feedback":
        return store.feedback(args.url, args.note), 0
    if args.action == "resolve":
        return store.resolve(args.feedback, args.cause, args.evidence, args.note), 0
    if args.action == "status":
        store.load()
        return store.state(), 0
    if args.action == "finish":
        return store.finish(args.plan, args.draft, read_json(args.events)), 0
    raise ValueError("未知主题操作")
