app_name = "order_analytics"
app_title = "Order Analytics"
app_publisher = "Order Analytics"
app_description = "客户订单数据导入与客户购买分析"
app_email = "admin@example.com"
app_license = "MIT"
app_version = "0.0.1"

# 只依赖 Frappe 核心，因此本应用既能安装在纯 Frappe 站点，也能安装在 ERPNext 站点
required_apps = ["frappe"]

# 安装 / 迁移后，自动把订单与报表权限授予 ERPNext 的销售角色（角色存在时才生效）
after_install = "order_analytics.setup.after_install"
after_migrate = "order_analytics.setup.after_migrate"

# ---- 页面静态资源（按需启用） ----
# app_include_css = "/assets/order_analytics/css/order_analytics.css"
# app_include_js = "/assets/order_analytics/js/order_analytics.js"

# ---- 网站路由（本应用仅用于后台 Desk，无需网站入口） ----
# website_route_rules = []

# ---- 文档事件（金额汇总在 DocType 类内完成，无需挂钩） ----
# doc_events = {}
