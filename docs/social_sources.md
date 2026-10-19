# 社交媒体信源：叙事雷达方式的复用

社交平台纳入各主题的信源和日检任务。它们能提供企业首发、行业线索、现场记录与讨论；取得帖子不等于事实已经核实。企业自己的发布可以作为其声明的原始来源，政策、融资完成、适航批准等结论仍追发文机构或公告。

## 已核对的原项目实现

本次只读核对了本机叙事雷达的 `probe_social.py`、`inspect_social.py`、`export_social_probe.py`、README及试采记录。其2026-10-11试采采用公开详情链接、匿名GET、HTML可见文本/明确的页面数据结构、时间和SHA-256留档：15次请求取得雪球3条、微博2条正文，小红书0条。微博年份未确认时保留空值，搜索壳和验证页未计作正文。原项目的X实采成功记录未找到。

当前信源清单另有WeRSS静态评估及XML兼容历史说明，不能据此断言已经部署了可用的公众号采集服务。本次没有把旧项目的ETF词表、原始帖子或登录资料复制进公开仓库。

## 当前接入能力

| 平台 | 发现与获取方式 | 当前边界 |
|---|---|---|
| X | 主题检索、明确账号/帖子；实际API导出或浏览器可见正文导入 | 本仓库未部署X API客户端；未取得授权接口样本，不声称全量抓取 |
| 小红书 | 主题检索、笔记永久链接；登录后实际可见正文导入 | 不将空搜索壳当作无更新；本次浏览器连接超时，未观察到平台页面 |
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

## 进入日报及遗漏反馈

按平台分别保存查询、排序/选样方式、帖子链接、作者身份核验、发布时间、采集时间、正文范围和失败原因。热门排序、推荐页与固定账号不是同一种覆盖方式；完成主题检索不能代替账号时间线和分页检查。

对于发现的重要新闻，追原始发布、区分原创与转述、以事件去重。仅有观点时明确归属，不提升为事实。社交热度不直接当作重要性或真实性；实际读取失败、登录受限、空页面和明确没有合格新增分开登记。

遗漏反馈先检查来源池、账号/主题词、任务是否执行、正文可达性、筛选和时间窗口。缺账号补信源；缺词补词表；访问失败重试并保留缺口；已发现而误删则修筛选规则。所有修改仍通过`topic update`管理版本与试检，不绕过`accept/finish`门槛。
