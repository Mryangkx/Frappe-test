"""安装与迁移后的初始化逻辑。

核心 DocType / Report / Page 的 JSON 只授予 Frappe 必定存在的 System Manager 角色，
这样本应用在纯 Frappe 站点上也能顺利 migrate。
当站点装有 ERPNext 时，这里再把访问权限补授给 Sales User / Sales Manager。
"""

import frappe

# 角色 -> Customer Order 权限
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
	grant_sales_permissions()


def after_migrate():
	grant_sales_permissions()


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

	frappe.db.commit()


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
