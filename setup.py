from setuptools import setup, find_packages

setup(
    name="agent-skill-manager",
    version="0.1.0",
    description="Cross-platform skill management for domestic AI agent products",
    long_description=open("README.md", encoding="utf-8").read(),
    long_description_content_type="text/markdown",
    license="MIT",
    requires_python=">=3.8",
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    entry_points={
        "console_scripts": [
            "askill=agent_skill_manager.cli:main",
        ],
    },
    python_requires=">=3.8",
)
