# 花与书页知识库

资料馆收录 25 张书页。17 张对应 Flower17 模型类别。独立查阅书页涵盖山茶花、绣球花、梅花、桃花、荷花、桂花、牡丹和紫藤。植物档案记录科属、可见特征、生境和花期。文化记录包括作品或传统、作者或机构、来源链接、章节或段落定位、摘要及关联范围。

## 数据与书页

| 文件 | 用途 |
| --- | --- |
| `knowledge/classes.json` | Flower17 类别编号、中英文显示名与稳定代号。 |
| `knowledge/botanical_profiles.json` | 以同一代号索引的代表植物档案。学名和花期的范围由各条目说明。 |
| `knowledge/cultural_sources.json` | 以 `class_key` 关联的文学、艺术和民俗记录，一种花可以有多条。 |
| `knowledge/extra_folios.json` | 独立书页的花名、别名、植物档案和文化出处，以书页代号索引。 |
| `knowledge/classic_images.json` | 以书页代号关联经典图像、馆藏编号、原图和使用许可。 |
| `src/sync_web_cards.py` | 校验 17 类覆盖、书页代号、必填字段和来源链接格式，再生成网页的数据。 |

在项目根目录运行 `python src/sync_web_cards.py` 即可更新书页数据。资料馆支持按花名、学名、作品名和文化关键词搜索。花卉类别保留数据集的原始含义，书页明确标注“代表植物”。例如番红花页展示 *Crocus vernus*，文化栏把剑桥大学的香料史明确关联到同属的 *C. sativus*。文学及民俗摘要注明作品或传统的语境。

扩展资料馆时，在 `extra_folios.json` 增加新的书页代号和有出处的资料。经典图像有明确使用许可时，可在 `classic_images.json` 登记并保存本地 WebP。独立书页可以搜索、浏览和收藏，页面提示其拍照识别状态。目前 SQLite 文献摘录和审核仍覆盖 Flower17 的 17 个模型类别。

## 结构参考

- 参考 Plantfolio 将来源数据与生成供界面使用的数据分开，并提供校验脚本的做法。[Plantfolio GitHub 仓库](https://github.com/Luminoid/plantfolio-common-plants)
- 参考 FloraaDB 将学名、俗名和来源记录分别建模的做法。[FloraaDB 数据字典](https://github.com/FloraaDB/houseplants-botanical-floradb/blob/main/DATA_DICTIONARY.md)

### 相关项目论文

| 论文 | 读哪里 | 对本项目有什么用 |
| --- | --- | --- |
| Borsch 等，2020，《World Flora Online》项目论文，[TAXON 原文](https://doi.org/10.1002/tax.12373) | 摘要和引言中的 *Taxonomic Backbone* 与 *Content* | 先用学名指清楚讨论的是哪种植物，再挂接描述、分布、图像和出处。书页用稳定代号关联这些材料，俗名用于搜索。例如「木犀」能找到桂花，学名字段保留 *Osmanthus fragrans*。 |
| Joly 等，2014，《Interactive plant identification based on social image data》，[IRD 论文摘要及 DOI](https://www.documentation.ird.fr/hor/PAR00012198) | 摘要中的 Pl@ntNet 照片识别和观察记录设计 | 一次观察可以包含花、叶等不同部位的照片。书页先写能观察到的特征，例如荷叶的叶柄位置和紫藤的下垂花序。馆藏作品供文化阅读，实地观察照片用于辨识。 |
| Garcin 等，2021，《Pl@ntNet-300K》，[NeurIPS 论文](https://datasets-benchmarks-proceedings.neurips.cc/paper_files/paper/2021/hash/7e7757b1e12abcb736ab9a754ffb617a-Abstract-round2.html) | 摘要和物种分布图 | 论文的首版数据含 1,081 个物种和 306,146 张照片。部分类别外观相近，各类样本量差异也很大。今后扩展拍照识别时，可参考论文按类别核对样本量和容易混淆的类别，再用独立实拍照片评估。 |

这批书页用邱园数据库核对学名与科属，用大学推广资料核对可见特征和花期，并在文学栏标出原文位置。阅读《桃花源记》时，可以从原文的溪岸桃林读到张宏的《桃源胜概图》，再回到植物档案查看普通桃的形态。

每条档案链接到实际参考的园艺机构、博物馆、原典或机构资料。书页的「原文摘录」保留出处里的措辞，「中文整理」由项目根据上下文撰写和核对。MinerU 用于扫描文字识别和版面、页码提取。应用直接读取已整理好的中文字段。文学记录中的「名字灵感」是项目从作品意象延伸出的取名提议。核对日期记录在文化条目里。

已有 11 张书页配有经典图像。图片位于前端的 `assets/folio/`，使用馆方开放图像缩放并转为 WebP。采用馆方长卷节选的图像在图注明确标出。每张图旁边可打开馆藏原页和使用许可。识花台的三个候选均可进入各自书页。

## 花语原书

鸢尾、向日葵、郁金香和雪滴花的补充花语来自 Kate Greenaway 的《Language of Flowers》（1884）。每条花语保留原书的具体限定，例如红色郁金香，或矮秆和高秆向日葵，便于核对该书的用法。[馆藏目录](https://www.biodiversitylibrary.org/item/269449) · [公版扫描 PDF](https://archive.org/download/languageflowers00gree/languageflowers00gree.pdf)

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
