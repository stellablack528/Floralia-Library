# Floralia SQLite 数据库

数据库文件为 `data/knowledge/floralia.sqlite3`，基础表由 `src/knowledge_schema.sql` 创建。版本 2 通过 `src/evidence_translations.sql` 增加译文表，本机服务启动时自动升级已有版本 1 的数据库。依赖 Python 3.12 自带的 `sqlite3`，新建连接开启外键检查，库启用 WAL。本地运行库放在 Git 忽略目录。建表文件、导入脚本和原始知识 JSON 可用于从头重建，数据库内后续录入的文献和修改需要保留本地库。表用 SQLite 的 STRICT 模式，并校验 JSON 数组。未来 Qt 如直接连接，请选择 SQLite 3.38 或更新版并在每个连接执行 `PRAGMA foreign_keys = ON`。参考 [外键](https://sqlite.org/foreignkeys.html)、[STRICT 表](https://sqlite.org/stricttables.html)和 [WAL](https://sqlite.org/wal.html)。

## 表名和关系

| 表 | 主键 | 用途 |
| --- | --- | --- |
| `flower_classes` | `class_key`，`class_id` 唯一 | 固定的 Flower17 0–16 类映射，模型和网页用同一类别代号。 |
| `botanical_profiles` | `class_key` | 每类一份代表植物档案，含科属、特征、生境、花期和适用范围。 |
| `sources` | `source_id` | 网页出处登记，URL 唯一。 |
| `botanical_sources` | `class_key` + `source_id` | 一份植物档案可以引用多个出处。 |
| `cultural_entries` | `entry_id` | 某类花的文学、绘画或民俗条目，含作者、出处、定位和核对日期。 |
| `documents` | `document_id`，`sha256` 唯一 | 文献原名、路径、题名、作者、出版年和来源 URL。 |
| `document_parses` | `parse_id` | 一份文献可以多次解析，分别保存时间、MinerU 版本、档位和结果目录。 |
| `document_pages` | `parse_id` + `page_number` | 一次解析找到的原文页码。由 MinerU 的 `page_idx` 加一得到，可保留跳页。 |
| `document_evidence` | `evidence_id` | 类别、解析记录和页码关联到原文摘录及整理内容，保留出处和审核状态。 |
| `evidence_translations` | `evidence_id` | 每条摘录的简体中文译文、原文快照、模型和译文审核状态。 |

## 增删改查

从 Python 模块 `src/knowledge_store.py` 开启一次连接。`open_store()` 在正常退出时提交，同一作用域抛出异常时回滚。

| 操作 | 调用方式 |
| --- | --- |
| 增加 | `add(table, **fields)` 返回记录 ID。`import_mineru(folder)` 一次登记文献、解析和页码。 |
| 查询 | `get(table, id)` 查单条，`flower(class_key)` 查整张书页，`list_flowers(query)` 和 `list_documents(query)` 搜索，`parses(document_id)` 查解析记录，`evidence(class_key, review_status)` 查待审核资料。 |
| 修改 | `update(table, id, **fields)` 改正文或元数据。`set_botanical_sources(class_key, source_ids)` 更新植物出处关联。 |
| 删除 | `delete(table, id)` 删除条目。文献记录删除时，其解析、页码和证据一并移除，磁盘原件和解析文件由文献管理界面另行处理。 |

CRUD 支持表为 `botanical_profiles`、`sources`、`cultural_entries`、`documents` 和 `document_evidence`。Flower17 类别编号由初始化数据固定，解析与页码由导入入口管理。已被档案或文化条目引用的出处受外键保护。代表植物特征写入 `traits_json` 时使用 JSON 字符串数组，读取整张书页时返回 `traits` 数组。

文献登记按原件 SHA-256 去重，同一次解析重复导入返回相同 ID。新一次运行使用独立目录。数据库保存文件位置和页码索引。OCR 提取结果可被录入为 `source_statement`（原文陈述）或 `inference`（推断），两者的审核状态均默认为 `pending`。证据内容修改后默认回到待审状态。书页查询只返回 `verified` 的原文陈述，审核入口仍可查询包括推断在内的全部记录。录入证据需要摘录、整理内容和本次解析中真实存在的页码。

## Windows 运行方式

项目根目录执行这些命令，作为例如 Qt 用 QProcess 调用时的约定，成功输出为 UTF-8 JSON。

~~~powershell
.\.venv\Scripts\python.exe src\knowledge_store.py init
.\.venv\Scripts\python.exe src\knowledge_store.py flower snowdrop
.\.venv\Scripts\python.exe src\knowledge_store.py documents
.\.venv\Scripts\python.exe src\knowledge_store.py import-mineru "某次解析输出的完整目录"
~~~

`init` 首次导入 17 类、植物档案和文化记录。重复运行会检查类别映射，保留已经产生的编辑。`--db` 支持在子命令前指定其它 SQLite 文件，适合测试。

本机书页的「文献与文学」从 SQLite 读取已审核的原文陈述。「审核文献摘录」可查看待审核原文和中文整理，保存通过或不通过的决定。审核按打开时读到的证据版本保存，证据若已变更需要重新核对。静态 Web 保留由 `knowledge/` 生成的书页内容。

## 雪滴花样例

Jane Loudon（1841）的《The Ladies’ Flower-Garden of Ornamental Bulbous Plants》在印刷第 180 页讨论普通雪滴花（*Galanthus nivalis*）；馆藏 PDF 对应第 20 页。演示从该页录入两条原文陈述，初始状态为一条已审核、一条待审核。 [查看馆藏 PDF 第 20 页](https://dafflibrary.org/wp-content/uploads/Narcissus-The-ladies-flower-garden-of-oramental-bulbous-plants-Mrs.-Loudon-1841.pdf#page=20)

在 D 盘项目根目录可用 MinerU Basic 复现扫描页的文字提取。

~~~powershell
.\.venv-mineru\Scripts\python.exe src\parse_document.py documents\sources\Loudon-1841-Narcissus-and-Snowdrop.pdf --tier basic --device cpu --page 20
~~~
