"""
BWSI_BackSeat.py will call `detect_buoys()` and pass in the .jpg image with the resolution of
640 x 480.

`detect_buoys()` will return g_centers, r_centers, g_angles, r_angles
g_centers: a list of tuples. Each tuple contains a coordinate of the center of a green buoy detected, 
in order of largest to smallest buoy
r_centers: same as above, but with red buoys
g_angles: A list of tuples containing the horizontal and vertical angle from the camera sensor to the 
green buoys detected in order of largest to smallest buoy
r_angles: same as above, but with red buoys
"""

import numpy as np
import cv2
import matplotlib.pyplot as plt

class BuoyDetector():
    def __init__(self, filter_size=(10, 10), green=(0, 120), red=(0, 150), threshold=0, logger=None):
        self.__filter_size = filter_size
        self.__green = green
        self.__red = red
        self.__threshold = threshold
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
        horizontal_angle = np.rad2deg(np.arctan2(sensor_pos_x, f))
        vertical_angle = np.rad2deg(np.arctan2(sensor_pos_y, f))
        return (horizontal_angle, vertical_angle)

    def get_centers(thresh, img_threshold_color, img):
        # Convert to uint8 so we can find contours around buoys we want to detect
        img8 = (img_threshold_color * 255 / np.max(img)).astype(np.uint8)
        thresh8 = (thresh * 255 / np.max(img)).astype(np.uint8)
        thresh, img_out = cv2.threshold(img8, thresh8, 255, cv2.THRESH_BINARY)
        # The image should still have one of two possible values at each pixel.
        contours, hierarchy = cv2.findContours(img_out, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
        buoys = []

        for contour in contours:
            center = np.mean(contour, axis=0)[0]
             # ^ Need to index 0 because np.mean(contour, axis=0)...
            # returns np.array([[mean]]) not np.array([mean])
            contour_x = np.max(contour, axis=0)[0][0]
            contour_y = np.max(contour, axis=0)[0][1]
            contour_size = contour_x * contour_y
            buoys.append((center, contour_size))

        buoys = sorted(buoys, key=lambda x: x[1], reverse=True)
        return np.array(buoys, dtype=object)

    def find_angles(centers, res):
        angles = []

        for center in centers:
            angle_for_center = BuoyDetector.get_angles(BuoyDetector.sensor_position(center[0], center[1], res[0], res[1]))
            angles.append(angle_for_center)

        return angles

    def detect_buoys(self, img):
        img = cv2.boxFilter(img, -1, (5, 5))
        # Find thresholds for Green Buoy
        filter_size = (10, 10) # P: may need to change when we get closer to buoy
        gfilt = cv2.boxFilter(img[:, :, 1], cv2.CV_32F, self.__filter_size)
        img_threshold_green = np.logical_and(self.__green[0] < gfilt, gfilt < self.__green[1])

        # Find thresholds for red buoy
        rfilt = cv2.boxFilter(img[:, :, 2], cv2.CV_32F, filter_size)
        img_threshold_red = np.logical_and(self.__red[0] < rfilt, rfilt < self.__red[1])
        
        if False and self.__logger is not None:
            self.__logger.info(np.argwhere(img_threshold_green))
        
        # img_threshold_red values are either 0 or 1... 
        # but if we used cv2.boxFilter with normalize = False, the pixel values would have values...
        # in range of 0 to the size of the filter

        # Get centers of the buoys using the thresholds
        g_centers = BuoyDetector.get_centers(self.__threshold, img_threshold_green, img)
        r_centers = BuoyDetector.get_centers(self.__threshold, img_threshold_red, img)
        res = img.shape # in the buoy_simulation photos, it was (480, 640, 3). 480 is y axis, 640 is x axis
        
#         if self.__logger is not None:
#             self.__logger.info("*!!1!21!@#@3$@5#^475*RETDHR***" + str((g_centers[:], g_centers[:]))) #, r_centers[:], g_angles, r_angles)))
            
        # Get angles (horizontal and vertical) from the camera sensor to the buoys
        g_angles = []
        r_angles = []
        
        if len(g_centers) > 0:
            g_angles = BuoyDetector.find_angles(g_centers[:, 0], (res[1], res[0])) # pass in resolution of image to calculate angles
            
        if len(r_centers) > 0:
            r_angles = BuoyDetector.find_angles(r_centers[:, 0], (res[1], res[0]))
        
        return (g_centers, r_centers, g_angles, r_angles)

# # This was for testing if detect_buoys() works
# doPlots = False # Plots from lab15
# if doPlots:
#     fig, ax = plt.subplots()
#     for frame_num in range(1627084245, 1627084283):
#         filename = f'frames/frame_{frame_num}.jpg'
#         # img = cv2.imread(f'frames/frame_1627084245.jpg')
#         print(filename)
#         try:
#             img = cv2.imread(filename)
#             g_centers, r_centers, g_angles, r_angles = detect_buoys(img)
#             print("g_angles", g_angles)
#             print('\n')
#             print("r_angles", r_angles)
#             ax.clear()
#             ax.imshow(np.flip(img, axis=2)) # plot in RGB
#             for g_center in g_centers:
#                 ax.plot(g_center[0], g_center[1], 'bo')
#             for r_center in r_centers:
#                 ax.plot(r_center[0], r_center[1], 'ko')
#             plt.pause(0.1)
#             plt.draw()
#             # plt.show()
#         except:
#             pass