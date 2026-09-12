app_name = "order_analytics"
app_title = "Order Analytics"
app_publisher = "Order Analytics"
app_description = "Customer order import and purchase analytics for ERPNext"
app_email = "admin@example.com"
app_license = "MIT"
app_version = "0.0.1"

# Depends on ERPNext (uses ERPNext sales roles and module system)
required_apps = ["frappe", "erpnext"]

# After install / migrate: auto-create Module Def and grant permissions to ERPNext sales roles
after_install = "order_analytics.setup.after_install"
after_migrate = "order_analytics.setup.after_migrate"

# Scheduled tasks: check every hour whether a TikTok Shop auto-sync is due.
# The actual sync only runs when the configured interval has elapsed
# (see TikTok Shop Settings -> Automatic Sync).
scheduler_events = {
	"hourly": [
		"order_analytics.order_analytics.doctype.tiktok_shop_settings.tiktok_shop_settings.run_scheduled_sync",
	],
}

# Module definition: ensures the module shows in the ERPNext sidebar with icon and label
module_def = {
	"Order Analytics": {
		"module_name": "Order Analytics",
		"label": "Order Analytics",
		"icon": "octicon octicon-graph",
		"color": "#5e64ff",
		"restrict_to_domain": None,
	},
}

# Show this app in the /desk apps screen (top-left app switcher + home tiles)
add_to_apps_screen = [
	{
		"name": "order_analytics",
		"logo": "/assets/order_analytics/logo.png",
		"title": "Order Analytics",
		"route": "/app/order-analytics",
	},
]

# ---- Page static assets (enable as needed) ----
# app_include_css = "/assets/order_analytics/css/order_analytics.css"
# app_include_js = "/assets/order_analytics/js/order_analytics.js"

# ---- Website routes (this app is Desk-only, no website entry needed) ----
# website_route_rules = []

# ---- Document events (amount totals are handled inside the DocType class) ----
# doc_events = {}
