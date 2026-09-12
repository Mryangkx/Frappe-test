// Copyright (c) 2026, Order Analytics
// MIT License. See license

frappe.listview_settings["Customer Order"] = {
	onload(listview) {
		// Add a "Sync from TikTok Shop" button to the list view toolbar
		listview.page.add_inner_button(
			__("Sync from TikTok Shop"),
			function () {
				sync_from_tiktok(listview);
			},
			"TikTok"
		);
	},
};

function sync_from_tiktok(listview) {
	const dialog = new frappe.ui.Dialog({
		title: __("Sync Orders from TikTok Shop"),
		fields: [
			{
				fieldname: "from_date",
				label: __("From Date"),
				fieldtype: "Date",
				default: frappe.datetime.add_days(frappe.datetime.get_today(), -30),
				reqd: 1,
			},
			{
				fieldname: "to_date",
				label: __("To Date"),
				fieldtype: "Date",
				default: frappe.datetime.get_today(),
				reqd: 1,
			},
		],
		primary_action_label: __("Start Sync"),
		primary_action(values) {
			dialog.hide();
			frappe.call({
				method:
					"order_analytics.order_analytics.doctype.tiktok_shop_settings.tiktok_shop_settings.sync_tiktok_orders",
				args: {
					from_date: values.from_date,
					to_date: values.to_date,
				},
				freeze: true,
				freeze_message: __("Syncing orders from TikTok Shop..."),
				callback(r) {
					if (r.message) {
						frappe.show_alert({
							message: __(
								`Synced: ${r.message.imported} imported, ${r.message.skipped} skipped`
							),
							indicator: r.message.imported ? "green" : "blue",
						});
						listview.refresh();
					}
				},
			});
		},
	});

	dialog.show();
}
