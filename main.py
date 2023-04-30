from google.cloud import firestore
from google.cloud import storage

import cv2
import csv
import os
import datetime
import pytz
import mediapipe as mp
from urllib.parse import unquote

mp_drawing = mp.solutions.drawing_utils
mp_pose = mp.solutions.pose

client = firestore.Client()


def pose_detection(data, context):
    path_parts = context.resource.split('/documents/')[1].split('/')
    user_id = path_parts[1]

    storage_client = storage.Client()

    bucket = storage_client.bucket("athlete-crowd-dev.appspot.com")
    video_file_name = data["value"]["fields"]["videoFileName"]["stringValue"]

    local_file_path = f"/tmp/{video_file_name}"

    dl_blob = bucket.blob(f"uploaded/video/{user_id}/{video_file_name}")
    dl_blob.download_to_filename(local_file_path)

    dt_now = datetime.datetime.now(pytz.timezone('Asia/Tokyo'))
    formatted_dt = dt_now.strftime('%Y-%m-%d-%H-%M-%S')
    output_thumbnail_filename = f"thumbnail_image_{formatted_dt}.jpg"
    output_csv_filename = f"pose_points_{formatted_dt}.csv"

    frameNumber, frame_rate = execute_detection(local_file_path, f"/tmp/{output_csv_filename}",
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

    motion_record_data = {"boneCsvFileName": output_csv_filename, "id": motion_record_ref.id, "userId": user_id, "markers": [],
                          "motionTypeRef": default_motion_type_ref, "comment": "",
                          "thumbnailFileName": output_thumbnail_filename, "createdAt": firestore.SERVER_TIMESTAMP,
                          "updatedAt": firestore.SERVER_TIMESTAMP, "isActive": frame_rate != None,
                          "model": "mediapipe-default", "shootedDate": firestore.SERVER_TIMESTAMP,
                          "shootingVerticalAngle": 0, "shootingHorizontalAngle": 90, "title": "未設定",
                          "version": 0, "videoFileName": video_file_name, "frameNumber": frameNumber, "fps": frame_rate}

    motion_record_ref.set(motion_record_data)

    print("Success convert preMotionRecord to motionRecord")


def execute_detection(video_path, output_csv_path, output_thumbnail_path):
    cap = cv2.VideoCapture(video_path)
    frame_rate = cap.get(cv2.CAP_PROP_FPS)

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
                            row_data.append(landmark.z)

                    else:
                        row_data = [0] * 99  # 33 landmarks * 2 (x, y)

                    writer.writerow(row_data)

                    if frame_number == 0:
                        cv2.imwrite(output_thumbnail_path, frame, [
                                    cv2.IMWRITE_JPEG_QUALITY, 50])

                    frame_number += 1
                else:
                    break

    cap.release()
    return frame_number, frame_rate
