from tkinter import filedialog
import glob
import csv
import cv2
import mediapipe as mp
import os
mp_drawing = mp.solutions.drawing_utils
mp_pose = mp.solutions.pose

dir = os.getcwd()
fle = filedialog.askdirectory(initialdir=dir)
test_name = fle.split("/")[-1].split(".")[0]


def execute_detection(test_name: str):
    video = glob.glob(f"data/{test_name}/*.MP4")
    cap = cv2.VideoCapture(video[0])
    fps = cap.get(cv2.CAP_PROP_FPS)

    if not cap.isOpened():
        return

    with mp_pose.Pose(static_image_mode=False, min_detection_confidence=0, min_tracking_confidence=0.4) as pose:
        frame_number = 0

        with open(f"data/{test_name}/bone_data_{test_name}.csv", "w", newline="") as csvfile:
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
                            # 扱いやすいよう、画面上部を正方向とするよう変換
                            row_data.append(
                                image_height - landmark.y * image_height)
                            row_data.append(landmark.z)

                    else:
                        row_data = [0] * 99

                    writer.writerow(row_data)

                    frame_number += 1
                else:
                    break

    cap.release()


execute_detection(test_name)
