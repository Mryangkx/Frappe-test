"""TikTok Shop Open API v2 client.

Implements:
  - HMAC-SHA256 request signing (x-tts-signature header)
  - Access token refresh
  - Order search with pagination
  - Order detail retrieval

Documentation: https://partner.tiktokshop.com/
"""

import hashlib
import hmac
import json
import time
from urllib.parse import urlencode

import frappe
import requests


# Region -> API base URL mapping
REGION_BASE_URLS = {
	"UK": "https://api.tiktokglobalshop.com",
	"US": "https://api-us.tiktokglobalshop.com",
	"TH": "https://api.tiktokglobalshop.com",
	"VN": "https://api.tiktokglobalshop.com",
	"ID": "https://api.tiktokglobalshop.com",
	"MY": "https://api.tiktokglobalshop.com",
	"PH": "https://api.tiktokglobalshop.com",
	"SG": "https://api.tiktokglobalshop.com",
	"JP": "https://api.tiktokglobalshop.com",
}

AUTH_URL = "https://auth.tiktok-shops.com"

# TikTok order statuses we consider "completed / paid" and worth analysing.
# 100 = Unpaid, 101 = Awaiting Shipment, 102 = Awaiting Collection,
# 103 = Partially Shipped, 104 = In Transit, 105 = Delivered,
# 111 = Cancel Requested, 112 = Cancelled, 121 = Refund Pending, 122 = Refunded
ANALYZABLE_ORDER_STATUSES = [101, 102, 103, 104, 105]


class TikTokAPIError(Exception):
	pass


class TikTokClient:
	def __init__(self, settings):
		"""settings: a TikTok Shop Settings doc (or frappe._dict with the same fields)."""
		self.app_key = settings.get("app_key")
		self.app_secret = settings.get("app_secret")
		self.access_token = settings.get("access_token")
		self.refresh_token = settings.get("refresh_token")
		self.shop_cipher = settings.get("shop_cipher")
		self.region = settings.get("shop_region") or "UK"
		self.is_sandbox = settings.get("is_sandbox")

		self.base_url = REGION_BASE_URLS.get(self.region, "https://api.tiktokglobalshop.com")
		if self.is_sandbox:
			self.base_url = "https://api-sandbox.tiktokglobalshop.com"

	# ------------------------------------------------------------------
	# Request signing
	# ------------------------------------------------------------------
	def _generate_signature(self, path, body, query_params=None, timestamp=None):
		"""Generate the x-tts-signature header value (v2 algorithm).

		Sign string = app_key + timestamp + access_token + sorted_query_string + body
		signature = HMAC-SHA256(sign_string, app_secret)
		header value = "v2." + signature_hex
		"""
		if timestamp is None:
			timestamp = str(int(time.time()))

		# Sort query parameters alphabetically
		query_string = ""
		if query_params:
			query_string = urlencode(sorted(query_params.items()))

		sign_string = (
			str(self.app_key)
			+ str(timestamp)
			+ str(self.access_token or "")
			+ query_string
			+ (body or "")
		)

		signature = hmac.new(
			str(self.app_secret).encode("utf-8"),
			sign_string.encode("utf-8"),
			hashlib.sha256,
		).hexdigest()

		return "v2." + signature, timestamp

	def _headers(self, path, body="", query_params=None):
		signature, timestamp = self._generate_signature(path, body, query_params)
		headers = {
			"Content-Type": "application/json",
			"x-tts-app-key": str(self.app_key),
			"x-tts-timestamp": timestamp,
			"x-tts-signature": signature,
		}
		if self.access_token:
			headers["x-tts-access-token"] = self.access_token
		if self.shop_cipher:
			headers["x-tts-shop-cipher"] = self.shop_cipher
		return headers

	def _request(self, method, path, query_params=None, body=None):
		url = self.base_url + path
		body_str = json.dumps(body) if body is not None else ""

		headers = self._headers(path, body_str, query_params)

		try:
			response = requests.request(
				method=method,
				url=url,
				params=query_params,
				headers=headers,
				data=body_str,
				timeout=30,
			)
		except requests.RequestException as exc:
			raise TikTokAPIError(f"Network error: {exc}")

		try:
			result = response.json()
		except ValueError:
			raise TikTokAPIError(f"Non-JSON response: {response.text[:200]}")

		if result.get("code") != 0:
			raise TikTokAPIError(
				f"TikTok API error code {result.get('code')}: {result.get('message', 'Unknown error')}"
			)

		return result.get("data", {})

	# ------------------------------------------------------------------
	# Auth
	# ------------------------------------------------------------------
	def refresh_access_token(self):
		"""Exchange refresh_token for a new access_token.

		Returns a dict with access_token, refresh_token, expire_in, etc.
		"""
		if not self.refresh_token:
			raise TikTokAPIError("Refresh token is not configured.")

		url = f"{AUTH_URL}/api/v2/token/refresh"
		params = {
			"app_key": self.app_key,
			"app_secret": self.app_secret,
			"refresh_token": self.refresh_token,
			"grant_type": "refresh_token",
		}

		try:
			response = requests.post(url, params=params, timeout=30)
			result = response.json()
		except (requests.RequestException, ValueError) as exc:
			raise TikTokAPIError(f"Token refresh failed: {exc}")

		if result.get("code") != 0:
			raise TikTokAPIError(
				f"Token refresh error code {result.get('code')}: {result.get('message', 'Unknown error')}"
			)

		data = result.get("data", {})
		self.access_token = data.get("access_token")
		self.refresh_token = data.get("refresh_token")
		return data

	# ------------------------------------------------------------------
	# Orders
	# ------------------------------------------------------------------
	def search_orders(self, create_time_from, create_time_to, order_statuses=None, page_size=100):
		"""Fetch all orders within a time range, handling pagination.

		Returns a list of order dicts.
		"""
		if order_statuses is None:
			order_statuses = ANALYZABLE_ORDER_STATUSES

		all_orders = []
		page_number = 1

		while True:
			body = {
				"shop_cipher": self.shop_cipher,
				"create_time_from": create_time_from,
				"create_time_to": create_time_to,
				"page_size": page_size,
				"page_number": page_number,
			}

			# TikTok requires order_status as a list in some API versions
			if order_statuses:
				body["order_status"] = order_statuses

			data = self._request("POST", "/api/v2/orders/search", body=body)

			orders = data.get("orders", [])
			all_orders.extend(orders)

			total = data.get("total", 0)
			if len(all_orders) >= total or not orders:
				break

			page_number += 1

			# Safety: avoid infinite loops
			if page_number > 100:
				frappe.log_error(
					f"TikTok order sync hit page limit (>100 pages), fetched {len(all_orders)} of {total}",
					"TikTok Shop Sync",
				)
				break

		return all_orders

	def get_order_detail(self, order_id):
		"""Fetch full detail for a single order (includes item list and payment)."""
		query_params = {"order_id": order_id}
		return self._request("GET", "/api/v2/orders/detail", query_params=query_params)


def get_tiktok_settings():
	"""Load the singleton TikTok Shop Settings doc.

	Returns a frappe._dict with all field values (Password fields are decrypted
	by Frappe when read via get_doc).
	"""
	doc = frappe.get_doc("TikTok Shop Settings")
	return doc


def make_client_from_settings(settings=None):
	"""Build a TikTokClient from settings, refreshing the access token first."""
	if settings is None:
		settings = get_tiktok_settings()

	if not settings.app_key or not settings.app_secret:
		raise TikTokAPIError("TikTok Shop API credentials are not configured.")

	client = TikTokClient(settings)

	# Refresh the access token on every sync to avoid expiry
	if settings.refresh_token:
		token_data = client.refresh_access_token()
		# Persist the refreshed tokens back to settings
		if token_data.get("access_token"):
			settings.access_token = token_data["access_token"]
		if token_data.get("refresh_token"):
			settings.refresh_token = token_data["refresh_token"]
		settings.save(ignore_permissions=True)

	return client
