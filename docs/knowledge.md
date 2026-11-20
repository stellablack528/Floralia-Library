# 花与书页知识库

资料馆收录 25 张中英双语书页。17 张对应 Flower17 类别，其余 8 张对应 Bloom 25 的新增类别。植物档案记录科属、可见特征、生境和花期。阅读栏收录文学典故与用物史，每条附作者或机构、出处位置、链接和摘要。[25 类实验报告](bloom25.md)

## 数据与书页

| 文件 | 用途 |
| --- | --- |
| `knowledge/classes.json` | Flower17 类别编号、中英文显示名与稳定代号。 |
| `knowledge/botanical_profiles.json` | 以同一代号索引的代表植物档案。学名和花期的范围由各条目说明。 |
| `knowledge/cultural_sources.json` | 以 `class_key` 关联的文学、艺术和民俗记录，一种花可以有多条。 |
| `knowledge/extra_folios.json` | 独立书页的花名、别名、植物档案和文化出处，以书页代号索引。 |
| `knowledge/folio_english.json` | 英文植物档案和对应的阅读摘要。 |
| `knowledge/flower_language.json` | 每种花的一句中英花语、出处位置和必要的名称或品种说明。 |
| `src/sync_web_cards.py` | 按已裁定的类别生成网页数据，同时核对中英文记录、出处位置和链接。 |

在项目根目录运行 `python src/sync_web_cards.py` 即可更新书页数据。资料馆支持按花名、学名、作品名和文化关键词搜索。花卉类别保留数据集的原始含义，书页明确标注“代表植物”。例如番红花页展示 *Crocus vernus*，文化栏把剑桥大学的香料史明确关联到同属的 *C. sativus*。文学及民俗摘要注明作品或传统的语境。

扩展资料馆时，在 `extra_folios.json` 和 `folio_english.json` 增加同一书页代号的内容。识别范围由本机已加载的模型确定。目前 SQLite 文献摘录和审核覆盖 Flower17 的 17 个类别。

## 资料收录裁定

1. **文学典故**收录中国和西方的诗文、小说、戏剧、神话或有来源的民间故事。植物须在原文或故事中有明确作用。记录作品、作者或记录机构，以及页码、章节或段落位置。将原文和项目摘要分开，按作品的具体语境解释。
2. **用物史**收录有文献记载的具体用途，例如食物、香料、染料、茶饮或日常工艺。写清使用的植物部位、用途和出处。有同名花或近缘种时，明确来源指的是哪一种。
3. **发布前**核对来源能否支撑摘要，并确认植物对应关系。资料不足时标记「待补充」。画作、图版、园徽、单独的花语标签和仅描写活动的节日习俗不进入阅读栏。MinerU 摘录和译文在审核区保存，成为书页条目前也需要按以上标准裁定。

| 候选资料 | 裁定与依据 |
| --- | --- |
| 林逋《山园小梅》 | 收录为文学典故。第一首颔联可核对梅枝疏影和梅香的写法。 |
| 青梅调味、蓝铃花旧书装订、桂花为茶和糖果添香 | 收录为用物史。来源分别说明使用的是梅果、蓝铃花球茎、桂花雄花。 |
| 番红花书页的藏红花香料 | 收录为用物史。香料来自 *C. sativus* 的柱头，植物档案的代表种是 *C. vernus*。 |
| 梅花园徽和馆藏画作 | 从阅读栏撤下。出处主要说明标识设计或艺术表现。 |

## 结构参考

- 参考 Plantfolio 将来源数据与生成供界面使用的数据分开，并提供校验脚本的做法。[Plantfolio GitHub 仓库](https://github.com/Luminoid/plantfolio-common-plants)
- 参考 FloraaDB 将学名、俗名和来源记录分别建模的做法。[FloraaDB 数据字典](https://github.com/FloraaDB/houseplants-botanical-floradb/blob/main/DATA_DICTIONARY.md)

### 相关项目论文

| 论文 | 读哪里 | 对本项目有什么用 |
| --- | --- | --- |
| Borsch 等，2020，《World Flora Online》项目论文，[TAXON 原文](https://doi.org/10.1002/tax.12373) | 摘要和引言中的 *Taxonomic Backbone* 与 *Content* | 先用学名指清楚讨论的是哪种植物，再挂接描述、分布、图像和出处。书页用稳定代号关联这些材料，俗名用于搜索。例如「木犀」能找到桂花，学名字段保留 *Osmanthus fragrans*。 |
| Joly 等，2014，《Interactive plant identification based on social image data》，[IRD 论文摘要及 DOI](https://www.documentation.ird.fr/hor/PAR00012198) | 摘要中的 Pl@ntNet 照片识别和观察记录设计 | 一次观察可以包含花、叶等不同部位的照片。书页先写能观察到的特征，例如荷叶的叶柄位置和紫藤的下垂花序。 |
| Garcin 等，2021，《Pl@ntNet-300K》，[NeurIPS 论文](https://datasets-benchmarks-proceedings.neurips.cc/paper_files/paper/2021/hash/7e7757b1e12abcb736ab9a754ffb617a-Abstract-round2.html) | 摘要和物种分布图 | 论文的首版数据含 1,081 个物种和 306,146 张照片。部分类别外观相近，各类样本量差异也很大。今后扩展拍照识别时，可参考论文按类别核对样本量和容易混淆的类别，再用独立实拍照片评估。 |

这批书页用邱园数据库核对学名与科属，用大学推广资料核对可见特征和花期，并在文学栏标出原文位置。读完《桃花源记》对溪岸桃林的描写，可以回到植物档案查看普通桃的形态。

每条档案链接到实际参考的园艺机构、博物馆、原典或机构资料。书页的「原文摘录」保留出处里的措辞，「中文整理」由项目根据上下文撰写和核对。MinerU 用于扫描文字识别和版面、页码提取。应用直接读取已整理好的中文字段。文学记录中的「名字灵感」是项目从作品意象延伸出的取名提议。核对日期记录在文化条目里。

用物史来源示例。[故宫博物院](https://www.dpm.org.cn/explode/others/259793.html) · [英国国民信托](https://www.nationaltrust.org.uk/discover/nature/trees-plants/a-guide-to-bluebells-in-the-uk) · [Wellcome Collection](https://wellcomecollection.org/works/a6bjqw89)

## 花语原书核对档案

每张书页的标题下方展示一句中英花语。「花语出处」可展开查看书名、定位和适用范围。网页的短句是对所选寓意的转述。一种花在不同传统中的寓意可能不同。十九世纪花语书若只写通名或限定花色，条目保留这项说明。花语位于书页开头，文学典故与用物史仍按各自的收录标准整理。

以下是先前核对 Kate Greenaway《Language of Flowers》（1884）的档案，供追溯 OCR 页码。每条保留原书限定，例如红色郁金香，或矮秆和高秆向日葵。[馆藏目录](https://www.biodiversitylibrary.org/item/269449) · [公版扫描 PDF](https://archive.org/download/languageflowers00gree/languageflowers00gree.pdf)

| 花卉 | 印刷页 | PDF 页 | 原书所载 |
| --- | ---: | ---: | --- |
| 鸢尾 | 23 | 27 | 消息 |
| 雪滴花 | 39 | 43 | 希望 |
| 向日葵 | 39 | 43 | 矮秆为爱慕，高秆为傲慢 |
| 红色郁金香 | 41 | 45 | 爱的告白 |

本机将扫描件放在 `documents/sources/Greenaway-1884-Language-of-Flowers.pdf`。用下面的命令分别解析 PDF 第 27、43、45 页，再对照扫描件核对文字和花语的对应行。

```powershell
foreach ($page in 27, 43, 45) {
    .\.venv-mineru\Scripts\python.exe src\parse_document.py documents\sources\Greenaway-1884-Language-of-Flowers.pdf --tier basic --device cpu --page $page
}
```

## 与毕业设计大纲的关系

网页知识库是应用交付的一部分。模型路线依次为迁移学习基线及错误分析、蒸馏方法对照、C++ 并发性能实验、真实推理接入和毕业展示。MinerU 路线已完成本地解析验证，并可将解析记录登记到 SQLite。数据表、CRUD 接口和运行指令见 [数据库设计](database.md)。Qt 文献馆、知识自动提取和网页书页联动留待各自的实现阶段。
