#!/usr/bin/env python
import signal
import sys
import time
import struct
from textile_udpclient import UdpInstance
from pythonosc import udp_client
import socket
import numpy as np

from PyQt5 import QtBluetooth as QtBt
from PyQt5 import QtCore

from qenum import qenum_key


class ServiceHandler(object):
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

        self.last = time.time()

        s.discoverDetails()

    def stateChanged(self, state):
        print("stateChanged()", self.device.address, self.uuid.toString(), qenum_key(QtBt.QLowEnergyService, state))
        if state == QtBt.QLowEnergyService.ServiceState.ServiceDiscovered:
            self.characteristics = self.service.characteristics()

            for c in self.characteristics:
                print(c.name(), qenum_key(QtBt.QLowEnergyCharacteristic, c.properties()))
                if ServiceHandler.supportsNotify(c):
                    self.enableNotify(c)

    def supportsNotify(char):
        return char.properties() & 0x10

    def enableNotify(self, char):
        notification = char.descriptors()[0]
        if notification.isValid():
            print("enabling notifications on ", notification)
            self.service.writeDescriptor(notification, QtCore.QByteArray.fromHex(b"0100"))

    def disconnected(self):
        print("Sevice.disconnected()", self.device.address, self.uuid.toString())

    def characteristicChanged(self, char, data):
        print("Sevice.characteristicChanged()", self.device.address, self.uuid.toString(), data, now - self.last)

    def descriptorWritten(self, desc, data):
        print("Sevice.descriptorWritten()", self.device.address, self.uuid.toString(), desc, data)

    def descriptorRead(self, *args, **kwargs):
        print("Sevice.descriptorRead()", self.device.address, self.uuid.toString(), args, kwargs)

    def error(self, error):
        print("Sevice.error()", self.device.address, self.uuid.toString(), qenum_key(QtBt.QLowEnergyService, error))


class EtextileServiceHandler(ServiceHandler):
    uuid = "{00004e20-0000-1000-8000-00805f9b34fb}"

    def __init__(self, device, uuid):
        super().__init__(device, uuid)

    def characteristicChanged(self, char, data):
        array = struct.unpack("H" * int((len(data) / 2)), data)
        EtextileServiceHandler.etextile_handle_data(self.device_number(self.device.address), array)

    def etextile_handle_data(device_address, data):
        print("etextile data:", device_address, data)

    # convert address to Riot1 Riot2 etc:
    def device_number(self, i):
        if device_name_dict.get(i) is None:
            new_device_num = 'Riot' + str(len(device_name_dict) + 1)
            device_name_dict[i] = new_device_num
            print("Unknown Riot device added" + i + " - gets Number " + new_device_num)
        return device_name_dict.get(i, "Invalid device. Add to List!")


class DeviceConnection(object):
    def __init__(self, app, device, service_handlers):
        self.app = app
        if sys.platform != "darwin":
            self.address = device.address().toString()
        else:
            self.address = device.deviceUuid().toString()

        self.service_handlers = {}
        for s in service_handlers:
            self.service_handlers[s.uuid] = s

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
        QtCore.QTimer.singleShot(2000, self.cleanup)

    def cleanup(self):
        print("device.cleanup()")
        if self.app.connections.get(self.address) == self:
            self.app.connections.pop(self.address, None)

    def serviceDiscovered(self, uuid):
        print("device.serviceDiscovered()", self.address, uuid.toString())

    def discoveryFinished(self):
        print("device.discoveryFinished()", self.address)

        for uuid in self.connection.services():
            service_handler = self.service_handlers.get(uuid.toString())
            if service_handler is not None:
                service_handler(self, uuid)

    def error(self, error):
        print("device.error()", self.address, qenum_key(QtBt.QLowEnergyController, error))
        if qenum_key(QtBt.QLowEnergyController, error) == "UnknownError":
            self.connection.disconnectFromDevice()
            QtCore.QTimer.singleShot(5000, self.cleanup)


class Application(QtCore.QCoreApplication):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.service_handlers = [EtextileServiceHandler]
        self.connections = {}
        self.riotUuid = []
        self.scan_for_devices()
        self.exec()

    def display_status(self):
        pass

    def device_discovered(self, device):
        # Application.device_print(device)
        if device.name().startswith("RIOT"):
            if device.deviceUuid().toString() not in self.riotUuid:
                self.riotUuid.append(device.deviceUuid().toString())
        pass

    def device_print(device):
        print(device.address().toString(), device.name(), '\t', device.deviceUuid().toString())

    def error(self, error):
        print("error():", qenum_key(QtBt.QBluetoothDeviceDiscoveryAgent, error))

    def finished(self, *args, **kwargs):
        for device in self.agent.discoveredDevices():
            if sys.platform != "darwin":
                if device.name().startswith("RIOT"):
                    if device.address().toString() not in self.connections:
                        connection = DeviceConnection(self, device, self.service_handlers)
                        connection.connect()
            else:
                # on OSX the name can't be read, so use the Uudi
                if device.deviceUuid().toString() in self.riotUuid:
                    if device.deviceUuid().toString() not in self.connections:
                        connection = DeviceConnection(self, device, self.service_handlers)
                        connection.connect()

        self.agent.start()

    def scan_for_devices(self):
        self.agent = QtBt.QBluetoothDeviceDiscoveryAgent(self)
        self.agent.deviceDiscovered.connect(self.device_discovered)
        self.agent.finished.connect(self.finished)
        self.agent.error.connect(self.error)
        self.agent.setLowEnergyDiscoveryTimeout(1000)

        timer = QtCore.QTimer(self.agent)
        timer.start(2000)
        timer.timeout.connect(self.display_status)

        self.agent.start()


# provide
def handle_data(device_num, array):
    print(device_num, array)
    udp.sendUdp(device_num, array)


EtextileServiceHandler.etextile_handle_data = handle_data

if __name__ == "__main__":
    if sys.platform == "darwin":
        import os

        os.environ["QT_EVENT_DISPATCHER_CORE_FOUNDATION"] = "1"

    # setup OSC client
    localIP = "127.0.0.1"
    localPortSender = 7001
    device_name_dict = {
        # List of device names, add here:
        "{94e00f41-7d5a-4851-bd0a-1f7e02c1350f}": 'Riot1',
        "{0b0b4431-b150-4279-9f6a-ce112144b99e}": 'Riot2',
        "{620eb416-51d3-47d5-a4d4-7d7233cc08ec}": 'Riot3'
    }

    if len(sys.argv) > 1:
        localPortSender = int(sys.argv[1])

    print("set port to ", localPortSender)

    udp = UdpInstance(localIP, localPortSender, "firstSender")

    app = Application(sys.argv)

    udp.close()
