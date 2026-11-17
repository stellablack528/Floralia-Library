# Flower17 数据初检

检查日期：2026-10-28（Asia/Shanghai）

数据来源：<https://www.robots.ox.ac.uk/~vgg/data/flowers/17/index.html>

- 官方图片包：`data/raw/17flowers.tgz`；SHA-256：`FE38A60F8B4A95E657551247D3E7D799A3FAFCDBC595BE504B12839967823D70`
- 官方划分：`data/splits/datasplits.mat`；SHA-256：`634C141457B039095372C70685ECB0CBC88B7945EB7A9673690C0A39EBF2D481`
- 官方说明：`data/raw/README.txt`
- 解压位置：`data/raw/jpg/`；共 1360 张 `image_0001.jpg` 至 `image_1360.jpg`
- 使用 Pillow 验证：1360/1360 张可以读取

## 固定使用官方第一组划分

| 部分 | `.mat` 字段 | 数量 |
| --- | --- | ---: |
| 训练 | `trn1` | 680 |
| 验证 | `val1` | 340 |
| 测试 | `tst1` | 340 |

三组两两交集均为 0，合并后恰好覆盖 1–1360 的全部图片编号。训练与验证用于开发，测试只用于方案确定后的最终评价。

## 接下来需要核对

- 建立并验证 0–16 的类别映射；不要仅凭英文通用花名推断唯一物种。
- 记录每张图片编号、文件名、类别编号、划分。类别映射确认后再生成清单。
- 目前尚未训练模型，也没有使用测试集成绩选择方案。
