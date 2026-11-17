# MinerU 文献解析（第一阶段）

本模块与花卉分类模型隔离。已在 Windows、Python 3.12 的独立 `.venv-mineru` 中安装 MinerU 4.2.3。使用官方 4.x 的 `mineru-kit parse`，不使用旧版 `magic-pdf` 命令或未验证的 Python 内部 API。

## 本地运行

在项目根目录的 PowerShell 中：

```powershell
.\.venv-mineru\Scripts\python.exe src\parse_document.py documents\samples\flower_sample.pdf
```

文本型 PDF 可先用默认 `flash` 档；扫描件、公式和表格尝试 `--tier basic`。首次使用 Basic 时可能下载模型，且耗时明显更长：

```powershell
.\.venv-mineru\Scripts\python.exe src\parse_document.py C:\path\to\scan.pdf --tier basic --device cpu
```

`--device gpu` 是可选的 ONNX 设备请求，需在本机验证可用；默认强制 CPU，避免占用 4GB 显存。此入口不添加 `--remote`，文档只在本机解析。官方说明 [Flash 适合文本预览，Basic 支持 OCR、公式和表格](https://opendatalab.github.io/MinerU/usage/tiers/)。

每次输出到 `documents/parsed/<原名>-<SHA前10位>-<档位>/`：

- `markdown.md`：阅读预览。
- `middle_json.json`：版面和页级结构。
- `structured_content.json`：结构化内容。
- `result.zip`：MinerU 原始结果包，可能还含图片。
- `metadata.json`：原文件名、原路径、SHA-256、解析档位、设备和时间；`fact_review_status=unreviewed` 表示解析内容未经知识核对。

MinerU 的解析是**文字与版面提取**，不是花卉事实核验，更不是文学出处推理。后续知识抽取需另建审核流程、逐条记录来源和页码。Qt 可以用 `QProcess` 启动 `src/parse_document.py`，读取标准输出和退出码；进程在后台运行，界面可持续响应。

## 安装或重建独立环境

```powershell
uv venv --python 3.12 .venv-mineru
uv pip install --python .venv-mineru\Scripts\python.exe -r requirements-mineru.txt
.\.venv-mineru\Scripts\mineru.exe version --json
```

本项目只使用 MinerU 基础版。官方提示 `full` 套件建议至少 8GB 可用显存；本机 RTX 2050 为 4GB，不采用该套件。参考：[安装说明](https://opendatalab.github.io/MinerU/quick_start/)、[CLI 说明](https://opendatalab.github.io/MinerU/usage/cli_tools/)、[输出结构](https://opendatalab.github.io/MinerU/reference/output_files/)。

## 本机验证结果（2026-11-17）

- `flower_sample.pdf`：文本型 PDF，Flash + CPU 成功；Markdown、Middle JSON、Structured Content JSON 都存在。
- `flower_scan.pdf`：页面只有图片、没有可复制文字，Basic + CPU 成功；OCR 读出标题和正文，并生成上述三种结果。
- `flower_scan.png`：图片输入，Basic + CPU 成功；OCR 读出标题和正文。
- 自动化复核：`.\.venv-mineru\Scripts\python.exe -m unittest discover -s tests -p test_mineru.py`。

这是文档解析的最小闭环；尚未接入 Qt、SQLite 知识抽取或花卉识别卡片。样例文件只有测试文字，不是植物学事实来源。
