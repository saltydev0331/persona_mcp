from setuptools import setup, find_packages

setup(
    name="persona-mcp-server",
    version="0.1.0",
    description="Local MCP Persona Interaction Server",
    author="Persona MCP Developer",
    python_requires=">=3.11",
    packages=find_packages(),
    install_requires=[
        "aiohttp>=3.9.0",
        "aiofiles>=23.2.0",
        "pydantic>=2.5.0",
        "sqlalchemy>=2.0.0",
        "chromadb>=0.4.0",
        "httpx>=0.25.0",
        "numpy>=1.24.0",
        "python-dotenv>=1.0.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.4.0",
            "pytest-asyncio>=0.21.0",
        ]
    },
    entry_points={
        "console_scripts": [
            "persona-server=persona_mcp.server:main",
        ],
    },
)