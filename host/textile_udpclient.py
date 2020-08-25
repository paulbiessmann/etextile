#!/usr/bin/env python

import socket
import numpy as np
from pythonosc import udp_client

class UdpInstance:
    def __init__(self, ip, port, name):
        self.name = name
        self.serverAddressPort = (ip, port)
        self.osc_client = udp_client.SimpleUDPClient(*self.serverAddressPort)
        self.UDPClientSocket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
        print("UDP sending client ready")

    def sendUdp(self, message, riotAddr):
        # print(self.name, message)
        # send prediction to server
        #self.osc_client.send_message(riotAddr, message)
        self.osc_client.send_message("/data", message)

    def close(self):
        UDPClientSocket.close()

