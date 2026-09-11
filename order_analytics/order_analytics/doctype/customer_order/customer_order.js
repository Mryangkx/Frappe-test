// Copyright (c) 2026, Order Analytics
// MIT License. See license

frappe.ui.form.on("Customer Order", {
	calculate_totals(frm) {
		let total_qty = 0;
		let total_amount = 0;

		(frm.doc.items || []).forEach((row) => {
			total_qty += flt(row.qty);
			total_amount += flt(row.amount);
		});

		frm.set_value("total_qty", total_qty);
		frm.set_value("total_amount", total_amount);
	},
	items_remove(frm) {
		frm.trigger("calculate_totals");
	},
});

// 子表行内数量 / 单价变化时即时重算金额与合计
frappe.ui.form.on("Customer Order Item", {
	qty(frm, cdt, cdn) {
		recalculate_row(frm, cdt, cdn);
	},
	rate(frm, cdt, cdn) {
		recalculate_row(frm, cdt, cdn);
	},
});

function recalculate_row(frm, cdt, cdn) {
	const row = locals[cdt][cdn];
	row.amount = flt(row.qty) * flt(row.rate);
	frm.refresh_field("items");
	frm.trigger("calculate_totals");
}
