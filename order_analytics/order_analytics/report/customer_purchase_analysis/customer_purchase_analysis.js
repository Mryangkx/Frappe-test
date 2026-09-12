// Copyright (c) 2026, Order Analytics
// MIT License. See license

frappe.query_reports["Customer Purchase Analysis"] = {
	filters: [
		{
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
			default: frappe.datetime.add_months(frappe.datetime.get_today(), -12),
			reqd: 1,
		},
		{
			fieldname: "to_date",
			label: __("To Date"),
			fieldtype: "Date",
			default: frappe.datetime.get_today(),
			reqd: 1,
		},
		{
			fieldname: "customer",
			label: __("Customer"),
			fieldtype: "Data",
			description: __("Filter by customer name (fuzzy). Leave blank for all customers."),
		},
		{
			fieldname: "include_drafts",
			label: __("Include Draft Orders"),
			fieldtype: "Check",
			description: __("Only submitted orders are counted by default"),
		},
	],
};
