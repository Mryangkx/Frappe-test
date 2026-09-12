"""Initialization logic after install and migrate.

1. Ensure the Module Def exists and is configured (icon, label), so the module
   appears in the ERPNext sidebar.
2. Grant order / report / page permissions to ERPNext Sales User / Sales Manager
   roles (only when those roles exist; skipped on a plain Frappe site).
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

MANAGED_DOCTYPES = ["Customer Order"]
MANAGED_REPORTS = ["Customer Purchase Analysis"]
MANAGED_PAGES = ["order-analytics-dashboard"]


def after_install():
	setup_module_defs()
	grant_sales_permissions()
	frappe.db.commit()


def after_migrate():
	setup_module_defs()
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
