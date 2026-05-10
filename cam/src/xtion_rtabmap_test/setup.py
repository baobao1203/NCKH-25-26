from setuptools import find_packages, setup

package_name = "xtion_rtabmap_test"

setup(
    name=package_name,
    version="0.0.0",
    packages=find_packages(exclude=["test"]),
    data_files=[
        ("share/ament_index/resource_index/packages", ["resource/" + package_name]),
        ("share/" + package_name, ["package.xml"]),
        ("share/" + package_name + "/config", ["config/rtabmap_params.yaml"]),
        ("share/" + package_name + "/launch", ["launch/xtion_rtabmap.launch.py"]),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="bao",
    maintainer_email="helpbaobao@gmail.com",
    description="TODO: Package description",
    license="TODO: License declaration",
    extras_require={
        "test": [
            "pytest",
        ],
    },
    entry_points={
        "console_scripts": [],
    },
)
