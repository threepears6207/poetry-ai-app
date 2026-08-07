# 儿童古诗候选库来源

候选范围以公开的“小学古诗词75首”目录为筛选基线，原文从 GitHub 开源项目 `chinese-poetry/chinese-poetry` 的《千家诗》和《唐诗三百首》数据中匹配。

- 开源仓库：https://github.com/chinese-poetry/chinese-poetry
- 许可证：MIT
- 固定版本：`b8594f81a89752241442f2ce267d6f66f96704ee`
- 使用文件：`蒙学/qianjiashi.json`、`蒙学/tangshisanbaishou.json`
- 补充仓库：https://github.com/dudulittle/ChinesePoetryTreasure-troveKnowledgeBase
- 补充仓库许可证：MIT
- 补充仓库固定版本：`b34b4388cf8d3981571e73a418e3ff24bef38f6b`
- 篇目参考：https://geo.bnu.edu.cn/docs/2019-05/20190507204624528014.pdf
- 常用字难度参考：https://gist.github.com/jjgod/1432945 （固定版本 `90cd5fe7f3fc112823f7a5542632040f641ca487`）

只使用古诗原文、题目、作者和朝代。现代译文、赏析和教学文案不从外部资料复制，后续由项目自行编写并人工校对。

补充仓库中存在少量题目与正文错配，因此生成器只接受“题目与首句同时匹配”的记录；不能通过严格校验的内容不会进入候选库。

生成结果属于候选数据，不会自动覆盖 `backend/data/poems.json`。年龄、难度和标签为初步标注，正式导入数据库前需要人工复核。

最终150首的筛选不按战争、死亡、爱情、宫苑、饮酒等题材排除作品，只依据篇幅、句式、常用字覆盖和生僻字数量评估3-7岁儿童的语言理解难度。
# 300 首诗库扩充（2026-08-07）

- 选篇依据：教育部《义务教育语文课程标准（2022年版）》及人民教育出版社《小学生必备古诗词112首》，优先保留教材常见篇目、儿童易理解的自然与生活主题短诗。
- 正文来源：`chinese-poetry/chinese-poetry` 仓库固定提交 `b8594f81a89752241442f2ce267d6f66f96704ee`，优先使用《千家诗》和唐诗三百首语料，不足部分从常见作者的五言、七言短篇补齐。
- 质量口径：两个候选批次合计恰好 300 首；按规范化正文哈希去重；ID 连续为 `poem_001`—`poem_300`；译文及标签通过现有导入质量门禁。
- 构建与审计：`scripts/expand_catalog_to_300.py`；结果见 `generated/catalog_300_expansion_report.json`。
