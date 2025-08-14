"""Setup configuration for neo-commons package."""

from setuptools import setup, find_packages
from pathlib import Path

# Read version from __version__.py
version = {}
with open("src/neo_commons/__version__.py") as fp:
    exec(fp.read(), version)

# Read README for long description
readme_path = Path(__file__).parent / "README.md"
long_description = readme_path.read_text(encoding="utf-8") if readme_path.exists() else ""

setup(
    name="neo-commons",
    version=version["__version__"],
    description="Common utilities for NeoMultiTenant microservices",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="NeoFast Team",
    author_email="team@neofast.com",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    python_requires=">=3.13",
    install_requires=[
        "fastapi>=0.115.0",
        "asyncpg>=0.29.0", 
        "redis>=5.0.0",
        "python-keycloak>=5.7.0",
        "pydantic>=2.0.0",
        "python-jose[cryptography]>=3.3.0",
        "python-multipart>=0.0.6",
        "uvicorn[standard]>=0.30.0",
        "cryptography>=41.0.0",
        "aioredis>=2.0.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-asyncio>=0.21.0",
            "pytest-cov>=4.0.0",
            "black>=23.0.0",
            "ruff>=0.1.0",
            "mypy>=1.0.0",
            "pre-commit>=3.0.0",
        ],
        "test": [
            "pytest>=7.0.0",
            "pytest-asyncio>=0.21.0",
            "pytest-cov>=4.0.0",
            "pytest-mock>=3.11.0",
            "httpx>=0.24.0",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.13",
        "Framework :: FastAPI",
        "Framework :: AsyncIO",
        "Topic :: Internet :: WWW/HTTP :: HTTP Servers",
        "Topic :: Software Development :: Libraries :: Application Frameworks",
    ],
    keywords="fastapi microservices authentication authorization database cache",
    project_urls={
        "Documentation": "https://github.com/your-org/neo-commons",
        "Source": "https://github.com/your-org/neo-commons",
        "Tracker": "https://github.com/your-org/neo-commons/issues",
    },
)