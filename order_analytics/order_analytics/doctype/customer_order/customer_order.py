# Copyright (c) 2026, Order Analytics
# MIT License. See license

from frappe.model.document import Document
from frappe.utils import flt


class CustomerOrder(Document):
	def validate(self):
		# Back-end fallback calculation: runs for UI entry, Excel/CSV import, and API writes
		# so quantities and amounts are always consistent.
		self.calculate_totals()

	def calculate_totals(self):
		total_qty = 0.0
		total_amount = 0.0

		for item in self.items:
			item.amount = flt(item.qty) * flt(item.rate)
			total_qty += flt(item.qty)
			total_amount += item.amount

		self.total_qty = flt(total_qty, self.precision("total_qty"))
		self.total_amount = flt(total_amount, self.precision("total_amount"))
