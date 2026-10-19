# 多主题配置与反馈流程

从项目根目录执行，Windows先设置`$env:PYTHONPATH = (Resolve-Path .\src).Path`，macOS/Linux使用`export PYTHONPATH="$PWD/src"`。安装后也可使用`newsroom`，原`lowalt-news`命令继续保留。需要Python 3.11+，运行工具只用标准库。

## 1. 先明确主题，再建信源

```powershell
python -m lowalt_newsroom topic init --id esg --name "ESG" --preset esg
python -m lowalt_newsroom topic init --id compute-finance --name "算力金融" --preset compute-finance
python -m lowalt_newsroom topic init --id custom --name "我的主题" --scope "关注对象、地区及范围"
```

主题ID只用小写英文、数字、短横线或下划线，名称可用中文。两个预设提供范围、信源类别、词组和专业核验建议，未伪造可用入口；`suggestions`不参与任务生成。Agent应先定位真实信源并读取样本，再选用建议词组建立任务，不能跳过配置直接写新闻。

主题配置在`topics/<id>/topic.json`。其中`config`是业务配置，外层版本、哈希与changes由命令管理，不直接编辑。导出可编辑副本：

```powershell
python -m lowalt_newsroom topic export --id esg --output runtime/esg/config-edit.json
```

依次填写范围、信源、词表和任务。可以分多次保存未完成配置，每次保留版本：

```powershell
python -m lowalt_newsroom topic update --id esg --config runtime/esg/config-edit.json --expected-version 1 --reason "定位并登记首批信源"
python -m lowalt_newsroom topic check --id esg
```

保存后版本递增；下次以新版本号保存。冲突时重新导出并合并，不能删掉版本检查。直接改正式配置会触发哈希错误；不要手改哈希。`check`返回0表示本机当前版本已试检，1表示尚需配置或试检，2表示命令/数据错误。

## 2. 配置字段

| 字段 | 用途 |
|---|---|
| id/name/scope/audience | 唯一ID、名称、纳入范围与读者 |
| regions/languages/exclude | 地区、语言、排除范围；Agent据此判断与扩展任务 |
| sections/editorial_checks | 栏目顺序与本主题核验重点 |
| window | initial_hours首次窗口；lookback_days新闻回看；academic_days学术回看 |
| sources | 信源对象数组：id、name、type、entry、method、status、verification_note |
| keywords | 词组数组：id、label（可选）、terms |
| tasks | 任务数组：id、keyword_ids、source_ids、queries、frequency、enabled、verification |

`status`取candidate（候选）、readable（已读样本）、limited（访问有限）、failed（本次失败）。readable须有实际核验说明，不表示长期稳定接入。entry可为真实URL或已知数据库/官方栏目定位说明；未找到入口应如实记录。候选源可以保留，但本机试检必须取得实际原文证据才能验收。

来源和任务可多对多关联。开放搜索任务允许`source_ids: []`，用于发现清单外的新来源；整个主题仍须先有信源清单。来源未关联启用任务会提示，不把列出信源数量当作实际覆盖。

以下为**结构示例**，example.org不是实际信源，不可用作验收记录：

```json
{
  "sources": [
    {"id": "S01", "name": "待替换的真实机构", "type": "官方", "entry": "https://example.org/news", "method": "原站列表与开放搜索", "status": "candidate"}
  ],
  "keywords": [
    {"id": "K01", "label": "产业对象", "terms": ["智算中心", "数据中心", "AI infrastructure"]}
  ],
  "tasks": [
    {"id": "T01", "keyword_ids": ["K01"], "source_ids": ["S01"], "queries": ["{term} 融资", "{term} financing"], "frequency": "每日", "enabled": true, "verification": "读融资公告，区分投资总额、授信、实际融资与币种"}
  ]
}
```

将这些字段合并进导出的完整配置，不要用片段覆盖整个配置。`{term}`只支持这个占位符，按关联词组的每个词分别展开、去重，新增词下一次生成计划即生效。也可填固定检索式或真实原站入口。固定检索式不会随词表自动改写，改词时须审查对应任务。频率支持每日、每周1—7、线索触发、按需、未启用；后三项不自动到期，需执行时修改频率并重新生成计划。

scope、地区、语言及排除条件是编辑要求，CLI不把它们偷偷拼入查询；Agent须检查最终queries确实覆盖各要求。海外与英文条目按主题需要设置，不能只列在范围里而不设任务。

## 3. 实际试检，再生成日报

```powershell
python -m lowalt_newsroom topic plan --id esg --batch first-trial --trial
```

默认截止为当前北京时间，也可传`--cutoff 2026-10-19T08:30:00+08:00`。输出位于`runtime/esg/runs/first-trial/plan.json`，含配置快照、版本、哈希、展开查询和窗口。规划不是执行，所有到期任务初始为未执行。

编辑或联网Agent逐条执行queries，保留搜索结果与原文。每条实际查询用旧record命令写入新主题计划：

```powershell
python -m lowalt_newsroom record --plan runtime/esg/runs/first-trial/plan.json --task-id T01 --query "实际执行的查询" --evidence "https://example.org/actual-search" --original "https://example.org/actual-original" --status "已检有新增" --note "替换为真实核验范围、日期检查与缺口"
```

上述链接是语法示例，必须替换为当次真实记录。只有线索用“已发现待核”；失败用“读取失败”，未知发现数不填。无合格新增须在完成实际检查后记录“已检无合格新增”，不得因页面读取失败填零。核查后将当前配置的所有到期任务、全部展开查询完成，再验收：

```powershell
python -m lowalt_newsroom topic accept --id esg --plan runtime/esg/runs/first-trial/plan.json --note "说明实际读取样本、范围覆盖、相关性和无关结果检查"
python -m lowalt_newsroom topic plan --id esg --batch daily-001
```

试检至少需要一篇已读原文，可以在主题回看窗口中选取；不能把无结果或只搜到摘要当作来源可用。首次建议建立适量核心任务，逐步扩展；新任务或词表修订会使旧试检失效。验收仅覆盖本批次到期任务，不宣称其他每周任务已经执行。

正式计划执行完成后，依据`common_editorial_rules.md`和主题规则编写待审稿；先条目、后今日总结与标题。输出到`output/<id>/<date>/`，用`check`与`render`检查及排版，内部附记单独保存。命令本身不自动联网搜索或生成新闻正文。

## 4. 有遗漏，就定位原因并修正

```powershell
python -m lowalt_newsroom topic feedback --id esg --url "https://example.org/missed-news" --note "替换为真实遗漏新闻及其重要性"
python -m lowalt_newsroom topic status --id esg
```

产生本机反馈ID，如F0001，初始为unknown/open。先检查：是否属于范围、是否已发布、是否在当期窗口；再查来源是否有入口、任务是否实际执行、查询是否命中、读取是否成功、候选是否误筛。原因可以并存，选择主要原因并在说明中记录其他原因。

| cause | 处理 |
|---|---|
| source | 补来源及关联任务，核验入口 |
| keyword | 补别名、主体、英文词或模板，检查是否进入实际queries |
| execution | 修复读取或执行安排并重试；临时失败无需无意义改配置 |
| filter | 调整scope、exclude、editorial_checks及筛选要求，回查误筛候选 |
| time_window | 调整window或相关日期核验规则 |
| unknown | 证据不足，保持open |
| out_of_scope | 读原文后确认不在范围，附证据dismiss |

配置问题导出编辑后保存，并关联反馈：

```powershell
python -m lowalt_newsroom topic update --id esg --config runtime/esg/config-edit.json --expected-version 2 --reason "根据遗漏反馈补充披露术语及任务" --feedback F0001
python -m lowalt_newsroom topic plan --id esg --batch feedback-f0001 --trial
```

实际重检遗漏新闻和同类样本，登记真实查询；同一原文的URL应与反馈登记URL一致，转载或重定向需先核对原文。检查新增无关结果，必要时继续修改。通过accept后关闭：

```powershell
python -m lowalt_newsroom topic resolve --id esg --feedback F0001 --cause keyword --evidence "https://example.org/missed-news" --note "替换为诊断依据、具体修正和回查结果"
```

关闭时检查修订关联、当前版本试检、反馈后验收时间及遗漏原文读取记录。execution允许不改配置、在反馈后重新试检；out_of_scope需证据但不要求改配置。每个反馈是本机记录，不随Git发布，公开变更理由勿含私人内容。

## 5. 成功交接与历史隔离

把实际采用事件写入独立JSON数组，每项至少有`event_id`和`source_url`，来源须在该计划已读原文和正文中出现。事件键例如`主体:项目:融资完成:2026-10-19`；同一项目新阶段使用新的事件键，并另保留项目关联字段。

```powershell
python -m lowalt_newsroom topic finish --id esg --plan runtime/esg/runs/daily-001/plan.json --draft output/esg/2026-10-19/daily.md --events runtime/esg/events-daily-001.json
```

全部到期查询完成才允许成功交接。若实际无合格新增，事件数组为`[]`并省略`--draft`。存在未执行、待核或读取失败时继续保留缺口，不推进成功截止；可以交付明确标注覆盖缺口的待审稿，但不调用finish假记成功。CLI格式验证不替代编辑审核，交接后也不自动发布。

下一批计划读取该主题最近成功截止及已采用事件。不同主题、试检和失败批次不混用历史。批次不能覆盖或重复交接，早先并行生成的旧窗口计划不能覆盖更新的成功截止。每个主题串行写配置与状态；没有文件锁，不支持同一主题多进程并发编辑。

## 6. 低空迁移与兼容

仓库预置`topics/lowalt/topic.json`，保留Excel的全部信源、任务ID、原记录及覆盖对象。源状态保留在legacy，迁移后的candidate表示尚未在当前流程重新验收，不否认此前读取记录。旧Excel、旧命令、示例和历史目录保持可用。

若在没有lowalt主题的旧副本中迁移，可执行`topic import-lowalt --id lowalt`；已有主题会拒绝覆盖。迁移后多主题流程以JSON为运行配置，Excel是原始版本快照；较新主表须比对差异，用update合并并保留原ID与历史。不要在两边各自修改后假定自动同步。

原`plan --checklist`等命令仅供旧低空流程兼容，新主题必须走topic命令。旧runtime不会自动成为新主题成功基线；确需迁移时先审核证据与截止，不能把示例或其他人的历史导入。
