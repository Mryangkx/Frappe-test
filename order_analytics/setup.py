"""Initialization logic after install and migrate.

1. Ensure the Module Def exists and is configured (icon, label), so the module
   appears in the ERPNext sidebar.
2. Grant order / report / page permissions to ERPNext Sales User / Sales Manager
   roles (only when those roles exist; skipped on a plain Frappe site).
3. Force-update any stale Chinese labels left in the database from earlier
   migrations (Page title, DocField labels, etc.).
"""

import frappe

# Module definition configuration
MODULE_DEFS = {
	"Order Analytics": {
		"module_name": "Order Analytics",
		"label": "Order Analytics",
		"icon": "octicon octicon-graph",
		"color": "#5e64ff",
		"app": "order_analytics",
		"restrict_to_domain": None,
	}
}

# Role -> Customer Order permissions
SALES_DOCTYPE_PERMISSIONS = {
	"Sales User": {
		"read": 1,
		"create": 1,
		"write": 1,
		"email": 1,
		"print": 1,
		"report": 1,
		"export": 1,
		"share": 1,
	},
	"Sales Manager": {
		"read": 1,
		"create": 1,
		"write": 1,
		"delete": 1,
		"submit": 1,
		"cancel": 1,
		"amend": 1,
		"email": 1,
		"print": 1,
		"report": 1,
		"export": 1,
		"share": 1,
	},
}

MANAGED_DOCTYPES = ["Customer Order", "Customer Order Item", "TikTok Shop Settings"]
MANAGED_REPORTS = ["Customer Purchase Analysis"]
MANAGED_PAGES = ["order-analytics-dashboard"]

# Force-correct any stale Chinese labels that may remain in the DB from
# earlier migrations. Keyed by (doctype, docname, fieldname) -> new value.
STALE_LABEL_FIXES = {
	("Page", "order-analytics-dashboard", "title"): "Order Analytics Dashboard",
	("Page", "order-analytics-dashboard", "module"): "Order Analytics",
	("Module Def", "Order Analytics", "label"): "Order Analytics",
	("Module Def", "Order Analytics", "app"): "order_analytics",
}


def after_install():
	setup_module_defs()
	fix_stale_labels()
	grant_sales_permissions()
	frappe.db.commit()


def after_migrate():
	setup_module_defs()
	fix_stale_labels()
	grant_sales_permissions()
	frappe.db.commit()


def setup_module_defs():
	"""Ensure the Module Def exists and is configured with icon / label
	so the module shows in the sidebar."""
	for module_name, defs in MODULE_DEFS.items():
		if frappe.db.exists("Module Def", module_name):
			doc = frappe.get_doc("Module Def", module_name)
		else:
			doc = frappe.new_doc("Module Def")
			doc.module_name = module_name

		doc.app = defs.get("app", "order_analytics")
		doc.label = defs.get("label", module_name)
		doc.icon = defs.get("icon", "octicon octicon-graph")
		doc.color = defs.get("color", "#5e64ff")
		doc.restrict_to_domain = defs.get("restrict_to_domain")
		doc.save(ignore_permissions=True)

	# Explicitly set the name field too (some Frappe versions need it)
	frappe.db.set_value("Module Def", "Order Analytics", "name", "Order Analytics")


def fix_stale_labels():
	"""Overwrite any stale Chinese labels in the database with English.

	Run on every migrate so the UI never shows old Chinese text.
	"""
	for (doctype, docname, fieldname), value in STALE_LABEL_FIXES.items():
		if frappe.db.exists(doctype, docname):
			frappe.db.set_value(doctype, docname, fieldname, value)

	# Fix DocField labels for Customer Order if any Chinese slipped through
	customer_order_field_labels = {
		"naming_series": "Naming Series",
		"customer": "Customer",
		"transaction_date": "Order Date",
		"currency": "Currency",
		"total_qty": "Total Quantity",
		"total_amount": "Total Amount",
		"source": "Source",
		"external_order_id": "External Order ID",
		"external_order_url": "External Order URL",
		"buyer_user_id": "Buyer User ID",
		"amended_from": "Amended From",
		"items": "Order Items",
		"notes": "Notes",
	}
	for fieldname, label in customer_order_field_labels.items():
		frappe.db.sql(
			"UPDATE `tabDocField` SET label = %s WHERE parent = 'Customer Order' AND fieldname = %s",
			(label, fieldname),
		)

	customer_order_item_labels = {
		"item_code": "Item Code",
		"item_name": "Item Name",
		"qty": "Qty",
		"uom": "UOM",
		"rate": "Rate",
		"amount": "Amount",
	}
	for fieldname, label in customer_order_item_labels.items():
		frappe.db.sql(
			"UPDATE `tabDocField` SET label = %s WHERE parent = 'Customer Order Item' AND fieldname = %s",
			(label, fieldname),
		)


def grant_sales_permissions():
	for role, permissions in SALES_DOCTYPE_PERMISSIONS.items():
		if not frappe.db.exists("Role", role):
			continue

		for doctype in MANAGED_DOCTYPES:
			add_docperm(doctype, role, permissions)

		for report in MANAGED_REPORTS:
			add_has_role("Report", report, role)

		for page in MANAGED_PAGES:
			add_has_role("Page", page, role)


def add_docperm(doctype, role, permissions):
	if frappe.db.exists(
		"DocPerm", {"parent": doctype, "role": role, "permlevel": 0}
	):
		return

	docperm = frappe.new_doc("DocPerm")
	docperm.parent = doctype
	docperm.parenttype = "DocType"
	docperm.parentfield = "permissions"
	docperm.role = role
	docperm.permlevel = 0
	for key, value in permissions.items():
		setattr(docperm, key, value)
	docperm.insert(ignore_permissions=True)


def add_has_role(parenttype, parent, role):
	if frappe.db.exists(
		"Has Role", {"parenttype": parenttype, "parent": parent, "role": role}
	):
		return

	has_role = frappe.new_doc("Has Role")
	has_role.parenttype = parenttype
	has_role.parentfield = "roles"
	has_role.parent = parent
	has_role.role = role
	has_role.insert(ignore_permissions=True)
