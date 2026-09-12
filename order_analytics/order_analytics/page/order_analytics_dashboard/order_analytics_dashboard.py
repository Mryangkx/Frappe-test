# Copyright (c) 2026, Order Analytics
# MIT License. See license

import frappe

from order_analytics.order_analytics.report.customer_purchase_analysis.customer_purchase_analysis import (
	execute,
)


@frappe.whitelist()
def get_data(from_date=None, to_date=None):
	"""Called by the dashboard page: reuses the report's customer aggregation
	and adds monthly trend, top products, and order source breakdown."""
	filters = frappe._dict({"from_date": from_date, "to_date": to_date})
	_columns, rows, _message, _chart, summary = execute(filters)

	date_filter = """
		AND (%(from_date)s IS NULL OR co.transaction_date >= %(from_date)s)
		AND (%(to_date)s IS NULL OR co.transaction_date <= %(to_date)s)
	"""
	params = {"from_date": from_date, "to_date": to_date}

	monthly_trend = frappe.db.sql(
		f"""
		SELECT
			DATE_FORMAT(co.transaction_date, '%%Y-%%m') AS month,
			COUNT(*) AS order_count,
			COALESCE(SUM(co.total_amount), 0) AS total_amount
		FROM `tabCustomer Order` co
		WHERE co.docstatus = 1
		{date_filter}
		GROUP BY month
		ORDER BY month ASC
		""",
		params,
		as_dict=True,
	)

	# Top 10 products by sales value (from the order item child table)
	top_products = frappe.db.sql(
		f"""
		SELECT
			COALESCE(NULLIF(oi.item_name, ''), oi.item_code) AS item_name,
			COUNT(*) AS line_count,
			COALESCE(SUM(oi.qty), 0) AS total_qty,
			COALESCE(SUM(oi.amount), 0) AS total_amount
		FROM `tabCustomer Order Item` oi
		INNER JOIN `tabCustomer Order` co ON co.name = oi.parent
		WHERE co.docstatus = 1
		{date_filter}
		GROUP BY item_name
		ORDER BY total_amount DESC
		LIMIT 10
		""",
		params,
		as_dict=True,
	)

	# Order source breakdown (Manual vs TikTok Shop)
	source_breakdown = frappe.db.sql(
		f"""
		SELECT
			COALESCE(co.source, 'Manual') AS source,
			COUNT(*) AS order_count,
			COALESCE(SUM(co.total_amount), 0) AS total_amount
		FROM `tabCustomer Order` co
		WHERE co.docstatus = 1
		{date_filter}
		GROUP BY source
		ORDER BY total_amount DESC
		""",
		params,
		as_dict=True,
	)

	return {
		"summary": summary,
		"top_customers": rows[:10],
		"monthly_trend": monthly_trend,
		"top_products": top_products,
		"source_breakdown": source_breakdown,
	}
