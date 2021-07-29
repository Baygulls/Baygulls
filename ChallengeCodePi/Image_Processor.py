#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Jul 22 11:30:37 2021

@author: BWSI AUV Challenge Instructional Staff
"""
### JRE: for simulation only!
### MDM: added Rasperry Pi V2 camera 

import sys
import pathlib
import datetime

import time 
import numpy as np

import os

if "pi" in os.uname().nodename:
    import picamera
    import picamera.array

import cv2
import random

# For simulations
from BWSI_BuoyField import BuoyField
from BWSI_Sensor import BWSI_Camera


class ImageProcessor():
    def __init__(self, camera='SIM', log_dir='./', logger=None):
        self.__camera_type = camera.upper()
        
        if self.__camera_type == 'SIM':
            self.__camera = BWSI_Camera(max_angle=24.4, visibility=50)
            self.__simField = None
            
        else:
            self.__camera = picamera.PiCamera()
            self.__camera.resolution = (640, 480) 
            self.__camera.framerate = 24
            time.sleep(2) # camera warmup time
            self.__image = np.empty((480*640*3,), dtype=np.uint8)
            
        # create my save directory
        self.__image_dir = pathlib.Path(log_dir, 'frames')
        self.__image_dir.mkdir(parents=True, exist_ok=True)
        self.__logger = logger
        
    def sensor_position(pix_x, pix_y, res_x, res_y): # res_x = img.shape[0]; res_y = img.shape[1]
        x = 3.68 # length of camera sensor in mm
        y = 2.76 # height of camera sensor in mm
        # adjust pixel coordinate system so (0, 0) is in the center of the camera sensor, 
        # not at the corner of the pixel frame
        sensor_pos_x_pixel = pix_x - res_x / 2
        sensor_pos_y_pixel = pix_y - res_y / 2
        sensor_pos_x = sensor_pos_x_pixel * x / res_x
        sensor_pos_y = sensor_pos_y_pixel * y / res_y
        return (sensor_pos_x, sensor_pos_y) # position of point on the sensor (mm)
        
    def get_angles(sensor_pos):
        sensor_pos_x, sensor_pos_y = sensor_pos
        f = 3.04 # mm. f: focal length
        # r = f * tanθ
        # θ = arctan(r / f)
        horizontal_angle = np.arctan2(sensor_pos_x, f) * 180 / np.pi
        vertical_angle = np.arctan2(sensor_pos_y, f) * 180 / np.pi
        return (horizontal_angle, vertical_angle)
        
    def get_centers(thresh, img_threshold_color, img):
        # Convert to uint8 so we can find contours around buoys we want to detect
        img8 = (img_threshold_color * 255 / np.max(img)).astype(np.uint8)
        thresh8 = (thresh * 255 / np.max(img)).astype(np.uint8)
        thresh, img_out = cv2.threshold(img8, thresh8, 255, cv2.THRESH_BINARY)
        # The image should still have one of two possible values at each pixel.

        if cv2.__version__ == '3.2.0':
            _, contours, hierarchy = cv2.findContours(img_out, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
            
        else:
            contours, hierarchy = cv2.findContours(img_out, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
            
        buoys = []
        
        for contour in contours:
            center = np.mean(contour, axis=0)[0]
             # ^ Need to index 0 because np.mean(contour, axis=0)...
            # returns np.array([[mean]]) not np.array([mean])
            contour_x_max = np.max(contour, axis=0)[0][0]
            contour_x_min = np.min(contour, axis=0)[0][0]
            contour_y_max = np.max(contour, axis=0)[0][1]
            contour_y_min = np.min(contour, axis=0)[0][1]
            contour_size = (contour_x_max - contour_x_min) * (contour_y_max - contour_y_min)
            
            if contour_size < 1000:
                buoys.append((center, contour_size))
        
        buoys = np.array(sorted(buoys, key=lambda x: x[1], reverse=True), dtype=object) # sort buoys by their size in descending order
    
        return buoys

    def find_angles(centers, res):
        angles = []
        
        for center in centers:
            angle_for_center = ImageProcessor.get_angles(ImageProcessor.sensor_position(center[0], center[1], res[0], res[1]))
            angles.append(angle_for_center)
        
        return angles

    def detect_buoys(self, img):
        img = cv2.boxFilter(img, -1, (10, 10))
        # Find thresholds for Green Buoy
        filter_size = (5, 5) # P: may need to change when we get closer to buoy
        gfilt = cv2.boxFilter(img[:, :, 1], cv2.CV_32F, filter_size)
        # Find thresholds for red buoy
        rfilt = cv2.boxFilter(img[:, :, 2], cv2.CV_32F, filter_size)
        
        if self.__camera_type == "PICAM":
            img_threshold_green = np.logical_and(gfilt > 175, gfilt < 255) # PICAM
            img_threshold_red = np.logical_and(rfilt > 60, rfilt < 255) # PICAM
            
        else:
            img_threshold_green = np.logical_and(gfilt > 150, gfilt < 255) # SIM
            img_threshold_red = np.logical_and(rfilt > 40, rfilt < 255) # SIM
            
        thresh = 0 # img_threshold_red values are either 0 or 1... 
        # but if we used cv2.boxFilter with normalize = False, the pixel values would have values...
        # in range of 0 to the size of the filter

        # Get centers of the buoys using the thresholds
        g_centers = ImageProcessor.get_centers(thresh, img_threshold_green, img)
        r_centers = ImageProcessor.get_centers(thresh, img_threshold_red, img)
        res = img.shape # in the buoy_simulation photos, it was (480, 640, 3). 640 is x axis, 480 is y axis

        # Get angles (horizontal and vertical) from the camera sensor to the buoys
        g_angles = []
        r_angles = []
        
        if len(g_centers) > 0:
            g_angles = ImageProcessor.find_angles(g_centers[:, 0], (res[1], res[0])) # pass in resolution of image to calculate angles
            
        if len(r_centers) > 0:
            r_angles = ImageProcessor.find_angles(r_centers[:, 0], (res[1], res[0]))
            
        return g_centers, r_centers, g_angles, r_angles
    
    # ------------------------------------------------------------------------ #
    # Run an iteration of the image processor. 
    # The sim version needs the auv state to generate simulated imagery
    # the PICAM does not need any auv_state input
    # ------------------------------------------------------------------------ #
    def run(self, auv_state=None):
        red = []
        green = []
        image = None
        
        if self.__camera_type == 'SIM':
            if auv_state['heading'] is not None:
                # if it's the first time through, configure the buoy field
                if self.__simField is None:
                    self.__simField = BuoyField(auv_state['datum'])
                    config = {'nGates': 5,
                              'gate_spacing': 5,
                              'gate_width': 2,
                              'style': 'pool_1',
                              'max_offset': 5,
                              'heading': 0}

                    self.__simField.configure(config)

                # synthesize an image
                image = self.__camera.get_frame(auv_state['position'], auv_state['heading'], self.__simField)
                
        elif self.__camera_type == 'PICAM':
            try:
                self.__camera.capture(self.__image, 'bgr')

            except:
                # restart the camera
                self.__camera = picamera.PiCamera()
                self.__camera.resolution = (640, 480)
                self.__camera.framerate = 24
                time.sleep(2) # camera warmup time
            
            # Reshape the image. this is the image that the camerea took
            image = self.__image.reshape((480, 640, 3)) # y pixels, x pixels, bgr
            # Rotate the image right side up
            image = np.rot90(image, 2) # Dimensions are: 640 x pixels, 480 y pixels
            
        else:
            self.__logger.warning(f"Unknown camera type: {self.__camera_type}")
            sys.exit(-10)
            
        if image is not None:
            # log the image
            fn = self.__image_dir / f"frame_{datetime.datetime.utcnow().timestamp()}.jpg"
            cv2.imwrite(str(fn), image)

            # process and find the buoys!
            g_centers, r_centers, green, red = self.detect_buoys(image)
            
        return g_centers, r_centers, green, red
