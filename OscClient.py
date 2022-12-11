#!/usr/bin/env python
import argparse
import random
import time

from pythonosc import udp_client

# //////////////////////////////////////////////////////////////////////////////
class OscClient:
    """ class that handles creating an OSC client """

    def __init__(self, ip_address, port):
        self.server_ip = ip_address
        self.port = port
        self.client = udp_client.SimpleUDPClient(ip_address, port)

    def send_message(self, path, value):
        self.client.send_message(path, value)



# /////////////////////////////////////////////////////////////////////////// 
if __name__ == "__main__":

    print("starting osc client test...")
    parser = argparse.ArgumentParser()
    parser.add_argument("--ip", default="127.0.0.1", help="The ip of the OSC server")
    parser.add_argument("--port", type=int, default=5005, help="The port the OSC server is listening on")
    args = parser.parse_args()

    osc_client = OscClient(args.ip, args.port)

    for x in range(10):
        print("sending message...")
        osc_client.send_message("/filter", random.random())
        time.sleep(1)

    print("osc client test complete.")


