from google.cloud import firestore
from google.cloud import storage

import re
import cv2
import csv
import os
import datetime
import mediapipe as mp
from urllib.parse import unquote

mp_drawing = mp.solutions.drawing_utils
mp_pose = mp.solutions.pose

client = firestore.Client()


# Converts strings added to /messages/{pushId}/original to uppercase

def pose_detection(data, context):
    path_parts = context.resource.split('/documents/')[1].split('/')
    user_id = path_parts[1]

    storage_client = storage.Client()

    bucket = storage_client.bucket("athlete-crowd-dev.appspot.com")
    video_url = unquote(data["value"]["fields"]["videoUrl"]["stringValue"])
    download_path = video_url.split("athlete-crowd-dev.appspot.com/o/")[1]

    pattern = r'\/([^%]+)\?'
    match = re.search(pattern, download_path)

    filename = match.group(1).split("/")[-1]

    local_file_path = f"/tmp/{filename}"
    # %2Fを/に置換。replace("%2F", "/")だとFしか置換されない
    storage_path = download_path.split("?")[0]

    dl_blob = bucket.blob(storage_path)
    dl_blob.download_to_filename(local_file_path)

    dt_now = datetime.datetime.now()
    formatted_dt = dt_now.strftime('%Y-%m-%d-%H-%M-%S')
    output_thumbnail_filename = f"thumbnail_image_{formatted_dt}.jpg"
    output_csv_filename = f"pose_points_{formatted_dt}.csv"

    execute_detection(local_file_path, f"/tmp/{output_csv_filename}",
                      f"/tmp/{output_thumbnail_filename}")

    up_csv_blob = bucket.blob(
        f"uploaded/csv/{user_id}/{output_csv_filename}")
    up_csv_blob.upload_from_filename(f"/tmp/{output_csv_filename}")

    up_thumbnail_blob = bucket.blob(
        f"uploaded/thumbnail/{user_id}/{output_thumbnail_filename}")
    up_thumbnail_blob.upload_from_filename(
        f"/tmp/{output_thumbnail_filename}")

    os.remove(local_file_path)
    os.remove(f'/tmp/{output_csv_filename}')
    os.remove(f'/tmp/{output_thumbnail_filename}')

    motion_record_ref = client.collection("user").document(
        user_id).collection("motion_record").document()
    default_motion_type_ref = client.collection("sport_type").document("bwukr89IMu8vpbUse58w").collection(
        "event_type").document("ZuNCp9bLyvWrujKckiB6").collection("motion_type").document("lg4teMIv0cyEXl9tDyZ9")

    motion_record_data = {"boneCsvUrl": up_csv_blob.path, "id": motion_record_ref.id,
                          "motionTypeRef": default_motion_type_ref, "comment": "",
                          "thumbnailUrl": up_thumbnail_blob.path, "createdAt": firestore.SERVER_TIMESTAMP,
                          "updatedAt": firestore.SERVER_TIMESTAMP, "isActive": False,
                          "model": "mediapipe-default", "shootedDate": firestore.SERVER_TIMESTAMP,
                          "shootingVerticalAngle": 0, "shootingHorizontalAngle": 90, "title": "未設定",
                          "version": 0, "videoUrl": video_url}

    motion_record_ref.set(motion_record_data)

    print("Success convert preMotionRecord to motionRecord")


def execute_detection(video_path, output_csv_path, output_thumbnail_path):
    cap = cv2.VideoCapture(video_path)

    if not cap.isOpened():
        return

    with mp_pose.Pose(static_image_mode=False, min_detection_confidence=0, min_tracking_confidence=0.4) as pose:
        frame_number = 0

        with open(output_csv_path, "w", newline="") as csvfile:
            writer = csv.writer(csvfile)

            while cap.isOpened():
                ret, frame = cap.read()
                if ret:
                    # 姿勢推定処理
                    results = pose.process(
                        cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))

                    row_data = []
                    if results.pose_landmarks:
                        image_height, image_width, _ = frame.shape

                        for i, landmark in enumerate(results.pose_landmarks.landmark):
                            row_data.append(landmark.x * image_width)
                            row_data.append(landmark.y * image_height)

                    else:
                        row_data = [0] * 66  # 33 landmarks * 2 (x, y)

                    writer.writerow(row_data)

                    if frame_number == 0:
                        cv2.imwrite(output_thumbnail_path, frame, [
                                    cv2.IMWRITE_JPEG_QUALITY, 50])

                    frame_number += 1
                else:
                    break

    cap.release()
