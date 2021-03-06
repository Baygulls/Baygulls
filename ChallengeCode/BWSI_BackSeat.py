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
import time
import datetime
import logging

import utm

from Image_Processor import ImageProcessor
from AUV_Controller import AUVController

from pynmea2 import pynmea2
import BluefinMessages
from Sandshark_Interface import SandsharkClient

# Check the NMEA checksum
def valid_checksum(msg):
    fields = msg.split('*')
    cmd = fields[0][1:]
    expected = str(hex(BluefinMessages.checksum(cmd))[2:])
    
    if expected.upper() != fields[1].upper():
        print(f"cmd = {cmd}")
        print(f"{expected} != {fields[1]}")
        return False
    
    return True

class BackSeat():
    # we assign the mission parameters on init
    def __init__(self, host='localhost', port=8000, warp=1, camera_type="SIM", logger=None):
        
        # back seat acts as client
        self.__client = SandsharkClient(host=host, port=port)
        self.__current_time = datetime.datetime.utcnow().timestamp()
        self.__start_time = self.__current_time
        self.__logger = logger
        self.__warp = warp
        
        self.__auv_state = dict([
            ('position', (None, None)),
            ('latlon', None),
            ('heading', None),
            ('depth', None),
            ('altitude', None),
            ('roll', None),
            ('pitch', None),
            ('last_fix_time', None),
            ('speed', None),
            ('rudder', 0)
        ])
        
        # we'll use the first navigation update as datum
        self.__datum = None
        
        # set to PICAM for the real camera
        self.__camera_type = camera_type
        self.__buoy_detector = ImageProcessor(camera=self.__camera_type, logger=logger)
        self.__autonomy = AUVController(logger=logger)
    
    def run(self):
        try:
            # connect the client
            client = threading.Thread(target=self.__client.run, args=())
            client.start()
            msg = BluefinMessages.BPLOG('ACK', 'ON')
            self.send_message(msg)
            msg = BluefinMessages.BPLOG('ALL', 'ON')
            self.send_message(msg)
            ### These flags are for the test code. Remove them after the initial test!
            engine_started = False
            turned = False
            
            while True:
                now = datetime.datetime.utcnow().timestamp()
                delta_time = (now-self.__current_time) * self.__warp

                self.send_status()

                self.__current_time += delta_time
                
                msgs = self.get_mail()
                
                if len(msgs) > 0:
                    for msg in msgs:
#                         print(f"{str(msg, 'utf-8')}")
                        self.process_message(str(msg, 'utf-8'))
#                         print(f"{self.__auv_state}")
                        
                self.__logger.info(f"Received from Frontseat: {msgs}")
                self.__logger.info(f"AUV state: {self.__auv_state}")
                
                if self.__auv_state["heading"] is not None or self.__camera_type != "SIM":
                    ### ---------------------------------------------------------- #
                    ### Here should be the request for a photo from the camera
                    ### img = self.__camera.acquire_image()
                    ###
                    ### Here you process the image and return the angles to target
                    ### green, red = self.__detect_buoys(img)
                    green, red = self.__buoy_detector.run(self.__auv_state)
                    self.__logger.info(f"Next green buoy: {green}, next red buoy: {red}")
                    ### ---------------------------------------------------------- #


                    ### self.__autonomy.decide() probably goes here!
                    rudder_angle, speed = self.__autonomy.decide(self.__auv_state, green, red)

                    ### ---------------------------------------------------------- #
                    ### turn your output message into a BPRMB request! 

                    cmd = self.format_command(rudder_angle, speed)
                    msg = f"${cmd}*{hex(BluefinMessages.checksum(cmd))[2:]}\n"
                    self.send_message(msg)
                
                time.sleep(1/self.__warp)
                
                # ------------------------------------------------------------ #
                # ----This is example code to show commands being issued
                # ------------------------------------------------------------ #
                if False:
                    print(f"dt = {self.__current_time - self.__start_time}")
                    if not engine_started and (self.__current_time - self.__start_time) > 3:
                        ## We want to change the speed. For now we will always use the RPM (1500 Max)
                        self.__current_time = datetime.datetime.utcnow().timestamp()
                        # This is the timestamp format from NMEA: hhmmss.ss
                        hhmmss = datetime.datetime.fromtimestamp(self.__current_time).strftime('%H%M%S.%f')[:-4]

                        cmd = f"BPRMB,{hhmmss},,,,750,0,1"
                        # NMEA requires a checksum on all the characters between the $ and the *
                        # you can use the BluefinMessages.checksum() function to calculate
                        # and write it like below. The checksum goes after the *
                        msg = f"${cmd}*{hex(BluefinMessages.checksum(cmd))[2:]}\n"
                        self.send_message(msg)
                        engine_started = True

                    if not turned and (self.__current_time - self.__start_time) > 30:
                        ## We want to set the rudder position, use degrees plus or minus
                        ## This command is how much to /change/ the rudder position, not to 
                        ## set the rudder
                        self.__current_time = datetime.datetime.utcnow().timestamp()
                        hhmmss = datetime.datetime.fromtimestamp(self.__current_time).strftime('%H%M%S.%f')[:-4]

                        cmd = f"BPRMB,{hhmmss},-15,,,750,0,1"
                        msg = f"${cmd}*{hex(BluefinMessages.checksum(cmd))[2:]}\n"
                        self.send_message(msg)
                        turned = True
                    
                # ------------------------------------------------------------ #
                # ----End of example code
                # ------------------------------------------------------------ #
                
        except:
            self.__logger.error("An error occurred. The stack trace is below.", exc_info=True)
            self.__client.cleanup()
            client.join()
          
    
    def format_command(self, rudder_angle, speed=750):
        hhmmss = datetime.datetime.fromtimestamp(self.__current_time).strftime('%H%M%S.%f')[:-4]
        cmd = f"BPRMB,{hhmmss},{-rudder_angle},1,0,{speed},0,1"
        return cmd
    
    def process_message(self, message):
        # DEAL WITH INCOMING BFNVG MESSAGES AND USE THEM TO UPDATE THE
        # STATE IN THE CONTROLLER!
        messages = message.split('$')
        messages = messages[1:] # the first split will be blank, or partial message
        
        processed_list = list()
        for msgpart in reversed(messages):
            msg = f"${msgpart}"
        
            # JRE: skipping the checksum check for now!
            self.__logger.info(f"Processing: {msg}")

            if not valid_checksum(msg):
                self.__logger.warning(f"Mismatched checksum, skipping message {msg}")
                return
                
            payld = msg.split('*')
            fields = payld[0].split(',')
            
            # only process one of each type of message
            if fields[0] in processed_list:
                continue
            
            processed_list.append(fields[0])
            
            if fields[0] == '$BFNVG':
                # don't care about message timestamp
                #nvg_time = self.receive_nmea_time(fields[1])
                        
                # really only care about heading and position for now
                self.__auv_state['latlon'] = self.receive_nmea_latlon(fields[2],fields[3], fields[4], fields[5])
                            
                if self.__datum is None:
                    # on first navigation update, set datum
                    self.__datum = self.__auv_state['latlon']
                    self.__datum_position = utm.from_latlon(self.__datum[0], self.__datum[1])
                    self.__auv_state['position'] = (0, 0)
                    
                else:
                    self.__auv_state['position'] = self.__get_local_position()
                    
                self.__auv_state['datum'] = self.__datum
                self.__auv_state['altitude'] = float(fields[7])        
                self.__auv_state['depth'] = float(fields[8])
                self.__auv_state['heading'] = float(fields[9])
                self.__auv_state['roll'] = float(fields[10])
                self.__auv_state['pitch'] = float(fields[11])
                self.__auv_state['last_fix_time'] = self.receive_nmea_time(fields[12])
                
                self.__logger.info(f"Interpreted as: {str(self.__auv_state)}")
                    
            elif fields[0] == '$BFNVR':
                nvr = {'timestamp': fields[1],
                   'east_velocity': float(fields[2]),
                   'north_velocity': float(fields[3]),
                   'down_velocity': float(fields[4]),
                   'pitch_rate': float(fields[5]),
                   'roll_rate': float(fields[6]),
                   'yaw_rate': float(fields[7]),
                }
                
                self.__logger.info(f"Interpreted as: {nvr}")
                    
            elif fields[0] == '$BFVER':
                # don't care about the time for now
                print(f"Version is {fields[2]}")
                
                self.__logger.info(f"Version: {fields[2]}")
                
            elif fields[0] == '$BFACK':
                print(f"time = {fields[1]}")
                msg_type = fields[2]
                status = int(fields[5])
                if status < 2:
                    outstr = f"Vehicle failed to process request {msg_type}: {fields[7]}"
                    
                elif status == 2:
                    outstr = f"Vehicle successfully processed request {msg_type}"
                    
                else:
                    outstr = f"Request {msg_type} is pending"
                    
                self.__logger.info(f"{outstr}")
                    
            else:
                self.__logger.warning(f"I do not know how to process this message type: {fields[0]}")
                
    def send_message(self, msg):
        self.__logger.info(f"sending message {msg}...")
        self.__client.send_message(msg)    
        
    def send_status(self):
        #print("sending status...")
        self.__current_time = datetime.datetime.utcnow().timestamp()
        hhmmss = datetime.datetime.fromtimestamp(self.__current_time).strftime('%H%M%S.%f')[:-4]
        msg = BluefinMessages.BPSTS(hhmmss, 1, 'BWSI Autonomy OK')
        self.send_message(msg)
            
    def get_mail(self):
        msgs = self.__client.receive_mail()
        return msgs
    
    def receive_nmea_time(self, hhmmss):
        tm = datetime.datetime.utcnow()
        nvg_time = datetime.datetime(tm.year,
                                     tm.month,
                                     tm.day,
                                     int(hhmmss[0:2]), 
                                     int(hhmmss[2:4]), 
                                     int(hhmmss[4:6]),
                                     0)
        
        return nvg_time
    
    def receive_nmea_latlon(self, latdeg, lathemi, londeg, lonhemi):
        latitude = int(latdeg[0:2]) + float(latdeg[2:]) / 60
        
        if lathemi == 'S':
            latitude = -latitude
        
        longitude = int(londeg[0:3]) + float(londeg[3:]) / 60
        if lonhemi == 'W':
            longitude = -longitude
            
        return (latitude, longitude)
    
    def __get_local_position(self):
        # check that datum is in the same UTM zone, if not, shift datum
        local_pos = utm.from_latlon(self.__auv_state['latlon'][0],
                                    self.__auv_state['latlon'][1],
                                    force_zone_number=self.__datum_position[2],
                                    force_zone_letter=self.__datum_position[3])
        
        return (local_pos[0]-self.__datum_position[0], local_pos[1]-self.__datum_position[1])
        
def main():
    if len(sys.argv) > 1:
        host = sys.argv[1]
    else:
        host = "localhost"
        
    if len(sys.argv) > 2:
        port = int(sys.argv[2])
    else:
        port = 29500
        
    file_handler = logging.FileHandler(f"backseat_{datetime.datetime.utcnow().timestamp()}.log")
    file_handler.setLevel(logging.DEBUG)
    logging.basicConfig(format="%(asctime)s [%(levelname)s] %(message)s", handlers=[logging.StreamHandler(sys.stdout), file_handler])
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    
    logger.info(f"host = {host}, port = {port}")
    backseat = BackSeat(host=host, port=port, logger=logger)
    backseat.run()
    
if __name__ == '__main__':
    main()
