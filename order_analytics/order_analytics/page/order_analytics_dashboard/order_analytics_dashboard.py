# Copyright (c) 2026, Order Analytics
# MIT License. See license

import frappe

from order_analytics.order_analytics.report.customer_purchase_analysis.customer_purchase_analysis import (
	execute,
)


@frappe.whitelist()
def get_data(from_date=None, to_date=None):
	"""供看板页面调用：复用报表的客户聚合逻辑，另加月度趋势。"""
	filters = frappe._dict({"from_date": from_date, "to_date": to_date})
	_columns, rows, _message, _chart, summary = execute(filters)

	monthly_trend = frappe.db.sql(
		"""
		SELECT
			DATE_FORMAT(transaction_date, '%%Y-%%m') AS month,
			COUNT(*) AS order_count,
			COALESCE(SUM(total_amount), 0) AS total_amount
		FROM `tabCustomer Order`
		WHERE docstatus = 1
			AND (%(from_date)s IS NULL OR transaction_date >= %(from_date)s)
			AND (%(to_date)s IS NULL OR transaction_date <= %(to_date)s)
		GROUP BY month
		ORDER BY month ASC
		""",
		{"from_date": from_date, "to_date": to_date},
		as_dict=True,
	)

	return {
		"summary": summary,
		"top_customers": rows[:10],
		"monthly_trend": monthly_trend,
	}
