# Floralia Bloom 1.0 本机识花

Floralia Bloom 1.0（花页识花）是项目的最终 17 类模型。它把 MobileNetV3 Small 的 S0 基线与 S2 末层微调权重按 25% / 75% 合成一份权重。客户端提交一张图片，本机服务返回 Top-3 类别、预测分数和低分提示，并用类别键关联花卉书页。

在已有 PyTorch、Torchvision 和 Pillow 的项目虚拟环境中，从项目根目录启动。

```powershell
.\.venv\Scripts\python.exe -B src\serve_floralia.py
```

打开 `http://127.0.0.1:8501/`。模型权重单独保存，默认路径为 `models/experiments/flower17-student-weight-blend-20261119/best.pt`。如果权重保存在其他位置，可用 `--checkpoint` 指定路径。服务启动时核对权重校验值和 17 类映射。上传处理在本机内存中完成，足迹由现有浏览器存储记录。

接受不大于 10 MB 的单张 JPG、PNG 和 WebP。第一候选模型分数低于 50% 时提示用户核对。服务的 `GET /api/model` 返回模型版本，`POST /api/identify` 接收图片的原始字节。静态托管版本使用带标注的演示数据。

识花台可从前三名点选一个解释类别。`POST /api/grad-cam?class_id=类别编号` 接收同一张照片，返回实际输入的中心裁剪图和该类别的热力图。Grad-CAM 使用所选类别的原始分数对最后一张空间特征图的梯度。高亮表示支持该类别的区域线索，强度按单图归一化。方法见 [Selvaraju 等，ICCV 2017](https://openaccess.thecvf.com/content_iccv_2017/html/Selvaraju_Grad-CAM_Visual_Explanations_ICCV_2017_paper.html)。

从项目根目录运行 `.\.venv\Scripts\python.exe -B src\plot_floralia_grad_cam.py`，可生成 `reports/figures/floralia_bloom_grad_cam.png`。脚本需要 Matplotlib 和用于核对官方划分的 SciPy。对照包含正确识别的雪滴花（0084）、在第一组 340 张官方测试原图中分数最高的错例（0614，郁金香被预测为黄花九轮草），以及将亮度降为原图 45% 的向日葵（0724）。

官方第一组的 340 张测试原图上，最终模型 Top-1 为 94.41%（321 张），Top-3 为 98.82%（336 张），Macro-F1 为 0.9443。三组去重汇总共 850 张原图，融合方案 Top-1 为 94.35%（802 张）。第二、三组按固定设置分别训练。15 种模拟变化来自同一批照片，融合方案平均 Top-1 为 89.08%。
