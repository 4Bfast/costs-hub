from setuptools import setup, find_packages

setup(
    name="lambda-cost-reporting-system",
    version="0.1.0",
    description="AWS Lambda-based cost reporting system for multiple clients",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    python_requires=">=3.9",
    install_requires=[
        "boto3>=1.34.0",
        "botocore>=1.34.0",
        "pandas>=2.0.0",
        "numpy>=1.24.0",
        "jinja2>=3.1.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.4.0",
            "pytest-mock>=3.11.0",
            "moto>=4.2.0",
            "black>=23.0.0",
            "flake8>=6.0.0",
            "mypy>=1.5.0",
            "localstack>=3.0.0",
        ]
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
)