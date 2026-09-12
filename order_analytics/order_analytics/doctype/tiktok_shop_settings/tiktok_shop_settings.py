# Copyright (c) 2026, Order Analytics
# MIT License. See license

from datetime import datetime, timedelta

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import now_datetime

from order_analytics.order_analytics.utils.tiktok_client import (
	TikTokAPIError,
	get_tiktok_settings,
	make_client_from_settings,
)


class TikTokShopSettings(Document):
	def validate(self):
		"""When auto-sync is enabled and no next sync time is set, schedule the first run."""
		if self.auto_sync_enabled and not self.next_sync_time:
			interval = int(self.sync_interval_hours or 24)
			self.next_sync_time = now_datetime() + timedelta(hours=interval)


@frappe.whitelist()
def sync_tiktok_orders(from_date=None, to_date=None, days=None):
	"""Pull orders from TikTok Shop and import them as Customer Order documents.

	This is the entry point for MANUAL sync (called from the list view button).

	Orders that already exist (matched by external_order_id) are SKIPPED, never
	overwritten — so re-running a sync for an overlapping window is safe.

	Parameters
	----------
	from_date : str, optional
		Start date (YYYY-MM-DD). If omitted, defaults to *days* ago, or to the
		configured lookback window when *days* is also None.
	to_date : str, optional
		End date (YYYY-MM-DD). Defaults to now.
	days : int, optional
		How many days back to pull when from_date is not given.

	Returns a summary dict with counts.
	"""
	settings = get_tiktok_settings()

	# Resolve the time window
	if from_date:
		create_time_from = int(datetime.strptime(from_date, "%Y-%m-%d").timestamp())
	else:
		if days is not None:
			lookback_hours = days * 24
		else:
			lookback_hours = int(settings.sync_lookback_hours or 24)
		create_time_from = int((datetime.utcnow() - timedelta(hours=lookback_hours)).timestamp())

	if to_date:
		create_time_to = int(
			(datetime.strptime(to_date, "%Y-%m-%d") + timedelta(days=1)).timestamp()
		) - 1
	else:
		create_time_to = int(datetime.utcnow().timestamp())

	return _run_sync(settings, create_time_from, create_time_to, silent=False)


@frappe.whitelist()
def run_scheduled_sync():
	"""Called by the Frappe scheduler (see hooks.py scheduler_events).

	Checks whether automatic sync is enabled and whether the scheduled time has
	arrived. If so, runs an incremental sync using the configured lookback
	window and reschedules the next run.
	"""
	settings = get_tiktok_settings()

	if not settings.auto_sync_enabled:
		return {"skipped": True, "reason": "Auto sync is disabled"}

	now = now_datetime()
	next_sync = settings.next_sync_time

	# If no next sync time is set, schedule one and wait for the next tick
	if not next_sync:
		interval = int(settings.sync_interval_hours or 24)
		settings.next_sync_time = now + timedelta(hours=interval)
		settings.save(ignore_permissions=True)
		frappe.db.commit()
		return {"skipped": True, "reason": "First sync scheduled"}

	# Not yet time
	if frappe.utils.get_datetime(next_sync) > now:
		return {"skipped": True, "reason": "Not yet time"}

	# Run incremental sync using the lookback window
	lookback_hours = int(settings.sync_lookback_hours or 24)
	create_time_from = int((datetime.utcnow() - timedelta(hours=lookback_hours)).timestamp())
	create_time_to = int(datetime.utcnow().timestamp())

	result = _run_sync(settings, create_time_from, create_time_to, silent=True)

	# Schedule the next run regardless of success/failure so the scheduler keeps ticking
	interval = int(settings.sync_interval_hours or 24)
	settings.next_sync_time = now + timedelta(hours=interval)
	settings.save(ignore_permissions=True)
	frappe.db.commit()

	return result


def _run_sync(settings, create_time_from, create_time_to, silent=False):
	"""Core sync logic shared by manual and scheduled sync.

	Orders are matched by external_order_id. Existing orders are never modified
	or overwritten; they are simply skipped.
	"""
	try:
		client = make_client_from_settings(settings)
		orders = client.search_orders(create_time_from, create_time_to)
	except TikTokAPIError as exc:
		settings.last_sync_status = "Failed"
		settings.last_sync_message = str(exc)
		settings.last_sync_time = now_datetime()
		settings.save(ignore_permissions=True)
		frappe.db.commit()
		if not silent:
			frappe.throw(_("TikTok Shop sync failed: {0}").format(exc))
		frappe.log_error(str(exc), "TikTok Shop Scheduled Sync")
		return {"imported": 0, "skipped": 0, "errors": [str(exc)], "total_fetched": 0}

	imported = 0
	skipped = 0
	errors = []

	for raw_order in orders:
		order_id = raw_order.get("order_id")
		if not order_id:
			continue

		# ---- Dedup: never overwrite an existing order ----
		# If an order with the same external_order_id (and TikTok Shop source)
		# already exists, skip it entirely. The existing record is left untouched.
		if frappe.db.exists(
			"Customer Order",
			{"external_order_id": order_id, "source": "TikTok Shop"},
		):
			skipped += 1
			continue

		try:
			_import_tiktok_order(raw_order, settings)
			imported += 1
		except Exception as exc:  # noqa: BLE001 - per-order errors must not stop the sync
			errors.append(f"Order {order_id}: {exc}")
			frappe.log_error(
				f"Failed to import TikTok order {order_id}: {exc}",
				"TikTok Shop Sync",
			)

	# Commit all imported orders
	frappe.db.commit()

	status = "Failed" if (not imported and errors) else "Success"
	message = (
		f"Imported {imported} new order(s), skipped {skipped} existing order(s)."
		+ (f" Errors: {'; '.join(errors[:5])}" if errors else "")
	)

	settings.last_sync_status = status
	settings.last_sync_message = message
	settings.last_sync_time = now_datetime()
	settings.save(ignore_permissions=True)
	frappe.db.commit()

	if not silent:
		frappe.msgprint(_(message))

	return {
		"imported": imported,
		"skipped": skipped,
		"errors": errors,
		"total_fetched": len(orders),
		"message": message,
	}


def _import_tiktok_order(raw_order, settings):
	"""Map a raw TikTok order dict to a Customer Order doc and submit it."""
	order_id = raw_order.get("order_id")

	# Buyer identification: TikTok does not always expose the buyer's real name.
	# We use buyer_user_id as the customer key, falling back to buyer_email if available.
	buyer_user_id = raw_order.get("buyer_user_id") or f"tt_{order_id}"
	buyer_email = raw_order.get("buyer_email") or ""
	customer_name = (
		buyer_email.split("@")[0]
		if "@" in buyer_email
		else f"TikTok Buyer {buyer_user_id[-6:]}"
	)

	# Order date (TikTok uses unix timestamps in seconds)
	create_time = raw_order.get("create_time")
	transaction_date = (
		datetime.utcfromtimestamp(create_time).strftime("%Y-%m-%d") if create_time else None
	)

	# Currency and total amount from payment info
	payment_list = raw_order.get("payment") or []
	currency = "GBP"
	total_amount = 0.0
	if payment_list:
		currency = payment_list[0].get("currency") or "GBP"
		total_amount = float(payment_list[0].get("amount") or 0)

	# Build item rows
	items = []
	item_list = raw_order.get("item_list") or []
	for item in item_list:
		qty = float(item.get("quantity") or 0)
		# Try to derive a unit price from the item; TikTok item_list may include
		# a sale_price field. If absent, distribute the order total proportionally.
		rate = float(item.get("sale_price") or item.get("price") or 0)
		if not rate and qty and total_amount:
			# Fallback: split total evenly across items (rough estimate)
			rate = total_amount / max(len(item_list), 1) / qty if qty else 0

		items.append(
			{
				"item_code": item.get("seller_sku") or item.get("product_id") or "UNKNOWN",
				"item_name": item.get("product_name") or item.get("sku_id") or "Item",
				"qty": qty,
				"uom": "Unit",
				"rate": rate,
			}
		)

	if not items:
		# Some order search responses omit item details; create a placeholder line
		items.append(
			{
				"item_code": "TT-TOTAL",
				"item_name": f"TikTok Order {order_id}",
				"qty": 1,
				"uom": "Unit",
				"rate": total_amount,
			}
		)

	# Build the Customer Order
	order_doc = frappe.new_doc("Customer Order")
	order_doc.naming_series = "OA-.YYYY.-.#####"
	order_doc.customer = customer_name
	order_doc.transaction_date = transaction_date
	order_doc.currency = currency
	order_doc.source = "TikTok Shop"
	order_doc.external_order_id = order_id
	order_doc.buyer_user_id = buyer_user_id
	order_doc.external_order_url = (
		f"https://seller.tiktokglobalshop.com/order/detail?order_id={order_id}"
	)
	order_doc.notes = f"Imported from TikTok Shop. Order status: {raw_order.get('status')}"

	for item in items:
		order_doc.append("items", item)

	order_doc.insert(ignore_permissions=True)
	order_doc.submit()

	return order_doc
