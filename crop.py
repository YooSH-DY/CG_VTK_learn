import cv2
import imageio
import mediapipe as mp
from PIL import Image

# 파일 불러오기
gif_path = "/mnt/data/이아니1.gif"
frames = imageio.mimread(gif_path)
fps = 10  # 수정 가능

# MediaPipe Face Detection 초기화
mp_face = mp.solutions.face_detection
face_detection = mp_face.FaceDetection(model_selection=0, min_detection_confidence=0.5)

cropped_frames = []

for frame in frames:
    img = cv2.cvtColor(frame, cv2.COLOR_RGBA2RGB)
    results = face_detection.process(img)

    if results.detections:
        # 얼굴 위치 탐지
        bbox = results.detections[0].location_data.relative_bounding_box
        h, w, _ = img.shape
        cx = int((bbox.xmin + bbox.width / 2) * w)
        cy = int((bbox.ymin + bbox.height / 2) * h)
        size = int(max(bbox.width * w, bbox.height * h) * 1.5)

        # 크롭 영역 계산
        x1 = max(cx - size // 2, 0)
        y1 = max(cy - size // 2, 0)
        x2 = min(cx + size // 2, w)
        y2 = min(cy + size // 2, h)

        cropped = img[y1:y2, x1:x2]
        cropped = cv2.resize(cropped, (256, 256))  # 원하는 크기로
        cropped_frames.append(cropped)
    else:
        # 얼굴 인식 실패 시 원본 저장
        cropped_frames.append(cv2.resize(img, (256, 256)))

# 저장
output_path = "/mnt/data/cropped_face_follow.gif"
imageio.mimsave(output_path, cropped_frames, fps=fps)
