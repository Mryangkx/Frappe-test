# -*- coding: utf-8 -*-
# Compatibility entry point for older bench versions (Frappe v15+ uses pyproject.toml)
from setuptools import setup, find_packages

with open("requirements.txt") as f:
	install_requires = f.read().strip().split("\n")

setup(
	name="order_analytics",
	version="0.0.1",
	description="Customer order import and purchase analytics for ERPNext",
	author="Order Analytics",
	author_email="admin@example.com",
	packages=find_packages(),
	zip_safe=False,
	include_package_data=True,
	install_requires=install_requires,
)
