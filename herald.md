## 1. 项目概述

**项目名称**：Herald (消息聚合网关)
**核心逻辑**：

1.  **Webhook 接收**：标准 POST 接口 (`/send`) 接收外部消息（兼容 JSON/Form）。
2.  **分发核心**：基于 API Key 鉴权，基于 Channel 配置路由。
3.  **管理后台**：
    - **数据展示**：**服务端渲染 (SSR)**，由 FastAPI + Jinja2 直接生成 HTML。
    - **交互操作**：**RPC 风格** API (`/api/...`) 处理增删改，由 Alpine.js 调用。

## 2. 技术栈 (Tech Stack)

- **Backend**: FastAPI (Python 3.10+)
- **Database**: SQLite (SQLAlchemy ORM)
- **Template Engine**: **Jinja2** (核心渲染引擎，负责 HTML 注入数据)
- **CSS Framework**: **Tailwind CSS + DaisyUI** (CDN 引入)
- **Frontend Logic**: **Alpine.js** (CDN 引入，用于处理按钮点击、Toast 通知)
- **API Style**: **RPC (Action-oriented)**
  - Method: 均使用 `POST`
  - URL Pattern: `/api/{action_name}`
  - Response: JSON

## 3. 目录结构

herald/
├── app/
│ ├── main.py # 页面路由 (GET /, /channels...) -> 返回 HTML
│ ├── api.py # 动作接口 (POST /api/...) -> 返回 JSON
│ ├── models.py # DB 模型
│ ├── schemas.py # Pydantic 模型
│ ├── services.py # 发送逻辑
│ ├── templates/ # Jinja2 模板
│ │ ├── base.html # 骨架 (CSS/JS/TopNav)
│ │ ├── index.html # 首页 (SSR)
│ │ └── channels.html# 渠道页 (SSR)
│ └── static/
│ └── app.js # Alpine Store (API 调用器)
├── data/ # SQLite 挂载点
└── Dockerfile

## 4. 路由与 API 规范

### A. 页面路由 (Page Routes - GET)

_定义在 `app/main.py`。负责查询数据库，并将数据通过 Jinja2 注入 HTML。_

- `GET /` -> 渲染 `index.html` (Context: `stats` 统计对象, `recent_logs` 日志列表)
- `GET /channels` -> 渲染 `channels.html` (Context: `channels` 列表)
- `GET /keys` -> 渲染 `keys.html` (Context: `keys` 列表)
- `GET /logs` -> 渲染 `logs.html` (Context: `logs` 列表, `page` 当前页码)

### B. 动作接口 (Action RPC - POST)

_定义在 `app/api.py`。仅用于前端 Alpine.js 触发的操作，执行后通常需要刷新页面。_
_URL 前缀: `/api_`

1. **渠道管理**:

- `POST /api/create_channel` -> `{name, type, config, slug}`
- `POST /api/update_channel` -> `{id, ...}`
- `POST /api/delete_channel` -> `{id}`
- `POST /api/test_channel` -> `{id}` (触发一次测试发送)

2. **Key 管理**:

- `POST /api/create_key` -> `{name}` (自动生成 sk-...)
- `POST /api/revoke_key` -> `{id}`

3. **日志操作**:

- `POST /api/clear_logs` -> `{}`
- `POST /api/retry_msg` -> `{log_id}`

## 5. 前端实现规范 (SSR + Alpine)

**HTML 模板编写 (Jinja2)**:
使用 Jinja2 语法进行列表渲染。

```html
<tbody>
  {% for log in recent_logs %}
  <tr>
    <td>{{ log.title }}</td>
    <td>{{ log.status }}</td>
  </tr>
  {% endfor %}
</tbody>
```

**交互逻辑 (Alpine.js + API Store)**:
在 `app/templates/base.html` 或 `static/app.js` 中定义：

```javascript
document.addEventListener("alpine:init", () => {
  Alpine.store("api", {
    async call(action, payload = {}) {
      try {
        const res = await fetch(`/api/${action}`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || "API Error");

        // 成功提示
        this.showToast("success", "操作成功");
        return data;
      } catch (err) {
        this.showToast("error", err.message);
        throw err;
      }
    },
    showToast(type, msg) {
      /* DaisyUI implementation */
    },
  });
});
```

**按钮调用示例**:

```html
<button
  class="btn btn-error btn-sm"
  @click="$store.api.call('delete_channel', {id: {{ channel.id }} }).then(() => window.location.reload())"
>
  删除
</button>
```

## 6. UI 设计规范 (Light & Top Nav)

- **HTML 设置**: `<html data-theme="cupcake">` (浅色主题)
- **布局**: 顶部固定导航栏 (Sticky Top Navbar)。
- **颜色**: 页面背景 `bg-base-200`，内容卡片 `bg-base-100`。

**导航栏结构**:

- **Logo**: 左侧 "Herald" (Text-xl, Primary Color).
- **Menu**: 右侧链接 (概览, 渠道, 密钥, 日志).
- **Active State**: 当前页面的菜单项应高亮 (`request.url.path` 匹配).

```html
<div class="navbar bg-base-100 shadow-sm sticky top-0 z-50">
  <div class="flex-1">
    <a href="/" class="btn btn-ghost text-xl text-primary"
      ><i class="ri-radar-fill"></i> Herald</a
    >
  </div>
  <div class="flex-none">
    <ul class="menu menu-horizontal px-1 gap-2">
      <li>
        <a href="/" class="{{ 'active' if request.url.path == '/' else '' }}"
          >概览</a
        >
      </li>
    </ul>
  </div>
</div>
```

```

---

按顺序实现项目：

**Step 1: 初始化后端与数据库**
> "参考 `PROJECT_SPEC.md`，请先实现 `app/models.py` (数据库模型) 和 `app/database.py`。然后创建 `app/main.py`，实现基础的 Jinja2 配置和数据库依赖注入。"

**Step 2: 实现核心 Webhook 与 API**
> "请实现 `app/api.py` 中的 RPC 动作接口（Create/Delete等），以及 `app/main.py` 中的 `/send` Webhook 接收接口。确保使用 Pydantic 进行参数校验。"

**Step 3: 实现前端骨架 (Base)**
> "请根据 UI 规范，编写 `app/templates/base.html`。包含 Tailwind, DaisyUI, Alpine.js 的 CDN 引入，实现顶部导航栏，并在 `<script>` 中封装好 `$store.api` 调用器。"

**Step 4: 实现功能页面 (SSR)**
> "请实现 `app/main.py` 中的 GET 路由逻辑（查询数据库并传递 Context），然后编写 `app/templates/channels.html`。使用 Jinja2 渲染表格，使用 Alpine.js 调用 API 并刷新页面。"

```
