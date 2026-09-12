# Copyright (c) 2026, Order Analytics
# MIT License. See license

import frappe
from frappe import _
from frappe.utils import flt


def execute(filters=None):
	filters = frappe._dict(filters or {})
	columns = get_columns()
	data = get_data(filters)
	chart = get_chart(data)
	summary = get_summary(data)
	return columns, data, None, chart, summary


def get_columns():
	return [
		{
			"label": _("Rank"),
			"fieldname": "rank",
			"fieldtype": "Data",
			"width": 60,
		},
		{
			"label": _("Customer"),
			"fieldname": "customer",
			"fieldtype": "Data",
			"width": 220,
		},
		{
			"label": _("Order Count"),
			"fieldname": "order_count",
			"fieldtype": "Int",
			"width": 110,
		},
		{
			"label": _("Total Quantity"),
			"fieldname": "total_qty",
			"fieldtype": "Float",
			"width": 120,
		},
		{
			"label": _("Total Amount"),
			"fieldname": "total_amount",
			"fieldtype": "Currency",
			"width": 150,
		},
		{
			"label": _("Avg Order Value"),
			"fieldname": "avg_order_amount",
			"fieldtype": "Currency",
			"width": 150,
		},
		{
			"label": _("First Order Date"),
			"fieldname": "first_order_date",
			"fieldtype": "Date",
			"width": 140,
		},
		{
			"label": _("Last Order Date"),
			"fieldname": "last_order_date",
			"fieldtype": "Date",
			"width": 140,
		},
	]


def get_data(filters):
	# By default only submitted orders (docstatus=1) are counted.
	# Tick "Include Drafts" to include drafts; cancelled orders (docstatus=2) are always excluded.
	conditions = ["co.docstatus < 2"]
	params = {}

	if not filters.include_drafts:
		conditions.append("co.docstatus = 1")

	if filters.from_date:
		conditions.append("co.transaction_date >= %(from_date)s")
		params["from_date"] = filters.from_date

	if filters.to_date:
		conditions.append("co.transaction_date <= %(to_date)s")
		params["to_date"] = filters.to_date

	if filters.customer:
		conditions.append("co.customer LIKE %(customer)s")
		params["customer"] = f"%{filters.customer}%"

	# Quantity and amount are already aggregated on the order header, so a single-table
	# aggregation is enough — avoids multiplying amounts by the number of item rows.
	rows = frappe.db.sql(
		"""
		SELECT
			co.customer AS customer,
			COUNT(*) AS order_count,
			COALESCE(SUM(co.total_qty), 0) AS total_qty,
			COALESCE(SUM(co.total_amount), 0) AS total_amount,
			COALESCE(AVG(co.total_amount), 0) AS avg_order_amount,
			MIN(co.transaction_date) AS first_order_date,
			MAX(co.transaction_date) AS last_order_date
		FROM `tabCustomer Order` co
		WHERE {conditions}
		GROUP BY co.customer
		ORDER BY total_amount DESC, order_count DESC, co.customer ASC
		""".format(conditions=" AND ".join(conditions)),
		params,
		as_dict=True,
	)

	# Rank is generated in Python for cross-database compatibility
	for index, row in enumerate(rows, start=1):
		row.rank = index
		row.total_amount = flt(row.total_amount)
		row.avg_order_amount = flt(row.avg_order_amount)
		row.total_qty = flt(row.total_qty)

	return rows


def get_chart(data):
	top_customers = data[:10]
	return {
		"data": {
			"labels": [row.customer for row in top_customers],
			"datasets": [
				{
					"name": _("Total Amount"),
					"values": [row.total_amount for row in top_customers],
				}
			],
		},
		"type": "bar",
		"title": _("Top 10 Customers by Spend"),
		"height": 280,
		"colors": ["#5e64ff"],
	}


def get_summary(data):
	total_amount = sum(row.total_amount for row in data)
	total_orders = sum(row.order_count for row in data)
	total_qty = sum(row.total_qty for row in data)
	avg_order_value = total_amount / total_orders if total_orders else 0

	return [
		{"label": _("Customers"), "value": len(data), "datatype": "Int"},
		{"label": _("Total Orders"), "value": total_orders, "datatype": "Int"},
		{"label": _("Total Quantity"), "value": flt(total_qty), "datatype": "Float"},
		{"label": _("Total Sales"), "value": flt(total_amount), "datatype": "Currency"},
		{"label": _("Avg Order Value"), "value": flt(avg_order_value), "datatype": "Currency"},
	]
