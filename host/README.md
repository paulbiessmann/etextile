# Intro

This folder contains the eTextile host application

# Installation

## Linux prerequisites:

- PyQt5 (version >= 5.15.0)

    pip3 install --upgrade pyqt5

- missing capability issue: https://stackoverflow.com/questions/60989706/qt-bluetooth-stuck-when-connecting-to-classic-bluetooth-device
  for python3.8 for example:

    sudo setcap 'cap_net_raw,cap_net_admin+eip' /usr/bin/python3.8


## OS X prerequisites:
    
- Install the required python packages with ``pip install -r requirements.txt`` in the folder of the downloaded github repo

# Run

    python3 ble.py
    
# Examples

Use `udpReceiver.pd` for PureData or `pb_eTextile_rcv_V01.amxd` for Max4Live as example how to receive data. 
