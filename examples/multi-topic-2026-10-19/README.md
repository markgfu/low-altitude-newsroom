# 低空经济与算力金融：双主题范例

编制日期：2026-10-19。按用户要求制作的真实新闻选编示范，每个主题4条，展示同一编辑流程如何适配不同产业。不是全量采集日报，不作为主题试检验收、成功采集截止或去重历史；未执行 `topic accept` 或 `topic finish`。选用2026-10-12至18日发布的材料，正文保留真实日期，不能理解为全部发生于19日。

## 阅读与编辑

| 主题 | 可编辑正文 | 浏览器阅读版 |
| --- | --- | --- |
| 低空经济 | [lowalt.md](lowalt.md) | [lowalt.html](lowalt.html) |
| 算力金融 | [compute-finance.md](compute-finance.md) | [compute-finance.html](compute-finance.html) |

HTML由仓库自带渲染器生成，正文与Markdown一致，来源链接可点击。采用纯文字版：本次没有完成可复用新闻图片的许可核验，不添加素材图。文件供阅读和审稿，不代表已经在公众号发布。

## 先确定范围与信源

低空经济选取产品试验、产业赛事和采购机会。算力金融范围为算力芯片及AI基础设施企业股权融资、GPU资源租赁与数据中心项目融资；不将所有AI产品新闻或金融机构数字化项目自动纳入。租赁合同归资源获取和现金支出，不归融资到账。

本表是本次选编的公开来源清单，不覆盖生产环境完整信源，也不冒充已验收的新主题配置。readable仅表示本次样本已读。

| 来源 | 样本入口 | 本次访问状态与归属 |
| --- | --- | --- |
| 新华网 | [云哨试飞](https://www.xinhuanet.com/photo/20261016/1cc186e393264e5680f17beee049f65d/c.html) | readable；读现场图文文字部分，未使用图片 |
| 青岛日报社／观海新闻 | [青岛新闻网刊载](https://news.qingdaonews.com/wap/2026-10/18/content_23761747.htm) | readable；有记者署名的赛事报道 |
| 中国政府采购网 | [实训设备招标](https://www.ccgp.gov.cn/cggg/dfgg/gkzb/202610/t20261017_27513542.htm) | readable；读公告及需求表，未读取文件集附件 |
| 湖北省成套招标 | [黄石采购更正](https://www.hubeibidding.com/view/53348.html) | readable；读代理机构更正原文，未据此推定文件获取期延长 |
| 财联社创投通 | [投融资周报](https://www.cls.cn/detail/2507617) | readable；读蓝芯算力对应段落，属媒体报道 |
| 新京报贝壳财经 | [无问芯穹融资](https://www.bjnews.com.cn/detail/1791773724129744.html) | readable；读记者报道，未取得融资法律文件或到账凭证 |
| 紫荆网／中国基金报 | [并行科技GPU租赁](https://zijing.com.cn/web/article/1560384522714021889/web/content_1560384522714021889.html) | readable；转载中国基金报消息，审批状态截至10月15日；不冒称读到交易所公告 |
| DayOne／美通社 | [马来西亚融资扩容](https://en.prnasia.com/releases/apac/dayone-upsizes-malaysia-financing-to-us-7-2-billion-total-billings-surpass-1gw-and-bookings-reach-2-3gw-551659.shtml) | readable；企业发布的英文新闻稿，保留企业披露归属 |

## 再设置检索词

以下是根据选编范围整理的可复用词组建议，不是已执行任务清单。正式启用时应通过 `topic init/export/update` 登记来源、词组及任务，再执行试检；不能复制本说明作为试检完成证据。

| 主题 | 产业对象词 | 事件词 | 可用查询示例 |
| --- | --- | --- | --- |
| 低空经济 | 低空经济、无人机、浮空器、eVTOL、飞行汽车 | 首飞、取证、运营、招标、更正、赛事 | `无人机 采购 更正`；`浮空器 首飞` |
| 算力金融 | 算力、智算中心、数据中心、GPU、AI infrastructure、data center | 融资、增资、银团贷款、租赁、financing、syndicated loan | `数据中心 银团贷款`；`GPU 算力 租赁`；`data center syndicated financing` |

来源有明确对象后，增加公司名或项目名精检。本次实际执行过的精检包括 `"并行科技" "2.3328" "2026"`；随后打开紫荆网正文核对租期、金额和审批状态。其他采用消息均逐条打开上表具体页面核验；已知链接重读不登记成新发现。早期广搜及候选筛选不据此宣称主题全覆盖。

## 金额、状态与日期核验

| 条目 | 保留的口径或边界 |
| --- | --- |
| 云哨试飞 | 试验10月13—16日；首飞系列试验不能写成长期商业运行 |
| 青岛赛事 | 发布18日、开幕17日、赛期至19日；不写成仍开放报名 |
| 山东采购 | 73万元是包1整体预算和限价；文件获取与投标截止不同；未阅读附件不宣称掌握全部技术条件 |
| 黄石更正 | 原响应截止10月19日改为11月4日09时；设备和起降点为履约承诺；不推定文件获取期延长 |
| 蓝芯算力 | 近20亿元为B轮系列合计；文章未列明每笔交割时间 |
| 无问芯穹 | 本轮23亿元、历来累计43亿元；历来投资者名单不等于本轮名单 |
| 并行科技 | 三年租赁上限2.3328亿元；报道时待股东大会审议；未将此采购支出记成融资 |
| DayOne | 约72亿美元为扩容后总额；旧融资基数约35亿美元；未见本轮逐笔提款数据 |

格式检查只检查结构，新闻事实依据上述实际读取内容。没有取得交易文件或到账证明的媒体融资报道，保留媒体归属，不写成独立审计结论。

## 未采用及反馈处理

香港低空经济国际服务中心、Token贷及吉大正元公告等候选的部分原文入口读取失败，未仅凭摘要纳入本组范例。并行科技公告承载页读取不稳定，改用已读媒体消息并明确出处，不沿用此前稿件中未经本次核实的会计处理细节。

收到重要遗漏反馈时，先保留用户给出的原文与重要性，再比对实际检索记录：来源不在清单且无开放搜索命中，才评估补源；来源已覆盖而词组不能召回，才评估增词。读取失败、没有执行、筛选误判和时间窗口问题分别记录，不机械增词。配置修订后需重查遗漏样本及同类材料，并记录新增噪声；证据不足保持待查。本次未模拟真实用户反馈或伪造已关闭问题。

## 重现排版

在仓库根目录设置 `PYTHONPATH=src` 后执行：

```text
python -m lowalt_newsroom check examples/multi-topic-2026-10-19/lowalt.md
python -m lowalt_newsroom check examples/multi-topic-2026-10-19/compute-finance.md
python -m lowalt_newsroom render examples/multi-topic-2026-10-19/lowalt.md --output examples/multi-topic-2026-10-19/lowalt.html
python -m lowalt_newsroom render examples/multi-topic-2026-10-19/compute-finance.md --output examples/multi-topic-2026-10-19/compute-finance.html
```
