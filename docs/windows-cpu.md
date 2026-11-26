# Windows CPU 试用指南

使用 Windows x64、Python 3.12 和 Edge 或 Chrome。下文的 `py -3.12` 适用于通过 Windows Python Launcher 调用的 Python 3.12。若用 uv 管理 Python，可将 `py -3.12` 替换为 `& (uv python find 3.12)`。从 GitHub 下载源码或克隆仓库，然后在仓库根目录打开 PowerShell。

## 浏览资料馆与界面

```powershell
py -3.12 -m http.server 8000 --bind 127.0.0.1
```

打开 [本机界面预览](http://127.0.0.1:8000/)，以游客身份进入。识花台在此模式下显示标注为演示的数据，30 张书页及双语花语可直接浏览。

## 运行真实识花

本机识花需要已获得的 Bloom 25 权重 `best.pt` 及同版本的 `best.sha256`。将两份文件放到 `models/experiments/floralia-bloom25/`。公开仓库暂未提供权重下载。已有这两份文件的测试者可以继续。

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-inference-cpu.txt
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -B src\serve_floralia.py
```

预设依赖使用 PyTorch 和 torchvision 的 CPU 构建。服务会在启动时核对权重的 SHA-256 和类别映射。下载依赖后，推理和 Grad-CAM 在本机运行。

1. 打开 [本机识花台](http://127.0.0.1:8501/)，以游客身份进入识花台。
2. 下载并上传 [铃兰试用照片](https://inaturalist-open-data.s3.amazonaws.com/photos/671266239/medium.jpg)。这张照片由 Troi Perkins 拍摄，来自 [iNaturalist 观测记录](https://www.inaturalist.org/observations/367568082)，使用 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)。
3. 点 **开始识别**。这张照片在验收时的首选是铃兰，模型预测分数约为 97.2%，后两名为荷花和桂花。
4. 在 Grad-CAM 区域点 **铃兰**，核对裁剪图和热力图，再点 **查看铃兰书页**，查看花语「愿幸福归来」及植物档案。

端口 8501 已被占用时，可以用 `--port 8512` 启动，并在浏览器打开对应端口。完整的模型设置与评估范围见[本机模型说明](model.md)。文献解析和翻译可按需单独配置。[MinerU 设置](mineru.md) · [本机翻译](translation.md)
