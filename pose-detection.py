import cv2
import mediapipe as mp

mp_drawing = mp.solutions.drawing_utils
mp_pose = mp.solutions.pose

def process_video(video_path, output_path):
    cap = cv2.VideoCapture(video_path)

    if not cap.isOpened():
        return

    # 動画のフレームレートとサイズを取得
    fps = int(cap.get(cv2.CAP_PROP_FPS))
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    # 出力動画の設定
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

    with mp_pose.Pose(static_image_mode=False, min_detection_confidence=0, min_tracking_confidence=0.4) as pose:
        while cap.isOpened():
            ret, frame = cap.read()
            if ret:
                # 姿勢推定処理
                results = pose.process(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))

                if results.pose_landmarks:
                    image_height, image_width, _ = frame.shape
                    print(
                        f'Nose coordinates: ('
                        f'{results.pose_landmarks.landmark[mp_pose.PoseLandmark.NOSE].x * image_width}, '
                        f'{results.pose_landmarks.landmark[mp_pose.PoseLandmark.NOSE].y * image_height})'
                    )
                    # ランドマークの描画
                    mp_drawing.draw_landmarks(
                        frame, results.pose_landmarks, mp_pose.POSE_CONNECTIONS)

                # フレームを出力動画に書き込む
                out.write(frame)
            else:
                break

    cap.release()
    out.release()


video_path = 'trim.mp4'
output_path = 'output_video.mp4'

process_video(video_path, output_path)

# 静止画像の場合：
# with mp_pose.Pose(
#     static_image_mode=True, min_detection_confidence=0.5) as pose:
#   for idx, file in enumerate(file_list):
#     image = cv2.imread(file)
#     image_height, image_width, _ = image.shape
#     # 処理する前にBGR画像をRGBに変換
#     results = pose.process(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))

#     if not results.pose_landmarks:
#       continue
#     print(
#         f'Nose coordinates: ('
#         f'{results.pose_landmarks.landmark[mp_holistic.PoseLandmark.NOSE].x * image_width}, '
#         f'{results.pose_landmarks.landmark[mp_holistic.PoseLandmark.NOSE].y * image_height})'
#     )
#     # 画像にポーズのランドマークを描画
#     annotated_image = image.copy()
#     # upper_body_onlyがTrueの時
#     # 以下の描画にはmp_pose.UPPER_BODY_POSE_CONNECTIONSを使用
#     mp_drawing.draw_landmarks(
#        annotated_image, results.pose_landmarks, mp_pose.POSE_CONNECTIONS)
#     cv2.imwrite('/tmp/annotated_image' + str(idx) + '.png', annotated_image)

# Webカメラ入力の場合：
# cap = cv2.VideoCapture(0)
# with mp_pose.Pose(
#     min_detection_confidence=0.5,
#     min_tracking_confidence=0.5) as pose:
#  while cap.isOpened():
#     success, image = cap.read()
#     if not success:
#       print("Ignoring empty camera frame.")
#       # ビデオをロードする場合は、「continue」ではなく「break」を使用してください
#       continue

#     # 後で自分撮りビューを表示するために画像を水平方向に反転し、BGR画像をRGBに変換
#     image = cv2.cvtColor(cv2.flip(image, 1), cv2.COLOR_BGR2RGB)
#     # パフォーマンスを向上させるには、オプションで、参照渡しのためにイメージを書き込み不可としてマーク
#     image.flags.writeable = False
#     results = pose.process(image) 

#     # 画像にポーズアノテーションを描画
#     image.flags.writeable = True
#     image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
#     mp_drawing.draw_landmarks(
#         image, results.pose_landmarks, mp_pose.POSE_CONNECTIONS)
#     cv2.imshow('MediaPipe Pose', image)
#     if cv2.waitKey(5) & 0xFF == 27:
#       break
# cap.release()
# cv2.destroyAllWindows()