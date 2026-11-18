# Flower17 花卉知识库

2026 年 11 月 18 日整理。17 个模型类别都有一份代表植物档案和至少一条带出处的文化记录。植物档案记录科属、可见特征、生境和花期。文化记录包括作品或传统、作者或机构、来源链接、章节或段落定位、摘要及关联范围。

## 数据与书页

| 文件 | 用途 |
| --- | --- |
| `knowledge/classes.json` | Flower17 类别编号、中英文显示名与稳定代号。 |
| `knowledge/botanical_profiles.json` | 以同一代号索引的代表植物档案。学名和花期的范围由各条目说明。 |
| `knowledge/cultural_sources.json` | 以 `class_key` 关联的文学、艺术和民俗记录，一种花可以有多条。 |
| `src/sync_web_cards.py` | 校验 17 类覆盖、必填字段和来源链接格式，再生成网页的数据。 |

在项目根目录运行 `python src/sync_web_cards.py` 即可更新书页数据。资料馆支持按花名、学名、作品名和文化关键词搜索。花卉类别保留数据集的原始含义，书页明确标注“代表植物”。例如番红花页展示 *Crocus vernus*，文化栏把剑桥大学的香料史明确关联到同属的 *C. sativus*。文学及民俗摘要注明作品或传统的语境。

## 结构参考

- 参考 Plantfolio 将来源数据与生成供界面使用的数据分开，并提供校验脚本的做法。[Plantfolio GitHub 仓库](https://github.com/Luminoid/plantfolio-common-plants)
- 参考 FloraaDB 将学名、俗名和来源记录分别建模的做法。[FloraaDB 数据字典](https://github.com/FloraaDB/houseplants-botanical-floradb/blob/main/DATA_DICTIONARY.md)

每条档案链接到实际参考的园艺机构、博物馆、原典或机构资料。中文内容为项目整理的摘要。核对日期记录在文化条目里。

## 与毕业设计大纲的关系

网页知识库是应用交付的一部分。模型路线依次为迁移学习基线及错误分析、蒸馏方法对照、C++ 并发性能实验、真实推理接入和毕业展示。MinerU 路线已完成本地解析验证，并可将解析记录登记到 SQLite。数据表、CRUD 接口和运行指令见 [数据库设计](database.md)。Qt 文献馆、知识自动提取和网页书页联动留待各自的实现阶段。
