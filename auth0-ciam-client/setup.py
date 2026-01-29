"""Setup configuration for auth0-ciam-client package."""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="auth0-ciam-client",
    version="0.1.0",
    author="Brian Reavey",
    author_email="brian@reavey05.com",
    description="Auth0 Customer Identity and Access Management Client",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/auth0-ciam-client",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Internet :: WWW/HTTP",
        "Topic :: Security",
    ],
    python_requires=">=3.8",
    install_requires=[
        "requests>=2.25.0",
        "beautifulsoup4>=4.9.0",
    ],
    extras_require={
        "dev": [
            "pytest>=6.0.0",
            "pytest-mock>=3.0.0",
            "pytest-cov>=2.0.0",
            "black>=21.0.0",
            "flake8>=3.8.0",
            "mypy>=0.800",
        ],
    },
    keywords="auth0 authentication oauth jwt session management",
    project_urls={
        "Bug Reports": "https://github.com/yourusername/auth0-ciam-client/issues",
        "Source": "https://github.com/yourusername/auth0-ciam-client",
    },
)