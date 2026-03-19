from setuptools import setup
import os
from glob import glob

package_name = 'my_four_wheel_robot'  # PHẢI KHỚP với <name> trong package.xml

setup(
    name=package_name,
    version='0.0.0',
    packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        
        # Install toàn bộ thư mục launch (các file .launch.py)
        (os.path.join('share', package_name, 'launch'), glob(os.path.join('launch', '*.launch.py'))),
        
        # Nếu bạn có config YAML hoặc URDF/Xacro, thêm tương tự
        (os.path.join('share', package_name, 'config'), glob(os.path.join('config', '*.yaml'))),
        (os.path.join('share', package_name, 'urdf'), glob(os.path.join('urdf', '*.xacro'))),
        (os.path.join('share', package_name, 'urdf'), glob(os.path.join('urdf', '*.urdf'))),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='bao',  # Thay tên bạn
    maintainer_email='your@email.com',
    description='Robot 4 bánh xe với ROS2',
    license='Apache License 2.0',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            # Nếu có node Python: 'tên_node = my_four_wheel_robot.tên_file:main',
        ],
    },
)
