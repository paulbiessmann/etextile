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

- PyQt5 (version >= 5.15.0)

    pip3 install pyqt5


# Run

    python3 ble.py
