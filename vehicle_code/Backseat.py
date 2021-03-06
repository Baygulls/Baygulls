#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sat Jul 17 16:18:55 2021

This is the simulated Sandshark front seat


@author: BWSI AUV Challenge Instructional Staff
"""
import sys
import time
import threading
import datetime
# from picamera import PiCamera
# from picamera.array import PiRGBArray
import cv2
import numpy as np

from AUV_Controller import AUVController
from pynmea2 import pynmea2
import BluefinMessages
from Sandshark_Interface import SandsharkClient
import Detect_Buoys

class BackSeat():
    # we assign the mission parameters on init
    def __init__(self, host='localhost', port=8000, warp=1):
        # back seat acts as client
        self.__client = SandsharkClient(host=host, port=port)
        self.__current_time = time.time()
        self.__start_time = self.__current_time
        self.__warp = warp
        self.__autonomy = AUVController()
    
    def run(self):
        try:
            # connect the client
            client = threading.Thread(target=self.__client.run, args=())
            client.start()

            msg = BluefinMessages.BPLOG('ALL', 'ON')
            self.send_message(msg)
            
            # camera = PiCamera()
            # capture = PiRGBArray(camera)
            
            while True:
                now = time.time()
                delta_time = (now - self.__current_time) * self.__warp

                self.send_status()
                self.__current_time += delta_time
                
                msgs = self.get_mail()
                
                
                if len(msgs) > 0:
                    print("\nReceived from front seat:")
                    
                    for msg in msgs:
                        print(f"{str(msg, 'utf-8')}")
                # UNCOMMENT THE FOLLOWING LINES ONCE WE DEPLOY CODE ON RASPBERRY PI
                # camera.capture(capture, format="bgr")
                # buoys = Detect_Buoys.detect_buoys(cv2.resize(capture.array, (640, 360)))
                g_centers = [np.array([123.13333333, 383.86666667])]
                r_centers = [np.array([1052.97752809,  303.44382022]), np.array([670.12903226, 406.06451613])]
                g_angles = [(-26.39532577318937, -6.32962095448399)]
                r_angles = [(18.08203072496716, -10.358707340535199), (-0.7031573062995208, -5.204641813698806)]
                
                buoys = (g_centers, r_centers, g_angles, r_angles)
                time.sleep(1 / self.__warp)
                
                self.process_messages(msgs)
                self.__autonomy.decide(green_buoys=buoys[2], red_buoys=buoys[3])
                
                ### turn your output message into a BPRMB request! 
                
                # ------------------------------------------------------------ #
                # ----This is example code to show commands being issued
                # ------------------------------------------------------------ #
                
                ## We want to change the speed. For now we will always use the RPM (1500 Max)
                self.__current_time = time.time()
                # This is the timestamp format from NMEA: hhmmss.ss
                hhmmss = datetime.datetime.fromtimestamp(self.__current_time).strftime('%H%M%S.%f')[:-4]

                cmd = f"BPRMB,{hhmmss},,,,750,0,1"
                # NMEA requires a checksum on all the characters between the $ and the *
                # you can use the BluefinMessages.checksum() function to calculate
                # and write it like below. The checksum goes after the *
                msg = f"${cmd}*{hex(BluefinMessages.checksum(cmd))[2:]}"
                self.send_message(msg)
                
                ## We want to set the rudder position, use degrees plus or minus
                ## This command is how much to /change/ the rudder position, not to 
                ## set the rudder
                self.__current_time = time.time()
                hhmmss = datetime.datetime.fromtimestamp(self.__current_time).strftime('%H%M%S.%f')[:-4]

                cmd = f"BPRMB,{hhmmss},15,,,750,0,1"
                msg = f"${cmd}*{hex(BluefinMessages.checksum(cmd))[2:]}"
                self.send_message(msg)
                    
                # ------------------------------------------------------------ #
                # ----End of example code
                # ------------------------------------------------------------ #
                
        except:
            self.__client.cleanup()
            client.join()
            
    def process_messages(self, msgs):
        # DEAL WITH INCOMING BFNVG MESSAGES AND USE THEM TO UPDATE THE
        # STATE IN THE CONTROLLER!
        
        ### self.__autonomy.update_state() probably goes here!
        
        # $BFNVG,133501.99,421330.43002,N,071280.32286,W,0,10.0,1.0,20.3,0.0,0.0,1626716101.99*58
        
        auv_states = []
        
        for i in len(msgs):
            msg = msgs[i].split(",")
            
            if hex(BluefinMessages.checksum(msgs[i][1:-3]))[2:] == msg[10].split("*")[1]:
                auv_state = {}
                auv_state["Timestamp"] = msg[1]
                auv_state["Latitude"] = (msg[2], msg[3])
                auv_state["Longitude"] = (msg[4], msg[5])
                auv_state["Quality"] = msg[6]
                auv_state["Altitude"] = msg[7]
                auv_state["Depth"] = msg[8]
                auv_state["Heading"] = msg[9]
                auv_state["Roll"] = msg[10]
                auv_state["Pitch"] = msg[11]
                auv_state["Solution"] = msg[12].split("*")[0]
                auv_states.append(auv_state)
                
        self.__autonomy.update_state(auv_states)                
        
    def send_message(self, msg):
        print(f"sending message {msg}...")
        self.__client.send_message(msg)    
        
    def send_status(self):
        #print("sending status...")
        self.__current_time = time.time()
        hhmmss = datetime.datetime.fromtimestamp(self.__current_time).strftime('%H%M%S.%f')[:-4]
        msg = BluefinMessages.BPSTS(hhmmss, 1, 'BWSI Autonomy OK')
        self.send_message(msg)
            
    def get_mail(self):
        msgs = self.__client.receive_mail()
        return msgs
            
def main():
    if len(sys.argv) > 1:
        host = sys.argv[1]
        
    else:
        host = "localhost"
        
    if len(sys.argv) > 2:
        port = int(sys.argv[2])
        
    else:
        port = 8042
    
    print(f"host = {host}, port = {port}")
    backseat = BackSeat(host=host, port=port)
    backseat.run()
            
if __name__ == '__main__':
    main()