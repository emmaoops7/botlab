# 华亚幸福家 HTML 拆分产物

源文件未修改：`/root/.openclaw/media/inbound/huaya-property-app-v3---db4efdb9-c1f3-485a-8e4d-53529bb762ba.html`

## 如何打开

推荐在本目录启动静态服务：

```bash
cd /root/clawd/huaya-property-split
python3 -m http.server 8080
```

然后访问：

- 多页面开发版：首页 `http://127.0.0.1:8080/dev/home.html`
- 设计工具导入版总览：`http://127.0.0.1:8080/design/index.html`

也可以直接双击打开各 HTML 文件；外部 Tailwind CDN 与 Font Awesome CDN 需要联网时才能完整呈现样式和图标。

## 文件结构

```text
huaya-property-split/
├── README.md
├── assets/
│   ├── common.css      # 原始公共样式 + 拆分辅助样式
│   └── app.js          # 开发版公共交互与页面跳转
├── dev/                # 多页面开发版
│   ├── index.html
│   ├── home.html
│   ├── login.html
│   ├── payment.html
│   ├── pay-now.html
│   ├── my.html
│   ├── property.html
│   ├── repair.html
│   └── notice-detail.html
└── design/             # 设计工具导入版
    ├── design.css
    ├── index.html      # 390px 画板总览
    ├── home.html
    ├── login.html
    ├── payment.html
    ├── pay-now.html
    ├── my.html
    ├── property.html
    ├── repair.html
    └── notice-detail.html
```

## 两套版本差异

### 多页面开发版 `dev/`

- 每个原始页面拆为独立 HTML：`home/login/payment/pay-now/my/property/repair/notice-detail`。
- 公共 CSS/JS 放在 `assets/`。
- 原 `navTo()` 单页切换改为页面跳转，底部 Tab、验证码、缴费金额、报修弹窗、Toast 等轻量交互仍可预览。
- 页面宽度限制为移动端 390px 居中，便于浏览器预览。

### 设计工具导入版 `design/`

- 每个页面都是独立静态画板，视口/画板固定 390px 宽。
- 尽量移除业务 JS 与点击事件，仅保留视觉结构、文本、表单状态和静态弹层结构。
- `design/index.html` 将全部画板平铺展示，方便导入或截图比对。

## 验证

已提供 `verify.py`（生成时使用的静态验证脚本逻辑）：检查页面文件数量、公共资源引用、关键 DOM、设计版无业务脚本引用。
