from glob import glob
import os
from setuptools import setup

PACKAGE_NAME = 'diablo_mqtt'
SHARE_DIR = os.path.join("share", PACKAGE_NAME)

setup(
    name=PACKAGE_NAME,
    version='0.1.0',
    packages=["libdiablo_mqtt", "libdiablo_mqtt.nodes"],
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + PACKAGE_NAME]),
        ('share/' + PACKAGE_NAME, ['package.xml']),
        (os.path.join(SHARE_DIR, "launch"), glob(os.path.join("launch", "*.launch.py"))),
    ],
    package_dir={'': 'src', },
    zip_safe=True,
    install_requires=['setuptools',
                      'paho-mqtt'],
    maintainer='tianbot',
    maintainer_email='tianbot@tianbot.com',
    description='TODO: Package description',
    license='TODO: License declaration',
    # tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'mqtt_receive = libdiablo_mqtt.nodes.mqtt_receive:main',
            'mqtt_send = libdiablo_mqtt.nodes.mqtt_send:main',
        ],
    },
)
