#!/bin/bash
 
echo "remap the device serial port(ttyUSBX) to tianbot_base"
echo "diablo usb connection as /dev/tianbot_base , check it using the command : ls -l /dev|grep ttyUSB"
echo "start copy *.rules to  /etc/udev/rules.d/"
sudo cp *.rules  /etc/udev/rules.d

echo "Restarting udev"
sudo udevadm control --reload-rules
sudo service udev restart
sudo udevadm trigger
echo "finish "