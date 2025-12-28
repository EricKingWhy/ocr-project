# 百度 OCR 发票识别系统

本项目使用 Tkinter + PIL + sqlite3 + requests 实现发票识别与入库。

## 运行步骤
1. 在 `config.py` 中填写你的百度 OCR `API_KEY` 与 `SECRET_KEY`。
2. 初始化数据库：`python db_init.py`（生成 `invoice_system.db`）。
3. 启动系统：`python final_system.py`。

## 功能说明
- 启动先登录，用户名/密码来自本地数据库 `users` 表（默认：admin / 123456）。
- 选择图片后调用百度 OCR，正则提取发票代码、号码、日期、金额并自动填充。
- 点击保存将识别结果写入 `invoices` 表。

## legacy 目录
`legacy/` 保存了旧版入口与历史文件，供参考或回退使用。
