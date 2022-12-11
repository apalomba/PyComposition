#!/usr/bin/env python
import time, threading
#import serial
import os
import argparse
import math

from pythonosc import dispatcher
from pythonosc import osc_server
from pythonosc import osc_bundle_builder
from pythonosc import osc_message_builder

time_interval = 5

def print_control_handler(unused_addr, args, control, value):
  print("[{0}] ~ {1}".format(args[0], control))

def print_note_handler(unused_addr, args, note, velocity):
  try:
    print("[{0}] ~ {1}".format(args[0], args[1](note)))
  except ValueError: pass


# //////////////////////////////////////////////////////////////////////////////
class OscServer:
    """ class that handles creation of an OSC server """

    def __init__(self, ip_address, port):
        self.server_ip = ip_address
        self.port = port
        self.dispatcher = dispatcher.Dispatcher()
        self.server = None

    def register_handler(self, osc_handler, osc_path):
        self.dispatcher.map("/"+osc_path, osc_handler, osc_path)

    def server_start(self):
        self.server = osc_server.ThreadingOSCUDPServer( (self.server_ip, self.port), self.dispatcher)
        print("Serving on {}".format(self.server.server_address))
        self.server.serve_forever()

    def server_stop(self):
        self.server.shutdown()

    def send_message(self, path, value):
        pass


def thread_function(name):
    print ("Thread %s: starting", name)
    time.sleep(time_interval)

# ///////////////////////////////////////////////////////////////////////////
if __name__ == "__main__":
    # parser = argparse.ArgumentParser()
    # parser.add_argument("--ip", default="127.0.0.1", help="The ip to listen on")
    # parser.add_argument("--port", type=int, default=57120, help="The port to listen on")
    # args = parser.parse_args()

    server = OscServer("127.0.0.1", 57120)
    #server.register_handler(print_control_handler, "trigger")
    server.register_handler(print, "trigger")
    server.register_handler(print, "transport")
    #server.register_handler(print_note_handler, "/note")
    print("Starting server...")
    server.server_start()

