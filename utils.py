#utils.py

import os
import cv2
import numpy as np
import logging
from shapely.geometry import Polygon
from ultralytics import YOLO
import pandas as pd
import zipfile

# Настройка базового логирования
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')


def load_zones_for_camera(zone_files_path, camera_name):
    """
    Load zone coordinates from text files corresponding to a specific camera.
    """
    logging.info(f"Loading zones for camera: {camera_name}")
    zone_files = [f for f in os.listdir(zone_files_path) if camera_name in f]
    zones = []
    for file in zone_files:
        with open(os.path.join(zone_files_path, file), 'r') as f:
            coords = [list(map(int, line.strip('[], \n').split(','))) for line in f if line.strip()]
            zones.append(Polygon(coords))
    return zones

def is_within_zone(box, zones):
    """
    Check if the given box overlaps with any of the zones and calculate the overlap percentage.
    """
    box_polygon = Polygon([(box[0], box[1]), (box[2], box[1]), (box[2], box[3]), (box[0], box[3])])
    overlap_percentage = 0
    for zone in zones:
        if box_polygon.intersects(zone):
            intersection_area = box_polygon.intersection(zone).area
            overlap_percentage = round(max(overlap_percentage, (intersection_area / box_polygon.area) * 100), 2)
            if overlap_percentage > 15:
                return True, overlap_percentage
    return False, overlap_percentage

def detect_objects(model, img):
    results = model.predict(img, classes=0, imgsz=1280, iou=0.6)
    for result in results:
        boxes = result.boxes.xyxy.cpu().numpy()
        img_with_box = result.plot()

    return boxes, img_with_box

def draw_zones(img, zones, color=(0, 255, 0), thickness=2):
    """
    Draw the zones on an image.
    """
    logging.info("Drawing zones on image")
    for i, zone in enumerate(zones):
        # Log the coordinates of the zone
        coords = list(zone.exterior.coords)
        # logging.info(f"Zone {i+1}: {coords}")

        # Convert the coordinates to the appropriate numpy array format for polylines
        pts = np.array(coords, np.int32)
        pts = pts.reshape((-1, 1, 2))

        # Draw the zone
        cv2.polylines(img, [pts], isClosed=True, color=color, thickness=thickness)
        # logging.debug(f"Drawn polygon with points: {pts}")

    return img



def draw_box(img, box, color=(255, 0, 0), thickness=2):
    """
    Draw a box on an image.
    """
    x_min, y_min, x_max, y_max = map(int, box)
    cv2.rectangle(img, (x_min, y_min), (x_max, y_max), color, thickness)


def process_images_zip(image_folder_path, zone_files_path, output_folder_path):
    logging.info("Starting to process images for zipping.")
    if not os.path.exists(output_folder_path):
        os.makedirs(output_folder_path)
        logging.info(f"Created output directory at {output_folder_path}")

    results = []
    images_output_folder = os.path.join(output_folder_path, 'images')
    if not os.path.exists(images_output_folder):
        os.makedirs(images_output_folder, exist_ok=True)
        logging.info(f"Created images output directory at {images_output_folder}")

    logging.info("Starting to iterate over image files.")
    for image_file in os.listdir(image_folder_path):
        logging.info(f"Processing file {image_file}")
        camera_name = os.path.basename(os.path.normpath(image_folder_path))
        logging.debug(f'image_folder_path: {image_folder_path}')
        logging.debug(f'camera_name: {camera_name}')
        zones = load_zones_for_camera(zone_files_path, camera_name)
        if not zones:
            logging.warning(f"No zones found for camera {camera_name}.")
        img_path = os.path.join(image_folder_path, image_file)
        img = cv2.imread(img_path)
        if img is None:
            logging.error(f"Failed to read image {img_path}. Skipping file.")
            continue

        logging.info("Detecting objects in image.")
        detected_boxes, img_with_boxes = detect_objects(model, img)
        if detected_boxes.size == 0:
            logging.warning(f"No objects detected in image {img_path}.")

        logging.info("Drawing zones on image.")
        img_with_boxes_and_zone = draw_zones(img_with_boxes, zones)
        for box in detected_boxes:
            in_zone, overlap_percentage = is_within_zone(box, zones)
            # Check if the object is within any zone and update in_zone flag
            if in_zone:
                logging.info(f"Object detected in zone with overlap percentage of {overlap_percentage:.2f}%.")
                text = 'In zone'
                text_box = f'({overlap_percentage:.2f}%)'
                cv2.putText(img_with_boxes_and_zone, text, (30, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
                cv2.putText(img_with_boxes_and_zone, text_box, (int(box[0]), int(box[1]) - 30),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
            else:
                logging.info("Object detected not in zone.")

        output_img_path = os.path.join(images_output_folder, image_file)
        cv2.imwrite(output_img_path, img_with_boxes_and_zone)
        logging.info(f"Image saved to {output_img_path}")

        results.append([image_file, in_zone, overlap_percentage])

    logging.info("Saving results to CSV.")
    df_results = pd.DataFrame(results, columns=['Image', 'ObjectInRestrictedZone', 'OverlapPercentage'])
    csv_output_path = os.path.join(output_folder_path, 'results.csv')
    df_results.to_csv(csv_output_path, index=False)
    logging.info(f"Results CSV saved to {csv_output_path}")

    logging.info("Creating result zip file.")
    result_zip_path = os.path.join(output_folder_path, 'result.zip')
    with zipfile.ZipFile(result_zip_path, 'w') as zipf:
        for file_name in os.listdir(images_output_folder):
            file_path = os.path.join(images_output_folder, file_name)
            zipf.write(file_path, arcname=os.path.join('images', file_name))
            logging.info(f"Added {file_path} to zip file.")
        zipf.write(csv_output_path, arcname='results.csv')
        logging.info(f"Added results CSV to zip file.")

    logging.info("Finished processing images for zip.")
    return result_zip_path

path_yolov8_openvino_weght = 'yolov8m.pt'
# path_yolov8_openvino_weght = 'best_n_1280.pt' # path to custom weight
model = YOLO(path_yolov8_openvino_weght)
