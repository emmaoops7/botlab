# 华亚幸福家静态设计稿版

## 打开方式

直接双击 `index.html` 可平铺查看全部 8 个 390px 移动画板；也可以分别打开 `home.html`、`login.html`、`payment.html`、`pay-now.html`、`my.html`、`property.html`、`repair.html`、`notice-detail.html`。

本版使用本地 `styles.css` 与页面内嵌 SVG symbol 图标，未引用 FontAwesome、cdnjs、Tailwind CDN 或业务 JS，离线打开也能看到图标和主要样式。

## 和上一版区别

- 改为逐页面静态 HTML，一个页面一个独立设计稿。
- 固定 390px 宽移动端画板，灰色背景，白色卡片化内容。
- 删除 `onclick`、`navTo`、`showToast` 等业务交互和业务脚本依赖。
- 图标改为内嵌 SVG，不依赖 FontAwesome CDN，导入设计工具时不再丢图标。
- 保留原型主要内容：登录、首页公告、费用金额与明细、立即缴费、我的、房产绑定、报修记录、公告详情、底部导航。

## 设计工具导入建议

1. 优先导入单页 HTML，避免总览页 iframe 被工具识别成嵌套页面。
2. 导入宽度设置为 390px；高度按页面内容自动扩展或使用 844px 截图高度。
3. 若设计工具不支持外链 CSS，请先打开页面截图，或将 `styles.css` 内容内联后再导入。
4. SVG 图标已内嵌在每个页面，适合离线查看和截图交付。
