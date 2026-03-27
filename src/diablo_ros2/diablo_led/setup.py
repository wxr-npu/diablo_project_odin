from glob import glob
import os
from setuptools import setup

PACKAGE_NAME = 'diablo_led'
SHARE_DIR = os.path.join('share', PACKAGE_NAME)
setup(
    name=PACKAGE_NAME,
    version='0.1.0',
    packages=[PACKAGE_NAME],
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + PACKAGE_NAME]),
        ('share/' + PACKAGE_NAME, ['package.xml']),
        (os.path.join(SHARE_DIR, "launch"), glob('launch/*.launch.py')),
    ],
    package_dir={'': 'src'},
    zip_safe=True,
    install_requires=['setuptools',
                      'pyserial'],
    maintainer='tianbot',
    maintainer_email='tianbot@tianbot.com',
    description='TODO: Package description',
    license='TODO: License declaration',
    # tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'diablo_led = diablo_led.diablo_led:main',
            'led_test   = diablo_led.led_test:main '
        ],
    },
)
