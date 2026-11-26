# Floralia Bloom 25 本机实验报告

Floralia Bloom 25 在原版 17 类的基础上增加山茶花、绣球花、梅花、桃花、荷花、桂花、牡丹和紫藤。25 类使用同一个 MobileNetV3-Small 模型。英文界面和书页可通过页面上的语言按钮切换，文学原文保留原语种。PDF 摘录审核仍关联原有 17 类。

## 训练和划分

- 从 Floralia Bloom 1.0 的权重出发，冻结图像特征提取部分和已有分类头的中间层，只训练最后一层的 25 个输出。旧类一起参加训练，并用旧模型的预测分布辅助保留旧类。使用 RTX 2050，模型选自第 20 轮，依据是验证集 25 类等权的首选准确率（92.48%）。
- 旧类沿用 Oxford Flower17 的第一组划分。新类从 iNaturalist 实拍照片收集，保留照片署名、许可、观测页面和来源图像链接。逐张筛选是否能看到花，去除重复文件，新类按摄影者分组划分。园艺花卉使用的数据包括平台研究级和非研究级观测，物种标签继承自观测记录。牡丹补充了非商业许可的照片，用于这次本机实验。
- 旧类测试集 340 张。新增类留出测试集 111 张。新类测试照片来自同一观测平台，且各类样本量不均，这些结果适合做本机初测。

[Oxford Flower17 官方资料](https://www.robots.ox.ac.uk/~vgg/data/flowers/17/) · [iNaturalist 开放数据与照片署名](https://github.com/inaturalist/inaturalist-open-data)

## 测试结果

| 类别 | 训练 | 验证 | 留出测试 | 首选正确 | 前三命中 |
| --- | ---: | ---: | ---: | ---: | ---: |
| 山茶花 | 52 | 9 | 14 | 12 | 13 |
| 绣球花 | 65 | 17 | 22 | 17 | 20 |
| 梅花 | 36 | 6 | 8 | 4 | 8 |
| 桃花 | 55 | 17 | 17 | 15 | 16 |
| 荷花 | 55 | 8 | 18 | 15 | 17 |
| 桂花 | 34 | 12 | 5 | 5 | 5 |
| 牡丹 | 80 | 20 | 14 | 12 | 13 |
| 紫藤 | 58 | 20 | 13 | 10 | 13 |
| 新类合计 | 435 | 109 | 111 | 90（81.1%） | 105（94.6%） |

| 原有 17 类在同一批 340 张测试图上的表现 | 首选正确 | 前三命中 |
| --- | ---: | ---: |
| Floralia Bloom 1.0 | 321（94.4%） | 336（98.8%） |
| Floralia Bloom 25 | 323（95.0%） | 336（98.8%） |

梅花首选答对 4/8，验收时应重点查看前三个候选。桂花只测了 5 张，当前成绩对新照片的代表性有限。合并测试集共 451 张，首选正确 413 张，前三命中 441 张。两批测试图的来源不同，分别报告更方便解释结果。

## 本机验收

1. 打开识花台，点 **English**，进入资料馆可按英文花名或学名查找 25 张书页。
2. 上传单张照片，查看 Top-3、模型分数和 Grad-CAM，再打开候选的书页。
3. 查看本机 `models/experiments/floralia-bloom25/metrics.json` 和 `splits.json` 核对逐类成绩、划分及照片署名。模型权重与照片存放在本机。

[打开本机识花台](http://127.0.0.1:8501/#/identify)

## 下一轮扩类与准确率研究

先从 25 类扩到 30 类。首批选择月季、菊花、茉莉、栀子、牵牛。每类先核准模型标签与书页的对应关系，再审核照片，最后做训练对照。以下是调研后的实验方案，待实际训练与验收。

实施结果和本机复跑说明见 [Bloom 30](bloom30.md)。

### 新类定义与书页来源

| 对外显示名 | 首批照片的标签范围 | 植物档案与阅读资料 |
| --- | --- | --- |
| 月季 | 先用可核实为 *Rosa chinensis* 的照片。市售园艺杂交月季和 *Rosa rugosa* 的照片另存候选。 | 学名与形态见[邱园月季条目](https://powo.science.kew.org/taxon/urn%3Alsid%3Aipni.org%3Anames%3A732029-1)及[植物智月季花](https://www.iplant.cn/info/Rosa%20chinensis)。[邱园玫瑰条目](https://powo.science.kew.org/taxon/urn%3Alsid%3Aipni.org%3Anames%3A927373-1)用来区分 *R. rugosa*。莎士比亚《罗密欧与朱丽叶》第二幕第二场提到的 rose 可作为蔷薇属的文学关联，作品未限定为月季。[福尔杰图书馆原文](https://www.folger.edu/explore/shakespeares-works/romeo-and-juliet/read/2/2/) |
| 菊花 | 栽培菊 *Chrysanthemum × morifolium*。野菊等近似类单独保留，供混淆测试和人工核对。 | [邱园接受的杂交名称](https://powo.science.kew.org/taxon/77111328-1) · [英国皇家园艺学会栽培菊资料](https://www.rhs.org.uk/plants/chrysanthemum/growing-guide) · 陶渊明《饮酒（其五）》中的菊按文学通名收录。[原诗](https://article.xuexi.cn/html/13395986728056917107.html) |
| 茉莉 | *Jasminum sambac*。保留可辨认的单瓣与重瓣样本，对照栀子等白花。 | [邱园茉莉条目](https://powo.science.kew.org/taxon/609755-1) · [植物智茉莉花](https://www.iplant.cn/info/Jasminum%20sambac) · 福州以鲜花为茶叶窨香的工艺。[联合国粮农组织福州茉莉花与茶文化系统](https://www.fao.org/giahs/giahs-around-the-world/china-fuzhou-jasmine-tea/en) |
| 栀子 | *Gardenia jasminoides*。在栀子和茉莉两类中都收集能看见叶或花萼的照片。 | [邱园栀子条目](https://powo.science.kew.org/taxon/751073-1) · [植物智栀子](https://www.iplant.cn/info/Gardenia%20jasminoides) · 杜甫《江头四咏·栀子》可从《全唐诗》卷 227 核对。[原典转录](https://zh.wikisource.org/zh-hans/%E5%85%A8%E5%94%90%E8%A9%A9/%E5%8D%B7227#栀子) |
| 牵牛 | *Ipomoea nil*。*I. purpurea* 单独列为近似类，标签含糊的 morning glory 照片留待审核。 | [邱园牵牛条目](https://powo.science.kew.org/taxon/urn%3Alsid%3Aipni.org%3Anames%3A1071575-2/general-information) · [植物智牵牛](https://www.iplant.cn/info/Ipomoea%20nil?t=focn) · [邱园圆叶牵牛条目](https://powo.science.kew.org/taxon/urn%3Alsid%3Aipni.org%3Anames%3A30043043-2/general-information)。Florence Earle Coates 的《The Morning-Glory》以花的短暂开放为主题，按文学通名关联。[诗选第三卷原文](https://www.gutenberg.org/cache/epub/2621/pg2621-images.html) |

书页分别记录模型对应的学名及其适用范围、文学原文所用的通名、来源机构或作者、作品位置和核对日期。花语按现有要求逐条核对出处。学名以邱园为依据，中文名和形态对照植物智，文学与用物史分别核对原典或相关机构资料。书页照既有方式生成中英文网页数据。要在 SQLite 文献审核区使用新增类别，还需同步登记稳定代号和来源。[资料收录裁定](knowledge.md#资料收录裁定)

### 数据和 GitHub 工具

- 优先复用 `src/collect_bloom25.py` 的采集、署名及人工审核流程。以确切物种标识收集观测，按单张照片核对授权、作者、来源、可诊断部位与标签。栽培观测的评级受平台规则影响，可单独审核这批样本，用植物园铭牌或其他可追溯资料复核身份。[iNaturalist 数据集原论文](https://openaccess.thecvf.com/content_cvpr_2018/html/Van_Horn_The_INaturalist_Species_CVPR_2018_paper.html) · [iNaturalist Open Data GitHub](https://github.com/inaturalist/inaturalist-open-data) · [观测评级说明](https://inaturalist.freshdesk.com/en/support/solutions/articles/151000169936-what-is-the-data-quality-assessment-dqa-and-how-do-observations-qualify-to-become-research-grade-)
- Pl@ntNet-300K 作为候选补充数据和评估参考。先核对物种表、器官字段与单图授权，再决定是否纳入。Oxford Flowers102 的官方名录有 *rose* 和 *morning glory*，分别有 171 和 107 张，适合作为人工复核线索，物种确认后才能进入对应的训练标签。[Pl@ntNet-300K 论文](https://datasets-benchmarks-proceedings.neurips.cc/paper_files/paper/2021/hash/7e7757b1e12abcb736ab9a754ffb617a-Abstract-round2.html) · [Pl@ntNet-300K GitHub](https://github.com/plantnet/PlantNet-300K) · [Oxford Flowers102 官方类别](https://robots.ox.ac.uk/~vgg/data/flowers/102/categories.html)
- 每次划分前，按观测、摄影者、同株连拍和跨平台来源排查重叠。现有 SHA-256 查找内容相同的文件，可以加感知哈希（pHash）筛出疑似缩放、重压缩后仍相似的照片，再人工核对。无法拆分的近重复样本归入同一个划分。[ImageHash GitHub](https://github.com/JohannesBuchner/imagehash)
- 新类尽可能覆盖不同摄影者、品种、花色、距离和光照。首轮争取为每个新类单独留出 20–30 张确认物种的手机实拍图作为初验，并报告实际数量。留出集保留库外近似花和非花照片，分别记录系统误接纳率。扩 30 类前，重测当前 25 类的常见错例，尤其是梅花与桃花。

### 准确率实验顺序

| 对照 | 实施方式 |
| --- | --- |
| 现有 25 类基线 | 用当前权重跑新建的旧类实拍集，记录每类首选、前三命中和易混淆对象。官方 Flower17 测试集继续作为旧能力的最终回归检查。 |
| 25 类数据对照 | 固定原训练方法与标签，用原训练集和补充审核样本后的训练集分别训练，用同一份旧类验证集比较，判断补数据是否改善梅花、桂花等薄弱类别。 |
| 30 类基线 | 复用 MobileNetV3-Small，冻结特征提取层，只训练新的分类输出层，保留旧类样本。现有 Bloom 25 已经使用随机裁剪、翻转、颜色扰动、按类别加权的交叉熵和旧类蒸馏，首轮保留这些设置。 |
| 部分微调 | 使用相同数据划分、配对随机种子和训练预算，从同一权重起步，额外微调最后一个 1×1 卷积，固定 BatchNorm 运行统计量。可缓存这个卷积的输入，复用现有 S2 思路。用验证集比较逐类成绩，再运行独立实拍留出集。 |
| 错误驱动的单项调整 | 小花被裁掉时对比保留构图的输入，背光等拍摄条件集中出错时再比较温和增强。若少样本类别持续偏弱，对比现有损失权重与按有效样本数计算的类别权重。每次改变一项，保留原颜色和花形可见的验证样例。[Torchvision GitHub](https://github.com/pytorch/vision) · [RandAugment 论文](https://proceedings.neurips.cc/paper_files/paper/2020/hash/d85b63ef0ccb114d0a3bb7b7d808028f-Abstract.html) · [Class-Balanced Loss 论文](https://arxiv.org/abs/1901.05555) · [作者代码](https://github.com/richardaecn/class-balanced-loss) |
| 生物图像预训练对照 | 如果轻量主干对相似花仍明显吃力，再离线提取 BioCLIP 特征，训练同一套标签的线性分类头。它的训练资料含 iNat21，比较时优先用新增的独立实拍图，并检查能追溯的重叠。[BioCLIP 论文](https://arxiv.org/abs/2311.18803) · [作者 GitHub](https://github.com/Imageomics/bioclip) · [预训练数据清单](https://huggingface.co/datasets/imageomics/TreeOfLife-10M) |

验证集用各类别等权首选准确率选模型，同时看 Macro-F1。留出集单独报告旧类、新类、逐类 Top-1/Top-3、混淆对和库外误接纳率，附正确张数与总数。提醒阈值在验证集上选，记录误接纳和误拒绝之间的取舍。温度缩放可校准分数，它保持候选排序，分类准确率由模型及数据对照评估。[校准原论文](https://proceedings.mlr.press/v70/guo17a.html) · [最大 Softmax 分数的库外检测基线](https://arxiv.org/abs/1610.02136)

## Bloom 25 准确率优化对照

使用现有 Bloom 25 权重和已归档的 `splits.json`，固定 1,115 张训练图、449 张验证图和 451 张测试图。脚本在运行前核对文件哈希，以及 iNaturalist 的观测与摄影者是否跨组。所有对照共享相同的初始化、三份预处理后的训练视图和三个配对随机种子。验证集用类别等权的 Top-1 选择轮次，同分比较 Macro-F1，两项都相同时保留较早轮次。每组训练后核对 BatchNorm 和冻结参数。

| 对照 | 实际训练参数 | 类别权重 |
| --- | --- | --- |
| `head` | 只更新 25 类输出层 | 沿用 Bloom 25 的平方根逆频率 |
| `partial` | 更新 25 类输出层和最后一个 1×1 卷积的权重 | 与 `head` 相同 |
| `partial-balanced` | 更新与 `partial` 相同的参数 | 按 Cui 等论文的有效样本数计算类别权重，β = 0.99 |

三组共用加权交叉熵，并对旧类样本沿用温度为 2 的蒸馏项。蒸馏目标来自当前 Bloom 25 对旧 17 类输出的分布。冻结前段的特征图只提取一次，因此微调时只运行网络尾部。验证集先锁定方案，随后用固定的第一个种子复核各组在旧留出图上的表现。方案需高于当前模型的验证集 Macro Top-1，并将旧 17 类的等权 Top-1 降幅控制在 1 个百分点以内。该留出集已在历史版本报告过成绩。

方法与实现依据。[MobileNetV3 论文](https://arxiv.org/abs/1905.02244) · [知识蒸馏论文](https://arxiv.org/abs/1503.02531) · [Class-Balanced Loss 论文](https://arxiv.org/abs/1901.05555) · [类别均衡损失作者代码](https://github.com/richardaecn/class-balanced-loss) · [PyTorch / Torchvision](https://github.com/pytorch/vision)

从 Git 仓库根目录运行下面的命令。第一条做 16 张图的小批检查，验证分段计算与整网推理一致，并检查训练参数范围。第二条运行三个种子、每组 12 轮，保存逐轮曲线数据、逐类结果、混淆矩阵及可加载的候选权重。输出目录使用新名称以保留历史结果。训练依赖见 [CUDA 12.6 依赖文件](../requirements-training-cu126.txt)，CPU 重跑使用 [CPU 依赖文件](../requirements-inference-cpu.txt) 并改为 `--device cpu`。

```powershell
$runtime = 'D:/Projects/flower-and-folio'
$python = Join-Path $runtime '.venv/Scripts/python.exe'
$output = 'models/experiments/floralia-bloom25-accuracy'
& $python src/optimize_bloom25.py $runtime $output --device cuda --smoke
& $python src/optimize_bloom25.py $runtime $output --device cuda
```

### 本机结果

RTX 2050，PyTorch 2.13.0+cu126，Torchvision 0.28.0+cu126。16 张图的小批检查通过，三组各跑三个种子并成功导出可加载权重。特征提取、训练、评估和导出共耗时约 146 秒。下表对照组的验证成绩是三个种子的平均值，留出复核使用预先确定的第一个种子。

| 方案 | 验证集类别等权 Top-1 | 旧 17 类 Top-1 / Top-3 | 新增 8 类 Top-1 / Top-3 |
| --- | ---: | ---: | ---: |
| 当前 Bloom 25 | 92.48% | 323/340 · 336/340 | 90/111 · 105/111 |
| `head` | 92.88% | 322/340 · 336/340 | 88/111 · 106/111 |
| `partial` | 92.88% | 323/340 · 336/340 | 89/111 · 105/111 |
| `partial-balanced` | 92.81% | 323/340 · 336/340 | 89/111 · 105/111 |

`head` 和 `partial` 的验证 Top-1 持平。由平均 Macro-F1 的细微差距，验证规则选中 `head`。它在留出集的首选命中共减少 3 张，新增类前三多命中 1 张。微调和类别均衡损失也没有提高留出集首选成绩。此次部署建议仍是当前 Bloom 25。旧留出图用于历史复核，下一轮改动用独立实拍图确认。

逐类结果显示，当前模型将 8 张梅花中的 3 张认成桃花，将 22 张绣球花中的 3 张认成紫藤。三组再训练均未改善梅花的测试首选成绩（4/8）。后续补图可从这两组混淆开始，梅花和桃花补带枝叶的近景，绣球与紫藤补完整花序和侧面图。原始逐轮数据、逐类统计、混淆矩阵及哈希记录位于运行输出的 `metrics.json`、`selection.json` 和各组的 `*-validation.json`。

## 重新训练

在具备 PyTorch、Torchvision 和 Pillow 的环境中，先准备原版 Bloom 权重和 Oxford 第一组划分 CSV，路径见 [本机识花说明](model.md)。以下命令以项目根目录为起点。

```powershell
.\.venv\Scripts\python.exe src\collect_bloom25.py data\raw\floralia-bloom25
```

收集脚本会保存候选照片与 `candidates.json`。核对每张候选图是否拍到了花，并把通过审核的 `photo_id` 放入该目录下的 `approved.json`，格式是整数数组。原实验还使用 `--supplement-peony-local` 收集牡丹的本机非商业研究样本。重新收集时平台候选会随时间变化，复核原实验请使用本机留下的划分和署名记录。

```powershell
.\.venv\Scripts\python.exe src\train_bloom25.py . data\raw\floralia-bloom25 models\experiments\floralia-bloom25
```
