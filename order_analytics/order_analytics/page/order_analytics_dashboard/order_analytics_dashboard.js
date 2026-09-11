// Copyright (c) 2026, Order Analytics
// MIT License. See license

frappe.pages["order-analytics-dashboard"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __("订单分析看板"),
		single_column: true,
	});

	const today = frappe.datetime.get_today();

	page.from_date = page.add_field({
		fieldname: "from_date",
		label: __("开始日期"),
		fieldtype: "Date",
		default: frappe.datetime.add_months(today, -12),
	});

	page.to_date = page.add_field({
		fieldname: "to_date",
		label: __("结束日期"),
		fieldtype: "Date",
		default: today,
	});

	page.set_primary_action(__("查询"), () => load_data());

	page.main.html(`
		<div class="oa-kpi-row row"></div>
		<div class="row" style="margin-top: var(--margin-sm)">
			<div class="col-sm-12">
				<div class="oa-top-card card"></div>
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
			`<div class="col-sm-12 text-muted text-center">${__("加载中...")}</div>`
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
				.html(`<div class="col-sm-12 text-center">${__("数据加载失败")}: ${error.message}</div>`);
		}
	}

	function render(data) {
		render_kpis(data.summary || []);
		render_top_customers(data.top_customers || []);
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
		$(`<div class="card-header">${__("客户消费排行 Top 10")}</div>`).appendTo(card);
		const body = $(`<div class="card-body oa-top-chart"></div>`).appendTo(card);

		if (!rows.length) {
			body.html(`<div class="text-muted text-center">${__("暂无已提交的订单数据")}</div>`);
			return;
		}

		const labels = rows.map((row) => row.customer);
		const values = rows.map((row) => flt(row.total_amount));

		if (frappe.Chart) {
			new frappe.Chart(body.get(0), {
				data: {
					labels: labels,
					datasets: [{ name: __("消费总金额"), values: values }],
				},
				type: "bar",
				height: 300,
				colors: ["#5e64ff"],
				barOptions: { height: "20px", stacked: false },
			});
		} else {
			render_fallback_table(body, [
				{ label: __("客户"), field: "customer" },
				{ label: __("消费总金额"), field: "total_amount", format: (v) => format_currency(v) },
			], rows);
		}
	}

	function render_monthly_trend(rows) {
		const card = page.main.find(".oa-trend-card").empty();
		$(`<div class="card-header">${__("月度销售趋势")}</div>`).appendTo(card);
		const body = $(`<div class="card-body oa-trend-chart"></div>`).appendTo(card);

		if (!rows.length) {
			body.html(`<div class="text-muted text-center">${__("所选区间暂无数据")}</div>`);
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
						{ name: __("销售总额"), values: amounts, chartType: "line" },
						{ name: __("订单数"), values: counts, chartType: "bar" },
					],
				},
				type: "axis-mixed",
				height: 300,
				colors: ["#5e64ff", "#63c688"],
				axisOptions: { xIsSeries: true },
			});
		} else {
			render_fallback_table(body, [
				{ label: __("月份"), field: "month" },
				{ label: __("订单数"), field: "order_count" },
				{ label: __("销售总额"), field: "total_amount", format: (v) => format_currency(v) },
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
