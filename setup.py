"""Setup script for Leads Scraper."""

from setuptools import setup, find_packages
from pathlib import Path

# Read README for long description
readme_file = Path(__file__).parent / "README.md"
long_description = readme_file.read_text() if readme_file.exists() else ""

# Read requirements
requirements_file = Path(__file__).parent / "requirements.txt"
if requirements_file.exists():
    with open(requirements_file) as f:
        requirements = [
            line.strip()
            for line in f
            if line.strip() and not line.startswith('#') and not line.startswith('python')
        ]
else:
    requirements = []

setup(
    name="leads-scraper",
    version="1.0.0",
    author="Leads Scraper Team",
    author_email="",
    description="A comprehensive framework for scraping and analyzing job leads across multiple platforms",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/vishalc412/Leads-scrapper",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Internet :: WWW/HTTP :: Dynamic Content",
    ],
    python_requires=">=3.9",
    install_requires=requirements,
    extras_require={
        "dev": [
            "pytest>=8.0.0",
            "pytest-asyncio>=0.23.0",
            "pytest-cov>=4.1.0",
            "black>=24.0.0",
            "flake8>=7.0.0",
            "mypy>=1.8.0",
        ],
        "postgres": [
            "psycopg2-binary>=2.9.9",
        ],
    },
    entry_points={
        "console_scripts": [
            "leads-scraper=cli:main",
        ],
    },
    include_package_data=True,
    zip_safe=False,
)
