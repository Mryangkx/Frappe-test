// Copyright (c) 2026, Order Analytics
// MIT License. See license

frappe.query_reports["Customer Purchase Analysis"] = {
	filters: [
		{
			fieldname: "from_date",
			label: __("开始日期"),
			fieldtype: "Date",
			default: frappe.datetime.add_months(frappe.datetime.get_today(), -12),
			reqd: 1,
		},
		{
			fieldname: "to_date",
			label: __("结束日期"),
			fieldtype: "Date",
			default: frappe.datetime.get_today(),
			reqd: 1,
		},
		{
			fieldname: "customer",
			label: __("客户"),
			fieldtype: "Data",
			description: __("按客户名称模糊筛选，留空统计全部客户"),
		},
		{
			fieldname: "include_drafts",
			label: __("包含草稿订单"),
			fieldtype: "Check",
			description: __("默认只统计已提交订单"),
		},
	],
};
