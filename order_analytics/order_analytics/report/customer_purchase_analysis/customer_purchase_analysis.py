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
			"label": _("排名"),
			"fieldname": "rank",
			"fieldtype": "Data",
			"width": 60,
		},
		{
			"label": _("客户"),
			"fieldname": "customer",
			"fieldtype": "Data",
			"width": 220,
		},
		{
			"label": _("订单数"),
			"fieldname": "order_count",
			"fieldtype": "Int",
			"width": 90,
		},
		{
			"label": _("商品总数量"),
			"fieldname": "total_qty",
			"fieldtype": "Float",
			"width": 110,
		},
		{
			"label": _("消费总金额"),
			"fieldname": "total_amount",
			"fieldtype": "Currency",
			"width": 140,
		},
		{
			"label": _("平均客单价"),
			"fieldname": "avg_order_amount",
			"fieldtype": "Currency",
			"width": 130,
		},
		{
			"label": _("首次购买日期"),
			"fieldname": "first_order_date",
			"fieldtype": "Date",
			"width": 130,
		},
		{
			"label": _("最近购买日期"),
			"fieldname": "last_order_date",
			"fieldtype": "Date",
			"width": 130,
		},
	]


def get_data(filters):
	# 默认只统计已提交(docstatus=1)的订单；勾选“包含草稿”时纳入草稿，但始终排除已取消(docstatus=2)
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

	# 数量与金额在订单头上已有冗余汇总，单表聚合即可，避免 JOIN 子表导致金额按明细行数翻倍
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

	# 排名在 Python 中生成，兼容各版本数据库
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
					"name": _("消费总金额"),
					"values": [row.total_amount for row in top_customers],
				}
			],
		},
		"type": "bar",
		"title": _("客户消费排行 Top 10"),
		"height": 280,
		"colors": ["#5e64ff"],
	}


def get_summary(data):
	total_amount = sum(row.total_amount for row in data)
	total_orders = sum(row.order_count for row in data)
	total_qty = sum(row.total_qty for row in data)
	avg_order_value = total_amount / total_orders if total_orders else 0

	return [
		{"label": _("客户数"), "value": len(data), "datatype": "Int"},
		{"label": _("订单总数"), "value": total_orders, "datatype": "Int"},
		{"label": _("商品总数量"), "value": flt(total_qty), "datatype": "Float"},
		{"label": _("销售总额"), "value": flt(total_amount), "datatype": "Currency"},
		{"label": _("平均客单价"), "value": flt(avg_order_value), "datatype": "Currency"},
	]
