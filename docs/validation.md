# 本地验证记录

日期：2026-10-19。环境：Windows、Python 3.12。

| 检查 | 结果与边界 |
|---|---|
| 单元测试 | 15项通过：日期频率、计划/执行区分、说明词过滤、缺口记录、HTTP失败、RSS/Atom日期、原生加粗、图片目录边界及六条示例稿 |
| 清单读取 | 117个来源、240项任务、204个对象；读取全部行，包含Excel旧筛选范围之外的新增项 |
| 周一计划 | 187项到期，所有查询仍未执行；其余不在本轮计划。新增任务未倒填到历史采集成果 |
| 稿件格式 | 示例6条，无内部标签及结构错误 |
| HTML生成 | 原生strong加粗、1张图片内嵌；解码后图片SHA256为50dc5ff83406f30acf8ce032cd502976af6f1a7ed96a668c97183c9e2ad48bec，与原PNG一致 |
| RSS实测 | 亿航订阅入口当次返回HTTP403，结果记录为读取失败、0条已解析；不能据此说没有新消息，也不代表其他入口均失败 |
| 暂存文件检查 | 未检出规则所覆盖的GitHub令牌、私钥、临时签名URL或禁止提交的运行文件；这不是全部秘密类型的形式化保证 |

GitHub Actions已在公开仓库完成Windows/Linux检查，两项任务均成功；包括15项单元测试、待提交文件检查、清单读取和示例稿格式检查。验证提交为`8a6b3bc6f0c64ab39910fe52e16624ed50994fb4`，见[运行记录](https://github.com/markgfu/low-altitude-newsroom/actions/runs/39189570251)。没有在本次进行全站分页采集、公众号接入或微信后台发布。示例新闻仍需人工最终审核。

Actions版本依据官方[setup-python说明](https://github.com/actions/setup-python/blob/main/README.md)及[checkout说明](https://github.com/actions/checkout/blob/main/README.md)核对，使用v7；配置只申请contents: read权限。

本地测试中系统临时目录不可写，测试临时文件改在仓库忽略的runtime/test-temp中创建，路径检查保证其位于仓库内。未修改系统权限或其他目录。
