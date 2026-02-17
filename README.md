# 📡 Herald — 消息聚合网关

Herald 是一个轻量级的消息聚合转发网关，接收统一格式的消息请求，并分发到多个渠道（Webhook、Telegram、Email）。适用于服务监控告警、CI/CD 通知、IoT 事件推送等场景。

## ✨ 功能特性

- 🔗 **多渠道分发** — 支持 Webhook、Telegram Bot、Email（SMTP）三种渠道
- 🔑 **API Key 认证** — 通过 API Key 验证发送请求的合法性
- 🎛️ **Web 管理后台** — 渠道管理、密钥管理、消息日志查看，SSR 页面开箱即用
- 📝 **消息日志** — 记录每条消息的发送状态，支持失败重试
- 🔧 **Webhook 自定义** — 支持自定义 Headers、Body 模板（`{{title}}`/`{{body}}` 变量）、JSON/Form 两种内容格式
- 🐳 **Docker 部署** — 一键 `docker compose up` 启动

## 📦 技术栈

| 组件 | 技术 |
|------|------|
| 后端框架 | FastAPI + Uvicorn |
| 数据库 | SQLite (SQLAlchemy ORM) |
| 模板引擎 | Jinja2 (SSR) |
| 前端交互 | Alpine.js |
| UI 框架 | Tailwind CSS + DaisyUI |

## 🚀 快速开始

### Docker 部署（推荐）

```bash
git clone https://github.com/yourname/herald.git
cd herald

# 修改 docker-compose.yml 中的 HERALD_SECRET
docker compose up -d
```

访问 `http://localhost:8000`，使用 `HERALD_SECRET` 设定的密码登录。

### 本地开发

```bash
# 创建虚拟环境
python -m venv .venv
source .venv/bin/activate

# 安装依赖
pip install -r requirements.txt

# 启动（设置管理密码）
HERALD_SECRET=your_password uvicorn app.main:app --reload --port 8000
```

## ⚙️ 环境变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `HERALD_SECRET` | **必填** — 管理后台登录密码 & Cookie 签名密钥 | `changeme` |
| `DATABASE_URL` | SQLite 数据库路径 | `sqlite:///data/herald.db` |
| `SMTP_HOST` | SMTP 服务器地址 | — |
| `SMTP_PORT` | SMTP 端口 | `465` |
| `SMTP_USER` | SMTP 用户名 | — |
| `SMTP_PASSWORD` | SMTP 密码 | — |
| `SMTP_FROM` | 发件人地址 | 同 `SMTP_USER` |

## 📡 API 使用

### 发送消息

```bash
curl -X POST http://localhost:8000/send \
  -H "Content-Type: application/json" \
  -H "X-API-Key: YOUR_API_KEY" \
  -d '{
    "title": "部署通知",
    "body": "v1.2.0 已部署到生产环境",
    "channels": "my-webhook,telegram-bot"
  }'
```

**请求参数：**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `title` | string | ✅ | 消息标题 |
| `body` | string | ❌ | 消息正文 |
| `channels` | string | ❌ | 渠道名称，多个用英文逗号分隔。留空则发送到所有默认渠道 |

**认证方式：** 请求头 `X-API-Key: <key>` 或查询参数 `?key=<key>`

### 响应格式

```json
{
  "ok": true,
  "msg": "已发送到 2 个渠道",
  "data": {
    "results": [
      { "channel": "my-webhook", "status": "success" },
      { "channel": "telegram-bot", "status": "success" }
    ]
  }
}
```

## 🔧 渠道配置

### Webhook

| 配置项 | 说明 |
|--------|------|
| URL | 目标 Webhook 地址 |
| Method | HTTP 方法（GET / POST） |
| Content-Type | 请求格式（JSON / Form） |
| 自定义 Headers | 每行一个，格式 `Key: Value` |
| 自定义 Body | JSON 模板，支持 `{{title}}`、`{{body}}` 变量。留空默认 `{"title":"...","body":"..."}` |

### Telegram

| 配置项 | 说明 |
|--------|------|
| Bot Token | Telegram Bot API Token |
| Chat ID | 目标聊天 / 群组 ID |

### Email

| 配置项 | 说明 |
|--------|------|
| To | 收件人邮箱地址 |

> 💡 Email 渠道需要先配置 SMTP 相关环境变量。

## 📁 项目结构

```
herald/
├── app/
│   ├── main.py           # FastAPI 应用入口 & 页面路由
│   ├── api.py            # RPC 风格 API 端点
│   ├── models.py         # SQLAlchemy 数据模型
│   ├── schemas.py        # Pydantic 请求/响应 Schema
│   ├── services.py       # 消息分发服务（Webhook/Telegram/Email）
│   ├── auth.py           # 认证中间件（Cookie 签名）
│   ├── config.py         # 环境变量配置
│   ├── database.py       # 数据库连接
│   ├── static/app.js     # 前端 Alpine.js API 封装
│   └── templates/        # Jinja2 页面模板
│       ├── base.html
│       ├── login.html
│       ├── dashboard.html
│       ├── channels.html
│       ├── keys.html
│       └── logs.html
├── data/                 # SQLite 数据库存储目录
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```

## 📄 License

MIT
