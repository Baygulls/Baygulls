# -*- coding: utf-8 -*-
"""
Created on Sat Apr  3 19:49:45 2021

@author: BWSI AUV Challenge Instructional Staff
"""
import sys

import numpy as np
import BWSI_BuoyField

class BWSI_Camera(object):
    def __init__(self, max_angle=90, visibility=100):
        self.__MAX_RANGE = visibility # maximum range camera can see
        self.__MAX_ANGLE = max_angle # field of view of camera (+/- MAX_ANGLE degrees)
        self.__SENSOR_TYPE = 'ANGLE'
        
        # Parameters relevant for simulating camera images
        self.__Wpix = 640
        self.__Hpix = 480
        self.__max_angle_W = 31.1
        self.__max_angle_H = 24.4
    
        # calculate the horizontal and vertical angles to the pixels
        deg_per_pix_W = 2*self.__max_angle_W /  self.__Wpix
        deg_per_pix_H = 2*self.__max_angle_H /  self.__Hpix
    
        self.__angles_W = (np.arange(0, self.__Wpix) - (self.__Wpix-1)/2) * deg_per_pix_W
        self.__angles_H = np.flip((np.arange(0, self.__Hpix) - (self.__Hpix-1)/2) * deg_per_pix_H)
    
    
        self.__image_mat = np.zeros((self.__Hpix, self.__Wpix, 3), dtype=np.uint8)
        background = (184, 233, 238) # blue-green
    
        # blue-green background base image
        self.__image_mat[:,:,0].fill(background[0])
        self.__image_mat[:,:,1].fill(background[1])
        self.__image_mat[:,:,2].fill(background[2])
        
        self.image_snap = None

        
    def get_visible_buoys(self, pos, hdg, buoy_field):
        angle_left = np.mod(hdg-self.__MAX_ANGLE+360, 360)
        angle_right = np.mod(hdg+self.__MAX_ANGLE, 360)
        G, R = buoy_field.detectable_buoys(pos, 
                                           self.__MAX_RANGE, 
                                           angle_left,
                                           angle_right,
                                           self.__SENSOR_TYPE)
        
        for i in range(len(G)):
            G[i] = np.mod(G[i] - hdg + 360, 360)
            if G[i]>self.__MAX_ANGLE:
                G[i] = G[i] - 360.0
            if G[i]<-self.__MAX_ANGLE:
                G[i] = G[i] + 360.0
            
        for i in range(len(R)):
            R[i] = np.mod(R[i] - hdg + 360, 360)
            if R[i]>self.__MAX_ANGLE:
                R[i] = R[i] - 360.0
            if R[i]<-self.__MAX_ANGLE:
                R[i] = R[i] + 360.0
                
        return G, R
    
    def get_frame(self, pos, hdg, buoy_field):
        G, R = self.get_visible_buoys_with_range(pos, hdg, buoy_field)
        # print(f"{len(G)}, {len(R)}")
        image_snap = self.__image_mat.copy()
        for g in G:
            buoy_range, true_heading = g
            relative_heading = true_heading - hdg
            # JRE: hard-coding 1-m depth separation for now!
            elev = np.degrees(np.tan(1/buoy_range))
        
            # find the region of the image that this buoy spans
            # print(f"buoy_range = {buoy_range}")
            image_snap = self.add_buoy_to_image(image_snap, buoy_range, relative_heading, elev, 'green')
            
        for r in R:
            buoy_range, true_heading = r
            relative_heading = true_heading-hdg
            # JRE: hard-coding 1-m depth separation for now!
            elev = np.degrees(np.tan(1/buoy_range))
        
            # find the region of the image that this buoy spans
            # print(f"buoy_range = {buoy_range}")
            image_snap = self.add_buoy_to_image(image_snap, buoy_range, relative_heading, elev, 'red')
            
            
        image_snap = image_snap + np.random.normal(0, 20, (self.__Hpix, self.__Wpix, 3)).astype(int)
        image_snap[image_snap>255] = 255
        image_snap[image_snap<0] = 0
        
        # make it BGR since we're working with cv2
        image_snap = np.flip(image_snap, axis=2)

            
        return image_snap
            

    

    def add_buoy_to_image(self, image_snap, R, hdg, elev, color, buoy_size=0.25):
        if color.lower() == 'red':
            buoy_color = np.array([220, 30, 45], dtype=np.uint8)
        elif color.lower() == 'green':
            buoy_color = np.array([30, 220, 45], dtype=np.uint8)
        else:
            print(f"Unknown color: {color}")
            sys.exit()
            
            
        # print(f"Adding buoy at rel dg = {hdg}, elev = {elev}")

        vis_rng = self.__MAX_RANGE

        H = R * np.tan(np.radians(elev))
        max_y = np.degrees(np.arctan( (H + buoy_size/2)/R ) )
        min_y = np.degrees(np.arctan( (H - buoy_size/2)/R ) )
    
        yrng = np.where(np.logical_and(self.__angles_H<=max_y, self.__angles_H>=min_y))
    
        H = R * np.tan(np.radians(hdg))
        max_x = np.degrees(np.arctan( (H + buoy_size/2)/R ) )
        min_x = np.degrees(np.arctan( (H - buoy_size/2)/R ) )
    
        # find the pixels that fit here
        xrng = np.where(np.logical_and(self.__angles_W<=max_x, self.__angles_W>=min_x))

        # should never be > 1, but just in case...    
        frac = np.min((R/vis_rng, 1))
        
        vis_colr = (frac * image_snap[0,0,:] + (1-frac)*buoy_color).astype(np.uint8)
    
        for y in yrng[0]:
            for x in xrng[0]:
                image_snap[y, x, :] = vis_colr
                
        return image_snap
    
        

    def get_visible_buoys_with_range(self, pos, hdg, buoy_field):
        angle_left = np.mod(hdg-self.__MAX_ANGLE+360, 360)
        angle_right = np.mod(hdg+self.__MAX_ANGLE, 360)
        
        G, R = buoy_field.detectable_buoys(pos, 
                                           self.__MAX_RANGE, 
                                           angle_left,
                                           angle_right,
                                           'RANGE_ANGLE')
        
        return G, R
        
    
    
class BWSI_Laser(object):
    def __init__(self, visibility):
        self.__MAX_RANGE = visibility # maximum range camera can see
        self.__MAX_ANGLE = 85.0 # field of view of camera (+/- MAX_ANGLE degrees)
        self.__SENSOR_TYPE = 'RANGE_ANGLE'
        
    def get_visible_buoys(self, pos, hdg, buoy_field):
        angle_left = np.mod(hdg-self.__MAX_ANGLE+360, 360)
        angle_right = np.mod(hdg+self.__MAX_ANGLE, 360)
        G, R = buoy_field.detectable_buoys(pos, 
                                           self.__MAX_RANGE, 
                                           angle_left,
                                           angle_right,
                                           self.__SENSOR_TYPE)
                
        return G, R