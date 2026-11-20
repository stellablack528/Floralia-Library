# 本机文献翻译

Floralia 通过 llama.cpp 在本机运行腾讯的 Hy-MT2-1.8B。MinerU 提供原文和页码，翻译服务只处理选中的原文摘录。核对时并排参考原文、中文整理和可编辑的译文初稿。摘录和译文分别审核，书页展示两者均已通过的译文。

## 启动

从 [llama.cpp 发布页](https://github.com/ggml-org/llama.cpp/releases) 下载适合系统的 CPU 版，解压到 `models/translation/llama`。在 Windows 上已用 [b12540](https://github.com/ggml-org/llama.cpp/releases/tag/b12540) 的 x64 CPU 版验证。从 [腾讯官方 GGUF 仓库](https://huggingface.co/tencent/Hy-MT2-1.8B-GGUF/tree/main) 下载 `Hy-MT2-1.8B-Q4_K_M.gguf` 到 `models/translation`。该权重约 1.13 GB，采用 Apache 2.0 许可。

在项目根目录的两个 PowerShell 窗口分别启动。第一个窗口按实际解压路径选择 `llama-server.exe`。

```powershell
.\models\translation\llama\llama-server.exe --model .\models\translation\Hy-MT2-1.8B-Q4_K_M.gguf --alias Hy-MT2-1.8B-Q4_K_M --host 127.0.0.1 --port 8088 --n-gpu-layers 0 --ctx-size 4096 --parallel 1 --jinja --no-ui --cors-origins localhost --no-cors-credentials
```

```powershell
.\.venv\Scripts\python.exe -B src\serve_floralia.py
```

打开本机书页，点「生成中文译文」，在「待审核译文」中修改并通过，或退回后重新生成。单次最多处理 2400 个原文字符。服务仅连接回环地址，翻译模型和项目数据保存在本机。可用 `--translation-port` 指定另一端口。

## 接口

`src/document_translation.py` 向 llama-server 的 `POST /v1/chat/completions` 传入摘录和该条适用的术语提示，并读取生成的中文文本。译文存进独立表，保留原文快照与模型版本，避免原文修改后继续显示旧译文。原有中文整理仍显示在它自己的字段里。

[Hy-MT2 提示格式](https://github.com/Tencent-Hunyuan/Hy-MT2/blob/main/README.md) · [llama.cpp 服务端接口](https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md)
