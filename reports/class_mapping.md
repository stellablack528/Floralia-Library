# Flower17 类别映射与资料来源

日期：2026-11-17。当前只采用官方第一组划分。模型尚未训练，测试集只建立索引，不用于选模型。

## 映射依据

- [Oxford 官方数据页](https://www.robots.ox.ac.uk/~vgg/data/flowers/17/index.html)：17 类、每类 80 张，提供图片与三组划分。
- [Flower17 数据加载器的实现说明](https://galilai-group.github.io/stable-datasets/datasets/flowers17/)：说明图片按连续 80 个编号分组，`class_id = (image_id - 1) // 80`，列出类别顺序及官方划分的用法。
- `knowledge/classes.json` 是本项目的唯一类别映射表。`class_id` 从 0 到 16；界面 `order` 从 1 到 17，仅作显示。
- `data/processed/flower17_partition1.csv` 由 `src/prepare_flower17.py` 读取官方 `datasplits.mat` 生成。它只列出图片路径、类别和分组，不复制图片。

| class_id | 英文类别 | 中文展示名 | 图片编号 |
| ---: | --- | --- | --- |
| 0 | Daffodil | 黄水仙 | 1–80 |
| 1 | Snowdrop | 雪滴花 | 81–160 |
| 2 | Lily of the valley | 铃兰 | 161–240 |
| 3 | Bluebell | 蓝铃花 | 241–320 |
| 4 | Crocus | 番红花 | 321–400 |
| 5 | Iris | 鸢尾 | 401–480 |
| 6 | Tiger lily | 虎皮百合 | 481–560 |
| 7 | Tulip | 郁金香 | 561–640 |
| 8 | Fritillary | 贝母花 | 641–720 |
| 9 | Sunflower | 向日葵 | 721–800 |
| 10 | Daisy | 雏菊 | 801–880 |
| 11 | Colt's foot | 款冬 | 881–960 |
| 12 | Dandelion | 蒲公英 | 961–1040 |
| 13 | Cowslip | 黄花九轮草 | 1041–1120 |
| 14 | Buttercup | 毛茛 | 1121–1200 |
| 15 | Windflower | 银莲花 | 1201–1280 |
| 16 | Pansy | 三色堇 | 1281–1360 |

先前 UI 的顺序不符，且有 Lily、Colchicum、Wallflower 三个非本数据集类别。现已用上表统一。旧版文案中未经核实的学名和花语已改为“待核对”或“待补充”，避免把英文通用名称解释成唯一物种。先前浏览器收藏与历史若引用已移除的旧卡片 key，将无法打开；其它卡片的 key 保持不变。

## 文化资料

17 类均有带出处的代表植物档案和文化记录。`knowledge/classes.json` 保留模型类别的物种层级边界，代表植物及参考学名另存于 `knowledge/botanical_profiles.json`。条目来源和更新方式见 [知识库说明](../docs/knowledge.md)。

## 验证结果

`src/prepare_flower17.py` 实际检查 1360 张图片均可读取，官方第一组含训练 680、验证 340、测试 340；三者无交叉。每类在训练、验证、测试中分别为 40、20、20 张。复运行：

```powershell
.\.venv\Scripts\python.exe src\prepare_flower17.py
.\.venv\Scripts\python.exe src\sync_web_cards.py
```

哈希可用来确认下载文件未变化或检查重复文件，不用哈希值决定图片属于哪类。类别来自图片编号和映射表；划分来自官方 `.mat` 文件。

## 当前 Python 环境

项目使用 `D:\Projects\flower-and-folio\.venv`。已核对 PyTorch、torchvision、SciPy、Pillow 可用，CUDA 能识别 NVIDIA GeForce RTX 2050。已补齐 PyYAML、scikit-learn、matplotlib，供下一步配置、指标和图表使用。Grad-CAM 与服务接口依赖在实施相应模块时再确定。
