from setuptools import find_packages, setup

setup(
    name="SwitchWrapper",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "haversine~=2.3",
        "pandas~=1.2",
        (
            "powersimdata "
            "@ git+https://github.com/Breakthrough-Energy/PowerSimData#egg=PowerSimData"
        ),
        "switch-model==2.0.6",
    ],
)
