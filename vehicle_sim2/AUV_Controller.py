#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Jul  7 12:05:08 2021

@author: BWSI AUV Challenge Instructional Staff
"""
import sys
import numpy as np

class AUVController():
    def __init__(self, logger=None):
        # initialize state information
        self.__heading = None
        self.__speed = None
        self.__rudder = None
        self.__position = None
        
        # assume we want to be going the direction we're going for now
        self.__desired_heading = None
        self.__gnext = None
        self.__rnext = None
        self.__logger = logger
        
    def initialize(self, auv_state):
        self.__heading = auv_state['heading']
        self.__position = auv_state['position']
        
        # assume we want to be going the direction we're going for now
        self.__desired_heading = auv_state['heading']

    ### Public member functions    
    def decide(self, auv_state, green_buoys, red_buoys, sensor_type='ANGLE'):
        # update state information
        self.__heading = auv_state['heading']
        self.__position = auv_state['position']
                
        # determine what heading we want to go
        if sensor_type.upper() == 'POSITION': # known positions of buoys
            self.__desired_heading = self.__heading_to_position(green_buoys, red_buoys)
            
        elif sensor_type.upper() == 'ANGLE': # camera sensor
            self.__desired_heading = self.__heading_to_angle(green_buoys, red_buoys)
                              
        if self.__desired_heading is not None:
            # determine whether and what command to issue to desired heading               
            cmd = self.__select_command()
            
            if self.__heading is not None:
                auv_state["rudder"] = self.__desired_heading - self.__heading
            
#             self.__logger.info("*!#@#@$#%@$^&%$^! " + str(auv_state) + ", " + cmd)
            
        else:
            cmd = None
            
        return (cmd, auv_state)
        
    # return the desired heading to a public requestor
    def get_desired_heading(self):
        return self.__desired_heading
    
    ### Private member functions
        
    # calculate the heading we want to go to reach the gate center
    def __heading_to_position(self, gnext, rnext):
        # center of the next buoy pair
        gate_center = ((self.__gnext[0] + self.__rnext[0]) / 2.0, (self.__gnext[1] + self.__rnext[1]) / 2.0)
        
        # heading to gate_center
        tgt_hdg = np.mod(np.degrees(np.arctan2(gate_center[0]-self.__position[0],
                                               gate_center[1]-self.__position[1])) + 360, 360)
        
        return tgt_hdg

    def __heading_to_angle(self, gnext, rnext):
        # pass rnext on port side
        # pass gnext on starboard side
        self.__logger.info(f"rnext: {rnext} gnext: {gnext}") # relative angles to the buoys
        # which are measured clockwise from the heading of the AUV.

        # rnext and gnext are in this format. We only need the horizontal angle to the buoy,
        # which is why we get the horizontal angle by doing gnext[0][0]
        
        # rnext: [(-2.6533087248159455, -5.348725386576375)]
        # gnext:  [(8.445588240799415, -5.304815966173086)]

        # if angle in gnext is larger than 220 and len(gnext) > 1, get normal angle
        if gnext and rnext:
            relative_angle = (gnext[0][0] + rnext[0][0]) / 2.0
            # heading to center of the next buoy pair   
            tgt_hdg = self.__heading + relative_angle
            
        elif gnext:
            tgt_hdg = self.__heading + gnext[0][0]
            
        elif rnext:
            tgt_hdg = self.__heading + rnext[0][0]
            
        else: # see no buoys
            tgt_hdg = self.__heading
            
        return tgt_hdg

    # choose a command to send to the front seat
    def __select_command(self):
        # Unless we need to issue a command, we will return None
        cmd = None
        
#         if self.__heading is None:
#             return cmd
        
        # determine the angle between current and desired heading
        delta_angle = self.__desired_heading - self.__heading
        
        if delta_angle > 180: # angle too big, go the other way!
            delta_angle = delta_angle - 360
            
        if delta_angle < -180: # angle too big, go the other way!
            delta_angle = delta_angle + 360
        
        # how much do we want to turn the rudder
        ## Note: using STANDARD RUDDER only for now! A calculation here
        ## will improve performance!
        turn_command = f"{delta_angle} DEGREES RUDDER"
        
        if delta_angle > 1:  # need to turn to right!
#             if self.__rudder >= 0:  # rudder is turning to the left
            cmd = f"RIGHT {turn_command}"
            
        elif delta_angle < -1:  # need to turn to left!
#             if self.__rudder <= 0:  # rudder is turning right!
            cmd = f"LEFT {turn_command}"
            
        else:  # close enough!
            cmd = "RUDDER AMIDSHIPS"
            new_rudder = 0
            
        # Convert command to $BPRMB request
        # get direction and rudder position from cmd

        if len(cmd.split(" ")) == 4:
            direction, position = cmd.split(" ")[:2]
            position = int(float(position))
            
            if position == "STANDARD":
                position = 15
                
            elif position == "FULL":
                position = 30
                
            elif position == "HARD":
                position = 35

            if direction == "RIGHT":
                new_rudder = (-position)  # for some reason turning right has a negative angle on Sandshark
            else:
                new_rudder = position
                
#             change_rudder_by = new_rudder - self.__rudder
        
#         else:
#             new_rudder = 0
        
        # Note: Need to change hhmmss in backseat
        cmd = f"BPRMB,hhmmss,{new_rudder},,,750,0,1"
        # hhmmss.ss, Variable precision heading in degrees,
        # Variable precision depth or altitude in meters, Depth mode,
        # RPM or m/s of thruster, Speed mode (0 signifies previous mode was in RPM,
        # 1 signifies previous mode was in m/s),
        # Horizontal mode (0 signifies the first field is a heading; 1 signifies a rudder adjustment)

        return cmd
