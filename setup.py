from setuptools import setup, find_packages

setup(
    name="ersilia-pack",
    version="1.0.0",
    packages=find_packages(),
    install_requires=[
        "fastapi",
    ],
    package_data={
        "": ["*.txt"],
    },
    entry_points={
        "console_scripts": [
            "ersilia_model_pack=src.packer:main",
            "ersilia_model_serve=src.server:main",
            "ersilia_model_lint=src.linter:main",
        ],
    },
)
