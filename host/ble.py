#!/usr/bin/env python
import signal
import sys
import time

from PyQt5 import QtBluetooth as QtBt
from PyQt5 import QtCore

from qenum import qenum_key

class Service(object):
    def __init__(self, device, uuid):
        self.device = device
        self.uuid = uuid
        self.characteristics = {}
        s = device.connection.createServiceObject(uuid)
        s.stateChanged.connect(self.stateChanged)
        s.characteristicChanged.connect(self.characteristicChanged)
        s.descriptorWritten.connect(self.descriptorWritten)
        s.descriptorRead.connect(self.descriptorRead)
        s.error.connect(self.error)

        self.service = s
        device.services[uuid.toString()] = self

        s.discoverDetails()

    def stateChanged(self, state):
        print("stateChanged()", self.device.address, self.uuid.toString(), qenum_key(QtBt.QLowEnergyService, state))
        if state == QtBt.QLowEnergyService.ServiceState.ServiceDiscovered:
            self.characteristics = self.service.characteristics()

            for c in self.characteristics:
                print(c.name(), qenum_key(QtBt.QLowEnergyCharacteristic, c.properties()))
                if c.properties() & 0x10:
                    notification = c.descriptors()[0]
                    if notification.isValid():
                        print("enabling notifications on ", notification)
                        self.service.writeDescriptor(notification, QtCore.QByteArray.fromHex(b"0100"))
                    else:
                        print("notif inval")
                    break


    def disconnected(self):
        print("Sevice.disconnected()", self.device.address, self.uuid.toString())

    def characteristicChanged(self, char, data):
        print("Sevice.characteristicChanged()", self.device.address, self.uuid.toString(), data)

    def descriptorWritten(self, *args, **kwargs):
        print("Sevice.descriptorWritten()", self.device.address, self.uuid.toString(), args, kwargs)
    
    def descriptorRead(self, *args, **kwargs):
        print("Sevice.descriptorRead()", self.device.address, self.uuid.toString(), args, kwargs)

    def error(self, *args, **kwargs):
        print("Sevice.error()", self.device.address, self.uuid.toString(), args, kwargs)


class DeviceConnection(object):
    def __init__(self, app, device):
        self.app = app
        self.address = device.address().toString()
        c = QtBt.QLowEnergyController.createCentral(device)
        c.connected.connect(self.connected)
        c.disconnected.connect(self.disconnected)
        c.error.connect(self.error)

        c.serviceDiscovered.connect(self.serviceDiscovered)
        c.discoveryFinished.connect(self.discoveryFinished)

        self.connection = c

        self.services = {}

        self.app.connections[self.address] = self

    def connect(self):
        print("device.connect()", self.address)
        self.connection.connectToDevice()

    def connected(self):
        print("device.connected()", self.address)
        self.connection.discoverServices()

    def disconnected(self):
        print("device.disconnected()", self.address)
        self.app.connections.pop(self.address)

    def serviceDiscovered(self, uuid):
        print("device.serviceDiscovered()", self.address, uuid.toString())

    def discoveryFinished(self):
        print("device.discoveryFinished()", self.address)

        for uuid in self.connection.services():
            if uuid.toString() == "{00004e20-0000-1000-8000-00805f9b34fb}":
                Service(self, uuid)

    def error(self, *args, **kwargs):
        print("device.error()", self.address, args, kwargs)


class Application(QtCore.QCoreApplication):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connections = {}
        self.scan_for_devices()
        self.exec()

    def display_status(self):
        for device in self.agent.discoveredDevices():
            if device.name().startswith("RIOT"):
                if device.address().toString() not in self.connections:
                    self.agent.stop()
                    time.sleep(0.5)
                    connection = DeviceConnection(self, device)
                    connection.connect()

    def device_discovered(self, device):
        Application.device_print(device)

    def device_print(device):
        print (device.address().toString(), device.name())

    def error(self, error):
        print("error():", qenum_key(QtBt.QBluetoothDeviceDiscoveryAgent, error))

    def finished(self, *args, **kwargs):
        print("finished", args, kwargs)

    def scan_for_devices(self):
        self.agent = QtBt.QBluetoothDeviceDiscoveryAgent(self)
        self.agent.deviceDiscovered.connect(self.device_discovered)
        self.agent.finished.connect(self.finished)
        self.agent.error.connect(self.error)
        #self.agent.setLowEnergyDiscoveryTimeout(1000)

        timer = QtCore.QTimer(self.agent)
        timer.start(500)
        timer.timeout.connect(self.display_status)

        self.agent.start()


if __name__ == "__main__":
    if sys.platform == "darwin":
        os.environ["QT_EVENT_DISPATCHER_CORE_FOUNDATION"] = "1"

    app = Application(sys.argv)
