from cloudevents.http import CloudEvent
import functions_framework
from google.cloud import storage
from google.cloud import firestore
from google.events.cloud import firestore as firestoredata

import cv2
import csv
import copy
import os
import datetime
import pytz
import math


client = firestore.Client()

colors = {
    "red": (0, 0, 255),
    "blue": (255, 0, 0),
    "green": (0, 255, 0),
    "yellow": (0, 255, 255),
    "white": (255, 255, 255),
    "black": (0, 0, 0)
}


@functions_framework.cloud_event
def generate_download_video(cloud_event: CloudEvent):
    print(f"start generate_download_video {cloud_event}")
    firestore_payload = firestoredata.DocumentEventData()
    firestore_payload._pb.ParseFromString(cloud_event.data)

    path_parts = firestore_payload.value.name.split("/")
    separator_idx = path_parts.index("documents")

    try:
        doc_id = path_parts[separator_idx + 4]
        user_id = path_parts[separator_idx + 2]

        storage_client = storage.Client()
        bucket = storage_client.bucket(
            "athlete-crowd-dev-3f1f2.appspot.com")  # dev用
        # # bucket = storage_client.bucket(
        # #     "athlete-crowd-production.appspot.com")  # prod用

        baseUserId = firestore_payload.value.fields["baseUserId"].string_value
        targetUserId = firestore_payload.value.fields["targetUserId"].string_value

        video_file_name = firestore_payload.value.fields["videoFileName"].string_value
        video_path = f"/tmp/{video_file_name}"
        dl_blob = bucket.blob(f"uploaded/video/{baseUserId}/{video_file_name}")
        dl_blob.download_to_filename(video_path)

        csv_file_name = firestore_payload.value.fields["csvFileName"].string_value
        csv_path = f"/tmp/{csv_file_name}"
        dl_blob = bucket.blob(f"uploaded/csv/{baseUserId}/{csv_file_name}")
        dl_blob.download_to_filename(csv_path)

        csv_file_name_target = firestore_payload.value.fields["csvFileNameTarget"].string_value
        csv_target_path = f"/tmp/{csv_file_name_target}"

        if csv_file_name_target != "":
            dl_blob = bucket.blob(
                f"uploaded/csv/{targetUserId}/{csv_file_name_target}")
            dl_blob.download_to_filename(csv_target_path)

        csv_reader_base = []
        csv_reader_target = []

        overlap_frame_base = firestore_payload.value.fields["overlapFrameBase"].integer_value
        overlap_frame_target = firestore_payload.value.fields["overlapFrameTarget"].integer_value
        target_fps = firestore_payload.value.fields["targetFps"].double_value
        base_color = firestore_payload.value.fields["baseColor"].string_value
        target_color = firestore_payload.value.fields["targetColor"].string_value

        dt_now = datetime.datetime.now(pytz.timezone('Asia/Tokyo'))
        formatted_dt = dt_now.strftime('%Y-%m-%d-%H-%M-%S')
        output_video_file_name = f"download_{formatted_dt}_{video_file_name}"

        with open(csv_path, encoding='utf8', newline='') as f:
            csv_reader_base = list(csv.reader(f, delimiter=' ', quotechar='|'))
        if csv_file_name_target != "":
            with open(csv_target_path, encoding='utf8', newline='') as f:
                csv_reader_target = list(csv.reader(
                    f, delimiter=' ', quotechar='|'))

        cap = cv2.VideoCapture(video_path)
        fps = cap.get(cv2.CAP_PROP_FPS)
        h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))

        out = cv2.VideoWriter(
            f"/tmp/{output_video_file_name}", cv2.VideoWriter_fourcc(*'mp4v'), fps, (w, h))

        index = 0

        target_index_value = (overlap_frame_target *
                              (fps / target_fps) - overlap_frame_base) * (target_fps / fps)

        while True:
            ret, frame = cap.read()
            if ret:
                image = copy.deepcopy(frame)
                csv_row = csv_reader_base[index][0].split(',')

                keypoints = []

                for points in range(0, len(csv_row), 3):

                    keypoints.append(
                        (round(float(csv_row[points])), round(float(csv_row[points+1]))))

                drawed_image = draw_human_pose(
                    image, keypoints, colors[base_color])

                if csv_file_name_target != "":
                    if 0 <= math.floor(target_index_value) and len(csv_reader_target) > math.floor(target_index_value):
                        target_index = math.floor(target_index_value)
                        csv_row = csv_reader_target[target_index][0].split(',')

                        compare_keypoints = []

                        for points in range(0, len(csv_row), 3):

                            compare_keypoints.append(
                                (round(float(csv_row[points])), round(float(csv_row[points+1]))))

                        base_height = get_height(keypoints)
                        compare_height = get_height(compare_keypoints)

                        converted_compare_keypoints = []

                        base_hip_center = ((keypoints[23][0] + keypoints[24][0])//2,
                                           (keypoints[23][1] + keypoints[24][1])//2)
                        compare_hip_center = ((compare_keypoints[23][0] + compare_keypoints[24][0])//2,
                                              (compare_keypoints[23][1] + compare_keypoints[24][1])//2)

                        ratio = 1

                        if compare_height != 0:
                            ratio = base_height / compare_height

                        for compare_keypoint in compare_keypoints:
                            adjusted_keypoint = get_adjusted_for_base_point(
                                base_hip_center, compare_hip_center, compare_keypoint, ratio)
                            converted_compare_keypoints.append(
                                adjusted_keypoint)
                        drawed_image = draw_human_pose(
                            drawed_image, converted_compare_keypoints,  colors[target_color])

                out.write(cv2.resize(drawed_image,   # 画像データを指定
                                     (w, h)   # リサイズ後のサイズを指定
                                     ))
                index += 1
                target_index_value += target_fps / fps
            else:
                break

        cap.release()
        out.release()

        up_video_blob = bucket.blob(
            f"download/video/{user_id}/{output_video_file_name}")
        up_video_blob.upload_from_filename(f"/tmp/{output_video_file_name}")

        os.remove(f'/tmp/{output_video_file_name}')
        os.remove(f'/tmp/{video_file_name}')
        os.remove(f'/tmp/{csv_file_name}')

        if csv_file_name_target != "":
            os.remove(f'/tmp/{csv_file_name_target}')

        client.collection('user').document(user_id).collection(
            'download_video').document(doc_id).update({
                "isCompleted": True,
                "generatedVideoFileName": output_video_file_name,
                "generatedAt": firestore.SERVER_TIMESTAMP,
            })

        print(f"Success generate video for download {user_id} : {doc_id}")

    except Exception:
        print('Error on generate video for download')


def draw_human_pose(
    image,
    keypoints,
    color
):
    debug_image = copy.deepcopy(image)

    def draw_circle(keypoint):
        cv2.circle(debug_image, keypoint, 8, color, -1)

    def draw_line(start_keypoint, end_keypoint):
        cv2.line(debug_image, start_keypoint,
                 end_keypoint, color, 4)

    draw_circle(keypoints[11])  # Left shoulder
    draw_circle(keypoints[12])  # Right shoulder

    ear_center = (
        (keypoints[7][0] + keypoints[8][0])//2, (keypoints[7][1] + keypoints[8][1])//2)
    shoulder_center = (
        (keypoints[11][0] + keypoints[12][0])//2, (keypoints[11][1] + keypoints[12][1])//2)
    hip_center = ((keypoints[23][0] + keypoints[24][0])//2,
                  (keypoints[23][1] + keypoints[24][1])//2)

    draw_circle(ear_center)  # Ear center
    draw_circle(shoulder_center)  # Shoulder center
    draw_circle(hip_center)  # Hip center
    draw_line(ear_center, shoulder_center)
    draw_line(shoulder_center, hip_center)

    draw_line(keypoints[11], keypoints[12])  # Left shoulder to right shoulder
    draw_line(keypoints[23], keypoints[24])  # Left hip to right hip

    draw_circle(keypoints[13])  # Left elbow
    draw_circle(keypoints[14])  # Right elbow
    draw_circle(keypoints[15])  # Left wrist
    draw_circle(keypoints[16])  # Right wrist
    draw_circle(keypoints[19])  # Left index
    draw_circle(keypoints[20])  # Right index

    draw_line(keypoints[11], keypoints[13])  # Left shoulder to left elbow
    draw_line(keypoints[13], keypoints[15])  # Left elbow to left wrist
    draw_line(keypoints[15], keypoints[19])  # Left wrist to left index

    draw_line(keypoints[12], keypoints[14])  # Right shoulder to right elbow
    draw_line(keypoints[14], keypoints[16])  # Right elbow to right wrist
    draw_line(keypoints[16], keypoints[20])  # Right wrist to right index

    draw_circle(keypoints[25])  # Left knee
    draw_circle(keypoints[26])  # Right knee
    draw_circle(keypoints[27])  # Left ankle
    draw_circle(keypoints[28])  # Right ankle
    draw_circle(keypoints[29])  # Left heel
    draw_circle(keypoints[30])  # Right heel
    draw_circle(keypoints[31])  # Left foot index
    draw_circle(keypoints[32])  # Right foot index

    draw_line(keypoints[23], keypoints[25])  # Left hip to left knee
    draw_line(keypoints[25], keypoints[27])  # Left knee to left ankle
    draw_line(keypoints[27], keypoints[29])  # Left ankle to left heel
    draw_line(keypoints[29], keypoints[31])  # Left heel to left foot index

    draw_line(keypoints[24], keypoints[26])  # Right hip to right knee
    draw_line(keypoints[26], keypoints[28])  # Right knee to right ankle
    draw_line(keypoints[28], keypoints[30])  # Right ankle to right heel
    draw_line(keypoints[30], keypoints[32])  # Right hee

    return debug_image


def get_height(keypoints):
    def calculate_distance(point1, point2):
        x1, y1 = point1
        x2, y2 = point2
        distance = math.sqrt((x2 - x1)**2 + (y2 - y1)**2)
        return distance

    ear_center = (
        (keypoints[7][0] + keypoints[8][0])//2, (keypoints[7][1] + keypoints[8][1])//2)
    shoulder_center = (
        (keypoints[11][0] + keypoints[12][0])//2, (keypoints[11][1] + keypoints[12][1])//2)
    hip_center = ((keypoints[23][0] + keypoints[24][0])//2,
                  (keypoints[23][1] + keypoints[24][1])//2)
    knee_center = ((keypoints[25][0] + keypoints[26][0])//2,
                   (keypoints[25][1] + keypoints[26][1])//2)
    heel_center = ((keypoints[29][0] + keypoints[30][0])//2,
                   (keypoints[29][1] + keypoints[30][1])//2)

    height = calculate_distance(ear_center, shoulder_center) + calculate_distance(shoulder_center, hip_center) + \
        calculate_distance(hip_center, knee_center) + \
        calculate_distance(knee_center, heel_center)
    return height


def get_adjusted_for_base_point(base_overlap_point, target_overlap_point, target_point, ratio):
    if (base_overlap_point[0] == 0 and base_overlap_point[1] == 0) or (target_overlap_point[0] == 0 and target_overlap_point[1] == 0):
        return (0, 0)

    start = base_overlap_point
    end = (target_point[0] + base_overlap_point[0] - target_overlap_point[0],
           target_point[1] + base_overlap_point[1] - target_overlap_point[1])

    abX = end[0] - start[0]
    abY = end[1] - start[1]

    ab_length = math.sqrt(abX * abX + abY * abY)

    distance_to_c = ab_length * ratio

    ab_unitX = abX / ab_length
    ab_unitY = abY / ab_length

    return (round(start[0] + ab_unitX * distance_to_c), round(start[1] + ab_unitY * distance_to_c))
