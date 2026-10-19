# 社交媒体信源：叙事雷达方式的复用

社交平台纳入各主题的信源和日检任务。它们能提供企业首发、行业线索、现场记录与讨论；取得帖子不等于事实已经核实。企业自己的发布可以作为其声明的原始来源，政策、融资完成、适航批准等结论仍追发文机构或公告。

## 已核对的原项目实现

本次只读核对了本机叙事雷达的 `probe_social.py`、`inspect_social.py`、`export_social_probe.py`、README及试采记录。其2026-10-11试采采用公开详情链接、匿名GET、HTML可见文本/明确的页面数据结构、时间和SHA-256留档：15次请求取得雪球3条、微博2条正文，小红书0条。微博年份未确认时保留空值，搜索壳和验证页未计作正文。原项目的X实采成功记录未找到。

当前信源清单另有WeRSS静态评估及XML兼容历史说明，不能据此断言已经部署了可用的公众号采集服务。本次没有把旧项目的ETF词表、原始帖子或登录资料复制进公开仓库。

## 当前接入能力

| 平台 | 发现与获取方式 | 当前边界 |
|---|---|---|
| X | 主题检索、明确账号/帖子；实际API导出或浏览器可见正文导入 | 本仓库未部署X API客户端；未取得授权接口样本，不声称全量抓取 |
| 小红书 | 主题检索、笔记永久链接；登录后实际可见正文导入 | 后续登录复测已见低空经济30个结果卡片；正文读取仍失败，详见下文 |
| 公众号 | 已知文章URL读取`js_content`；已有WeRSS等系统导出的RSS/Atom正文导入 | 单篇URL不是账号订阅；未配置真实订阅源时不生成虚构feed地址 |
| 雪球 | 公开详情页明确的`SNOWMAN_STATUS`对象 | 按页面完整性标志处理；无结构或验证页保留失败 |
| 微博 | 公开详情探测及实际可见正文导入 | 月日时间不补造年份，当前未写通用HTML正文解析器 |

2026-10-19本机匿名GET重试了3篇已知公众号文章、X首页和小红书入口，均在收到HTTP响应前发生URLError。这是本机传输失败，不能据此判定各站永久不可采、没有新闻或账号不存在。浏览器创建小红书标签时工具超时，同样不计作平台拒绝。网络恢复或已登录浏览器可用后，沿相同来源ID重试。

## 命令

所有社交结果写入Git忽略的`runtime/`。API和浏览器取得的正文统一导入；不运行上游项目、不自动启动浏览器或常驻服务。

```powershell
$env:PYTHONPATH = (Resolve-Path .\src).Path
python -m lowalt_newsroom social probe --platform wechat --source-id W01 --url "https://mp.weixin.qq.com/s/-gl9-01nB8NoBPCTKiZeyg" --output runtime/social/probe.json
python -m lowalt_newsroom social import --input runtime/social/captured.json --output runtime/social/documents.json
python -m lowalt_newsroom social feed --platform wechat --source-id W01 --input runtime/social/export.xml --captured-at "2026-10-19T19:00:00+08:00" --output runtime/social/feed-documents.json
```

导入记录使用下面的字段；此处仅为格式说明，执行前替换为真实已读帖子及实际采集时间。JSON也可为记录数组。

```json
{
  "source_id": "SOC-X",
  "platform": "x",
  "url": "https://x.com/example/status/123",
  "route": "browser_visible",
  "sampling_method": "selected_permalink",
  "query": "实际执行的检索词",
  "captured_at": "2026-10-19T19:00:00+08:00",
  "published_at_raw": "页面显示的原始时间，未知可留空",
  "author": "页面显示的作者",
  "body": "实际取得的正文，不能填搜索摘要",
  "body_extent": "unknown"
}
```

`body_extent`为full、partial或unknown；导入保留实际正文哈希，强制`fact_verified=false`、`review_status=waiting_review`。采集时间与发布时间独立；无时区、不完整日期不自动换算。`available_at`指该条正文快照实际取得时点，合并历史时保留最早成功快照，不把过去发布日期当作本机当时可得。

RSS/Atom的`content:encoded`或`content`可导入正文，`description`只作线索；取得订阅正文仍不证明全文完整。WeRSS版本和路由可能不同，应使用已部署实例实际导出的文件，不照搬网络示例地址。参考：[WeRSS](https://github.com/letuswerss/werss)、[RSS内容字段问题记录](https://github.com/rachelos/we-mp-rss/issues/432)、[X官方分页说明](https://docs.x.com/xdks/python/pagination)。

## social-source-intake 兼容导入与登录复测

新增离线入口，不要求其他电脑安装本机skill。标准库校验器按用户提供的技能脚本适配，来源内容哈希保存在模块头；不运行独立浏览器，不读取Cookie或隐藏页面状态。

```powershell
python -m lowalt_newsroom social intake --source-id SOC-XHS --input runtime/social/capture-pack.json --output runtime/social/intake-observation-001.json
# 有项目明确热度门槛时才追加 --policy runtime/social/heat-policy.json
```

支持`social-capture-v1`、`social-browser-observation-v1`、`social-intake-batch-v1`。输入包含真实正文、公开帖子链接、带时区观察时间、正文证据及互动数原始显示。完整性声明须附范围；正文哈希不一致、凭证字段和带访问参数的导出链接会拒绝导入。输出仅限`runtime/`，已经存在的观察文件不能覆盖。原始截图、采集包和项目独立profile保存在忽略的`.private-social/`或`runtime/`，不能复制其他项目profile。

点赞、评论、转发、收藏分别保存；“1.2万”等显示不写成精确整数，缺失值保持null。日期只显示月日或相对时间时保留原样，编辑日期与首发日期分开，不能从导入时间反推发布时间。浏览器观察的读取区间、未知的实际DOM时点和原缺口会保留。热度策略缺省为unconfigured；命中阈值仍不自动提升为事实、有效讨论或日报收录。标签/标题单独成文标为缺少独立论述，其余内容依旧待人工复核。

2026-10-19登录后复测：低空经济搜索成功显示30个候选卡片；点击第一条后浏览器读取超时，标签标题/地址显示已进入帖子但没有取得正文。随后公开永久链接显示“当前笔记暂时无法浏览”（300031）。该入口停止；算力金融检索框检查也因浏览器连接超时而未提交查询。详情成功0条，不能以登录成功或卡片数量替代采集成功。详见[独立复测记录](../examples/social-intake-2026-10-19/README.md)。

恢复顺序：先恢复CUA连接，在正常网页确认详情可见；明确拒绝的入口保留停止状态，不换账号/代理或删历史反复访问。若要每天无人值守执行，需单独部署固定采集服务：安装Python Playwright、使用本机已有浏览器、为当前项目建立独立profile并由用户正常登录，再用一条搜索和一篇详情验收。当前只有离线状态检查证据（缺少Playwright），没有后台服务成功记录。X、微博、雪球和公众号各自验证，不推定共享小红书登录状态。

## 进入日报及遗漏反馈

按平台分别保存查询、排序/选样方式、帖子链接、作者身份核验、发布时间、采集时间、正文范围和失败原因。热门排序、推荐页与固定账号不是同一种覆盖方式；完成主题检索不能代替账号时间线和分页检查。

对于发现的重要新闻，追原始发布、区分原创与转述、以事件去重。仅有观点时明确归属，不提升为事实。社交热度不直接当作重要性或真实性；实际读取失败、登录受限、空页面和明确没有合格新增分开登记。

遗漏反馈先检查来源池、账号/主题词、任务是否执行、正文可达性、筛选和时间窗口。缺账号补信源；缺词补词表；访问失败重试并保留缺口；已发现而误删则修筛选规则。所有修改仍通过`topic update`管理版本与试检，不绕过`accept/finish`门槛。
