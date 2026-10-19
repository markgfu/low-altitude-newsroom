# 低空经济新闻工作台

面向低空经济公众号的新闻收集、开放搜索、原文核查和待审稿工作流。

这个仓库把每日工作需要的信源、搜索任务、编辑规则与辅助命令放在一起。**联网搜索与事实核验由编辑或具备联网能力的Agent实际执行；命令生成检索计划、保存执行记录、读取订阅和排版，不自动证明新闻已核实。** 最终审稿、核图及公众号发布由账号拥有者在微信官方后台完成。

本项目以 **Public** 仓库提供规则、公开信源清单和待审稿示例；个人运行历史及账号配置由使用者在本机独立保存。

首次在自己的Codex中运行，请从[START_HERE.md](START_HERE.md)开始。根目录`AGENTS.md`提供项目执行约定。

## 已有内容

| 路径 | 用途 |
|---|---|
| `data/source_registry.xlsx` | 2026-10-19信源快照：117个来源，含候选及访问限制 |
| `data/search_checklist.xlsx` | 240项搜索任务、204个覆盖对象及执行记录模板 |
| `docs/editorial_rules.md` | 编辑规则v1.10，包括一段式低空学术摘要 |
| `docs/agent_runbook.md` | 每日搜索、核验、去重和交接要求 |
| `src/lowalt_newsroom/` | Python标准库实现的辅助工具 |
| `examples/2026-10-19/` | 6条消息、1张有许可原稿图的待审稿示例；非已发布稿 |
| `tests/` | 任务计划、执行记录、订阅解析和排版边界测试 |

原始一次性修订脚本依赖本机路径、特定表格行号和旧版本，未纳入可重复执行的生产流程。

## 快速使用

需要Python 3.11及以上版本。运行命令没有第三方依赖。

Windows PowerShell：

```powershell
$env:PYTHONPATH = (Resolve-Path .\src).Path
python -m lowalt_newsroom inventory
python -m lowalt_newsroom plan --date 2026-10-19 --batch 20261019-A --output runtime/20261019/plan.json
python -m lowalt_newsroom check examples/2026-10-19/daily.md
python -m lowalt_newsroom render examples/2026-10-19/daily.md --output output/20261019/daily.html
python -m unittest discover -s tests -v
```

macOS/Linux：

```bash
export PYTHONPATH="$PWD/src"
python -m lowalt_newsroom inventory
python -m lowalt_newsroom plan --date 2026-10-19 --batch 20261019-A --output runtime/20261019/plan.json
python -m lowalt_newsroom check examples/2026-10-19/daily.md
python -m lowalt_newsroom render examples/2026-10-19/daily.md --output output/20261019/daily.html
```

也可执行 `python -m pip install -e .` 安装命令 `lowalt-news`；构建时可能需要下载setuptools。直接使用上面的`PYTHONPATH`方式即可离线运行。

## 每日如何做

1. 更新本地清单和规则；确认上次成功采集截止及已收录事件。
2. 用`plan`生成本日任务。每日任务与当日每周任务列为未执行，触发任务不自动启用。
3. 按主检索式、逐行补充和原站入口实际搜索。31省专项与综合政策分别执行，另做学术、标准、海外和采购检索。
4. 读原文和能取得的附件，核对日期、主体、数字、政策状态和项目阶段。订阅和搜索摘要只作线索。
5. 登记执行时间、实际式、证据、已读范围、采用事项和缺口。去重后按日期优先编稿，不设固定条数。
6. 单独保存公开正文和内部附记。用`check`做格式检查，用`render`生成图片内嵌HTML，最后人工审稿。

`plan`的输出全部是计划。它不会执行搜索，也不会把“生成查询式”登记成“搜索完成”。当前规则中的主检索、原文、附件和分页验收要求，不能由脚本输出的数量替代。

### 记录实际检索

```powershell
python -m lowalt_newsroom record --plan runtime/20261019/plan.json --task-id GP09-A --query "上海 低空经济 政策" --evidence "https://www.shanghai.gov.cn/" --status "已发现待核" --note "已搜到入口；尚未读取命中文件，不能判断无新增"
```

命令中的入口仅演示记录方式，不代表这项检索已实际完成。未知发现数省略`--findings`，不填0。要登记“已检有新增”，还必须用`--original`关联已读原文，并在`--note`说明实际核验范围。

### 读取RSS/Atom线索

```powershell
python -m lowalt_newsroom rss --url "https://ir.ehang.com/rss/news-releases.xml" --output runtime/feeds.json
```

该入口来自信源快照，访问能力仍须以当次结果为准。HTTP200与空订阅、日期解析失败、正文未读分别记录；不使用RSS条目日期替代原文日期。

## 当前边界

- 已实现：只读清单、按频率生成计划、实际检索记录、RSS2/Atom线索读取、公开稿格式检查、Markdown正文子集到HTML转换和本地图片内嵌。
- 需编辑或联网Agent执行：开放互联网搜索、政策/论文/标准全文核验、采购更正跟踪、图像内容与许可检查、写稿及最终审核。
- 尚未实现：全站分页采集、自动正文抽取、中文付费数据库接入、公众号草稿箱/群发、无人值守日更服务。
- 两份Excel保留原工作表与ID。已有原生表格筛选范围未覆盖所有后续新增行；本工具读取全部实际行，Excel界面筛选范围仍需另行修复。
- HTML静态校验不保证微信粘贴后排版完全一致。内嵌图片适合本地预览，微信后台可能需要重新上传原图。

## 更新清单与规则

`data/`是项目整理时的版本快照。持续编辑仍应以账号中当前的主信源文件、搜索清单和编辑规则为准，不能用仓库旧快照覆盖较新文件。更新时保留ID、历史说明、工作表及版本保护，并在`data/SNAPSHOT.json`登记版本和哈希。

原始抓取全文、签名下载地址、账号登录态、上传回执和本机浏览器配置不进入Git。研究和图片版权说明见[素材与权限](docs/rights.md)。
