# 飞行汽车独立检索

搜索清单v1.6新增以下6项每日启用任务。补充检索按行分别执行，不将同义词合并为必须同时命中的条件。原有eVTOL、无人机与监管检索继续保留。

|任务ID|主检索式（必做）|逐行补充检索|
|---|---|---|
| FC01-CN | 飞行汽车 | 飞行跑车；陆空两用汽车 |
| FC01-EN | "flying car" | "flying cars"；"roadable aircraft" |
| FC02-CN | 特斯拉 飞行 | 特斯拉 飞行汽车；特斯拉 Roadster |
| FC02-EN | Tesla flying | Tesla "flying car"；Tesla Roadster |
| FC03 | Roadster | Roadster thrusters；Roadster flight |
| FC04 | 马斯克 飞行汽车 | "Elon Musk" "flying car"；马斯克 Roadster |

关联词组为K13，覆盖对象为X-FC01（跨领域飞行汽车）、E-FC01（Tesla）和P-FC01（Roadster）。关联源ID沿用R01/R02/R03及涉及美国监管时的O09；开放搜索不限这些来源。Tesla官方管理层页已用于核身份，Roadster产品页本次只读到脚注；官网尚未登记为稳定信源，RSS/API未知。

## 命中后的处理

每个重要候选事件登记规范事件键、发现查询及时间、线索链接、原始发布/事件日期、已读范围和去向。去向写明采用、待核或不采用原因；未完成原文核验的线索必须保留，不能只留在搜索回执中。人物发言保留主体归属，Tesla与SpaceX、其他公司分别核实。

演示、预订、量产计划、适航审定、商业运行授权和交付逐项区分。Roadster检索排除服饰品牌、无关车型和旧概念重发。不得根据车辆腾空演示推定获适航证或允许商业载客，也不推断ETF收益或股价影响。

## 2026-10-19维护试检

本次实际提交6条主式、12条逐行补充，共18条查询，均使用近7日发现范围。查询时间如下（UTC，北京时间加8小时）：

- 2026-10-19T07:53:20.631Z：`飞行汽车`、`"flying car"`、`特斯拉 飞行`
- 2026-10-19T07:53:28.543Z：`Tesla flying`、`Roadster`、`马斯克 飞行汽车`
- 2026-10-19T07:56:33.966Z：`飞行跑车`、`陆空两用汽车`、`"flying cars"`
- 2026-10-19T07:56:39.386Z：`"roadable aircraft"`、`特斯拉 飞行汽车`、`特斯拉 Roadster`
- 2026-10-19T07:56:45.558Z：`Tesla "flying car"`、`Tesla Roadster`、`Roadster thrusters`
- 2026-10-19T07:56:51.431Z：`Roadster flight`、`"Elon Musk" "flying car"`、`马斯克 Roadster`

每组3条查询共享响应，未将结果数或链接分摊为逐式发现数。命中新闻与候选包括[Roadster展示报道](https://www.euronews.com/2026/10/16/well-it-worked-elon-musk-unveils-new-tesla-roadster-that-can-fly)、[企业飞行汽车线索](https://www.xiaopeng.com/news/company_news/5241.html)及其他公开报道；本页登记发现，不将它们标为本次全文核验成功或直接采用。

原始查询回执和逐任务记录写入本机runtime/2026-10-19-FC；发现数及已读原文数未知项保留为空。本次不重写早上日报、不改变其采集截止；不把专项试检作为新的全量成功基线。执行记录模板仍全部保留未执行，运行成果另存。

