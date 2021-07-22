"""
BWSI_BackSeat.py will call `detect_buoys()` and pass in the .jpg image with the resolution of
640 x 360.

(If we can only get images with a different resolution,
someone will need to add a line that will resize the image in the `detect_buoys` function)

`detect_buoys()` will return g_centers, r_centers, g_angles, r_angles
g_centers: a list of tuples. Each tuple contains a coordinate of the center of a green buoy detected
r_centers: same as above, but with red buoys
g_angles: a list of tuples. Each tuple contains the horizontal and vertical angle from the
camera sensor to the buoys
r_angles: same as above, but with red buoys
"""
import cv2
import matplotlib.pyplot as plt
import numpy as np


# res_x = img.shape[0]; res_y = img.shape[1]
def sensor_position(pix_x, pix_y, res_x, res_y):
    x = 3.68  # length of camera sensor in mm
    y = 2.76  # height of camera sensor in mm
    # adjust pixel coordinate system so (0, 0) is in the center of the camera sensor,
    # not at the corner of the pixel frame
    sensor_pos_x_pixel = pix_x - res_x / 2
    sensor_pos_y_pixel = pix_y - res_y / 2
    sensor_pos_x = round(sensor_pos_x_pixel * x / res_x, 5)
    sensor_pos_y = round(sensor_pos_y_pixel * y / res_y, 5)
    return (sensor_pos_x, sensor_pos_y)  # position of point on the sensor (mm)


def get_angles(sensor_pos):
    sensor_pos_x, sensor_pos_y = sensor_pos
    f = 3.04  # mm. f: focal length
    # r = f * tanθ
    # θ = arctan(r / f)
    horizontal_angle = np.arctan2(sensor_pos_x, f) * 180 / np.pi
    vertical_angle = np.arctan2(sensor_pos_y, f) * 180 / np.pi
    return (horizontal_angle, vertical_angle)


def get_centers(thresh, img_threshold_color):
    # Convert to uint8 so we can find contours around buoys we want to detect
    img8 = (img_threshold_color * 255 / np.max(img)).astype(np.uint8)
    thresh8 = (thresh * 255 / np.max(img)).astype(np.uint8)
    thresh, img_out = cv2.threshold(img8, thresh8, 255, cv2.THRESH_BINARY)
    """The image should still have one of two possible values at each pixel."""
    contours, hierarchy = cv2.findContours(img_out, cv2.RETR_EXTERNAL,
                                           cv2.CHAIN_APPROX_NONE)
    centers = []
    for contour in contours:
        center = np.mean(contour, axis=0)[0]
        centers.append(center)
        # ^ Need to index 0 because np.mean(contour, axis=0)...
        # returns np.array([[mean]]) not np.array([mean])
    return centers


def find_angles(centers, res):
    angles = []
    for center in centers:
        angle_for_center = get_angles(
            sensor_position(center[0], center[1], res[0], res[1]))
        angles.append(angle_for_center)
    return angles


def detect_buoys(img):
    img = cv2.boxFilter(img, -1, (5, 5))
    # Find thresholds for Green Buoy
    filter_size = (10, 10)  # P: may need to change when we get closer to buoy
    rfilt = cv2.boxFilter(img[:, :, 0], cv2.CV_32F, filter_size)
    img_threshold_green = np.logical_and(rfilt > 0, rfilt < 120)

    # Find thresholds for red buoy
    gfilt = cv2.boxFilter(img[:, :, 1], cv2.CV_32F, filter_size)
    img_threshold_red = np.logical_and(gfilt > 0, gfilt < 150)
    thresh = 0  # img_threshold_red values are either 0 or 1...
    # but if we used cv2.boxFilter with normalize = False, the pixel values would have values...
    # in range of 0 to the size of the filter

    # Get centers of the buoys using the thresholds
    g_centers = get_centers(thresh, img_threshold_green)
    r_centers = get_centers(thresh, img_threshold_red)
    # in the buoy_simulation photos, it was (480, 640, 3). 480 is y axis, 640 is x axis
    res = img.shape
    # print(res)
    res_x = res[1]
    res_y = res[0]

    # Get angles (horizontal and vertical) from the camera sensor to the buoys
    # pass in resolution of image to calculate angles
    g_angles = find_angles(g_centers, (res_x, res_y))
    r_angles = find_angles(r_centers, (res_x, res_y))
    return g_centers, r_centers, g_angles, r_angles


doPlots = False  # Plots from lab15
if doPlots:
    fig, ax = plt.subplots()
    for frame_num in range(0, 20):
        img = cv2.imread(f"buoy_simulation/frame_{frame_num:02d}.jpg")
        img = np.flip(img, axis=2)  # Convert BGR to RGB
        g_centers, r_centers, g_angles, r_angles = detect_buoys(img)
        print("g_angles", g_angles)
        print("\n")
        print("r_angles", r_angles)
        ax.clear()
        ax.imshow(img)
        for g_center in g_centers:
            ax.plot(g_center[0], g_center[1], "bo")
        for r_center in r_centers:
            ax.plot(r_center[0], r_center[1], "ko")
        plt.pause(0.0001)
        plt.draw()
