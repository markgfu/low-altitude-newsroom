# 主题目录

每个主题使用一个`<id>/topic.json`，包含范围、信源、词组、任务、栏目、核验规则和版本变更说明。

- `lowalt`：从现有低空清单迁移，保留全部ID与历史说明。原Excel继续保留为版本快照。
- ESG、算力金融及任意主题使用`topic init`新建；初始化建议在`templates/`，不冒充已验证入口。

业务字段集中在`config`；先`topic export`取得编辑副本，再`topic update`保存版本。不要直接手改正式配置或哈希。每次配置变更须重新试检。

本机试检、反馈、采集截止与事件历史保存在被Git忽略的`runtime/<id>/`，输出在`output/<id>/<date>/`。新使用者不会继承别人的“已完成”状态。

完整操作见[多主题流程](../docs/multi_topic.md)。
