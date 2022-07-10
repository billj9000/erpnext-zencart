from setuptools import setup, find_packages

with open("requirements.txt") as f:
	install_requires = f.read().strip().split("\n")

# get version from __version__ variable in zencart/__init__.py
from zencart import __version__ as version

setup(
	name="zencart",
	version=version,
	description="Zen Cart connector",
	author="Bill Jones",
	author_email="billj@saabits.com",
	packages=find_packages(),
	zip_safe=False,
	include_package_data=True,
	install_requires=install_requires
)
