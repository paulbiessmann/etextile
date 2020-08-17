# Intro

This folder contains the eTextile sensor application.
It has been tested on the Adafruit CircuitPlayground Bluefruit.

# How to use

Given a factory bluefruit, you'll probably need to update the bootloader. This
has to be done only once.

After that, given a compiled .uf2 file of this software, it can be installed as
follows:

- double-tab reset (red led should be slowly breathing)
- mount the drive called "CPLAYBTBOOT"
- copy the .uf2 file to that drive


# building from source

- clone RIOT:

    git clone https://github.com/kaspar030/RIOT -b add_circuit_playground_bluefruit

- build:

    BOARD=foo make clean all flash -j8


# update bootloader of the bluefruit (might be necessary)

(linked .zip is probably too old, might need self compiled version)

 - install adafruit-nrfutil:

    pip3 install --user adafruit-nrfutil

 - get new version from https://github.com/adafruit/Adafruit_nRF52_Bootloader/releases/download/0.3.2/circuitplayground_nrf52840_bootloader-0.3.2_s140_6.1.1.zip
 
 - flash: (adapt path/to and serial port accordingly)
  1. double press reset button. red led should slowly breathe
  2. then run

    adafruit-nrfutil dfu serial -pkg path/to/circuitplayground_nrf52840_bootloader-0.3.2_s140_6.1.1.zip -p /dev/ttyACM0 -b 115200 --touch 1200

