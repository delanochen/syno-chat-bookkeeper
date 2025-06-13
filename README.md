# Flask NAS Receipt OCR 项目

## 项目简介
本项目基于 Flask，部署于群晖 NAS，通过 Synology Chat 机器人自动接收购物小票图片，进行 OCR 解析，提取关键信息并分类，支持多用户、分类管理、统计分析等功能。

## 主要功能
1. 自动接收并下载 Synology Chat 机器人推送的购物小票图片。
2. OCR 解析小票，提取日期、商家、明细、金额，并自动分类。
3. 数据存储于 SQLite 数据库。
4. 支持商品分类自定义、增删改查。
5. 支持手动添加购物信息。
6. 支持分类统计、月度汇总。
7. 支持多用户操作。
8. 提供简单的 Web 管理页面。

## 目录结构
```
app/
  main.py           # Flask 主程序
  models.py         # 数据库模型
  ocr.py            # OCR 解析逻辑
  utils.py          # 工具函数
  requirements.txt  # 依赖
Dockerfile
README.md
```

## 快速部署
1. 配置 Synology Chat 机器人 Webhook 指向本服务。
2. 构建并运行 Docker 容器：
   ```
   docker build -t flask-nas-receipt .
   docker run -d -p 9090:9090 -v /volume2/bookkeeper/bills:/app/bills flask-nas-receipt
   ```
3. 访问 http://<NAS_IP>:9090 进行管理。

## 依赖
- Flask
- SQLAlchemy
- pytesseract
- Pillow
- requests
- 其它见 requirements.txt

## 备注
- OCR 支持中英文小票。
- 如需自定义存储路径，请修改 Docker 挂载参数。 