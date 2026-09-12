// Copyright (c) 2026, Order Analytics
// MIT License. See license

frappe.pages["order-analytics-dashboard"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __("Order Analytics Dashboard"),
		single_column: true,
	});

	const today = frappe.datetime.get_today();

	page.from_date = page.add_field({
		fieldname: "from_date",
		label: __("From Date"),
		fieldtype: "Date",
		default: frappe.datetime.add_months(today, -12),
	});

	page.to_date = page.add_field({
		fieldname: "to_date",
		label: __("To Date"),
		fieldtype: "Date",
		default: today,
	});

	page.set_primary_action(__("Refresh"), () => load_data());

	page.main.html(`
		<div class="oa-kpi-row row"></div>
		<div class="row" style="margin-top: var(--margin-sm)">
			<div class="col-sm-12">
				<div class="oa-top-card card"></div>
			</div>
		</div>
		<div class="row" style="margin-top: var(--margin-sm)">
			<div class="col-sm-8">
				<div class="oa-products-card card"></div>
			</div>
			<div class="col-sm-4">
				<div class="oa-source-card card"></div>
			</div>
		</div>
		<div class="row" style="margin-top: var(--margin-sm)">
			<div class="col-sm-12">
				<div class="oa-trend-card card"></div>
			</div>
		</div>
	`);

	load_data();

	async function load_data() {
		page.main.find(".oa-kpi-row").html(
			`<div class="col-sm-12 text-muted text-center">${__("Loading...")}</div>`
		);

		try {
			const data = await frappe.xcall(
				"order_analytics.page.order_analytics_dashboard.order_analytics_dashboard.get_data",
				{
					from_date: page.from_date.get_value(),
					to_date: page.to_date.get_value(),
				}
			);
			render(data);
		} catch (error) {
			page.main
				.find(".oa-kpi-row")
				.html(`<div class="col-sm-12 text-center">${__("Failed to load data")}: ${error.message}</div>`);
		}
	}

	function render(data) {
		render_kpis(data.summary || []);
		render_top_customers(data.top_customers || []);
		render_top_products(data.top_products || []);
		render_source_breakdown(data.source_breakdown || []);
		render_monthly_trend(data.monthly_trend || []);
	}

	function render_kpis(summary) {
		const container = page.main.find(".oa-kpi-row").empty();

		summary.forEach((item) => {
			let value = item.value;
			if (item.datatype === "Currency") {
				value = format_currency(value);
			} else if (item.datatype === "Float") {
				value = format_number(value, null, 2);
			} else {
				value = cint(value);
			}

			$(`
				<div class="col-sm">
					<div class="card p-4">
						<div class="text-muted" style="font-size: var(--text-sm)">${item.label}</div>
						<div style="font-size: 22px; font-weight: 600; margin-top: 4px">${value}</div>
					</div>
				</div>
			`).appendTo(container);
		});
	}

	function render_top_customers(rows) {
		const card = page.main.find(".oa-top-card").empty();
		$(`<div class="card-header">${__("Top 10 Customers by Spend")}</div>`).appendTo(card);
		const body = $(`<div class="card-body oa-top-chart"></div>`).appendTo(card);

		if (!rows.length) {
			body.html(`<div class="text-muted text-center">${__("No submitted orders yet")}</div>`);
			return;
		}

		const labels = rows.map((row) => row.customer);
		const values = rows.map((row) => flt(row.total_amount));

		if (frappe.Chart) {
			new frappe.Chart(body.get(0), {
				data: {
					labels: labels,
					datasets: [{ name: __("Total Amount"), values: values }],
				},
				type: "bar",
				height: 300,
				colors: ["#5e64ff"],
				barOptions: { stacked: false },
			});
		} else {
			render_fallback_table(body, [
				{ label: __("Customer"), field: "customer" },
				{ label: __("Total Amount"), field: "total_amount", format: (v) => format_currency(v) },
			], rows);
		}
	}

	function render_top_products(rows) {
		const card = page.main.find(".oa-products-card").empty();
		$(`<div class="card-header">${__("Top 10 Products by Sales")}</div>`).appendTo(card);
		const body = $(`<div class="card-body oa-products-chart"></div>`).appendTo(card);

		if (!rows.length) {
			body.html(`<div class="text-muted text-center">${__("No product data available")}</div>`);
			return;
		}

		// Reverse so the highest value appears at the top of the horizontal bar chart
		const sorted = [...rows].reverse();
		const labels = sorted.map((row) => row.item_name);
		const values = sorted.map((row) => flt(row.total_amount));

		if (frappe.Chart) {
			new frappe.Chart(body.get(0), {
				data: {
					labels: labels,
					datasets: [{ name: __("Sales Value"), values: values }],
				},
				type: "bar",
				height: 360,
				colors: ["#63c688"],
				barOptions: { stacked: false },
				axisOptions: { xIsSeries: false },
			});
		} else {
			render_fallback_table(body, [
				{ label: __("Product"), field: "item_name" },
				{ label: __("Qty Sold"), field: "total_qty" },
				{ label: __("Sales Value"), field: "total_amount", format: (v) => format_currency(v) },
			], rows);
		}
	}

	function render_source_breakdown(rows) {
		const card = page.main.find(".oa-source-card").empty();
		$(`<div class="card-header">${__("Orders by Source")}</div>`).appendTo(card);
		const body = $(`<div class="card-body oa-source-chart"></div>`).appendTo(card);

		if (!rows.length) {
			body.html(`<div class="text-muted text-center">${__("No data for the selected period")}</div>`);
			return;
		}

		const labels = rows.map((row) => row.source);
		const values = rows.map((row) => cint(row.order_count));

		if (frappe.Chart) {
			new frappe.Chart(body.get(0), {
				data: {
					labels: labels,
					datasets: [{ name: __("Order Count"), values: values }],
				},
				type: "donut",
				height: 260,
				colors: ["#5e64ff", "#63c688", "#ffa3ef", "#ffc400", "#ff7a45"],
			});
		} else {
			render_fallback_table(body, [
				{ label: __("Source"), field: "source" },
				{ label: __("Order Count"), field: "order_count" },
				{ label: __("Total Sales"), field: "total_amount", format: (v) => format_currency(v) },
			], rows);
		}
	}

	function render_monthly_trend(rows) {
		const card = page.main.find(".oa-trend-card").empty();
		$(`<div class="card-header">${__("Monthly Sales Trend")}</div>`).appendTo(card);
		const body = $(`<div class="card-body oa-trend-chart"></div>`).appendTo(card);

		if (!rows.length) {
			body.html(`<div class="text-muted text-center">${__("No data for the selected period")}</div>`);
			return;
		}

		const labels = rows.map((row) => row.month);
		const amounts = rows.map((row) => flt(row.total_amount));
		const counts = rows.map((row) => cint(row.order_count));

		if (frappe.Chart) {
			new frappe.Chart(body.get(0), {
				data: {
					labels: labels,
					datasets: [
						{ name: __("Total Sales"), values: amounts, chartType: "line" },
						{ name: __("Order Count"), values: counts, chartType: "bar" },
					],
				},
				type: "axis-mixed",
				height: 300,
				colors: ["#5e64ff", "#63c688"],
				axisOptions: { xIsSeries: true },
			});
		} else {
			render_fallback_table(body, [
				{ label: __("Month"), field: "month" },
				{ label: __("Order Count"), field: "order_count" },
				{ label: __("Total Sales"), field: "total_amount", format: (v) => format_currency(v) },
			], rows);
		}
	}

	function render_fallback_table(container, columns, rows) {
		const head = columns.map((col) => `<th>${col.label}</th>`).join("");
		const body_html = rows
			.map((row) => {
				const cells = columns
					.map((col) => {
						const value = col.format ? col.format(row[col.field]) : row[col.field];
						return `<td>${value}</td>`;
					})
					.join("");
				return `<tr>${cells}</tr>`;
			})
			.join("");

		container.html(`
			<table class="table table-bordered">
				<thead><tr>${head}</tr></thead>
				<tbody>${body_html}</tbody>
			</table>
		`);
	}
};
