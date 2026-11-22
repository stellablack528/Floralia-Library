# Floralia Library Windows CPU 验收报告

验收日期为 2026-11-22。源码来自 GitHub 的全新浅克隆，运行代码对应提交 `e46960f`。在同一台 Windows x64 工作机上新建虚拟环境，通过新增的 `requirements-inference-cpu.txt` 从 PyPI 和 PyTorch 官方 CPU 索引重新下载依赖。使用 Python 3.12.14、PyTorch 2.13.0+cpu、torchvision 0.28.0+cpu、Pillow 12.3.0 和 Microsoft Edge 158.0.4370.33。PyTorch 报告未编译 CUDA。

## 验收结果

| 检查项 | 实际结果 |
| --- | --- |
| 全新虚拟环境安装 | 通过。依赖安装完成，`pip check` 未发现冲突。 |
| 界面预览 | 通过。静态服务器载入了 25 个书页条目，游客可以打开铃兰书页。 |
| 本机权重与类别 | 通过。Bloom 25 权重约 6.3 MB，哈希与校验文件相符，服务报告 25 类。 |
| 铃兰照片 Top-3 | 铃兰 97.2%，荷花 1.2%，桂花 1.1%。 |
| Grad-CAM | 通过。接口返回 224 × 224 的模型裁剪图和针对铃兰的热力图，浏览器显示两张图。 |
| 识花回到书页 | 通过。点击首选结果打开铃兰书页，显示花语「愿幸福归来」和植物档案。 |

铃兰照片由 Troi Perkins 拍摄。复跑命令和原图入口见[Windows CPU 试用指南](../docs/windows-cpu.md)。97.2% 是该照片的模型预测分数。整体留出评估见[扩展实验报告](../docs/bloom25.md)。

## Beta 发布状态

**运行验收已通过，公开权重分发条件待核实。** 本次端到端验收使用本机已训练的权重。Oxford Flowers17 的项目页和随附 README 说明了图片来源与数据划分，未列出当前训练权重的分发条件。新增类别的训练清单中有 65 张 CC BY-NC 和 1 张 CC BY-NC-SA 照片。Creative Commons 说明，相关许可义务是否适用于模型分发取决于使用方式和具体情况。现有信息不足以确认这份权重的公开发布条件，因此预发布草稿暂不附权重。[Oxford Flowers17](https://www.robots.ox.ac.uk/~vgg/data/flowers/17/) · [Creative Commons 训练许可说明](https://creativecommons.org/using-cc-licensed-works-for-ai-training-2/)

读者目前可以使用公开源码预览资料馆。真实识花复现还需要获得同一权重与校验文件。
