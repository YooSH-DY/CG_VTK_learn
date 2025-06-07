import cv2
import imageio
import numpy as np

# ----------------------------
# 1) GIF 로드 및 프레임 추출
# ----------------------------
gif_path = "/Users/yoosehyeok/Documents/CG_VTK/Iani1.gif"        # 원본 GIF 파일 경로
frames = imageio.mimread(gif_path)       # 프레임 리스트 (RGBA 또는 RGB 배열)
fps = 33                               # 출력 GIF의 FPS (원본에 맞춰 조정)

# ----------------------------
# 2) OpenCV Haar Cascade 로드
# ----------------------------
face_cascade = cv2.CascadeClassifier(
    cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
)

# ----------------------------
# 3) 얼굴 트래킹용 변수 초기화
# ----------------------------
prev_cx, prev_cy = None, None    # 이전 프레임에서의 얼굴 중심
prev_size = None                 # 이전 프레임에서의 crop size
smooth_factor = 0.005             # 새 좌표로 얼마나 빠르게 이동할지 (0~1 사이)
min_size = 450                  # 최소 crop 크기 (픽셀) — 크기가 지나치게 작아지는 걸 방지

cropped_frames = []

# ----------------------------
# 4) 프레임별 얼굴 검출 및 크롭
# ----------------------------
for idx, frame in enumerate(frames):
    # 1) (PIL/Pillow → NumPy) / RGBA → RGB 형식으로 변환
    img = cv2.cvtColor(np.array(frame), cv2.COLOR_RGBA2RGB)
    h, w, _ = img.shape

    # 2) 그레이스케일 변환 → 얼굴 검출
    gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
    faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5)

    # 3) 얼굴 검출 성공 시: 가장 큰 얼굴로 선택
    if len(faces) > 0:
        # faces: 리스트 [(x, y, w, h), ...]
        x, y, fw, fh = max(faces, key=lambda b: b[2] * b[3])
        new_cx = x + fw // 2
        new_cy = y + fh // 2
        new_size = int(max(fw, fh) * 2.0)  # 크롭 영역을 충분히 크게

        # 스무딩: 이전 위치가 있으면 점진적으로 이동
        if prev_cx is not None and prev_cy is not None and prev_size is not None:
            cx = int(prev_cx * (1 - smooth_factor) + new_cx * smooth_factor)
            cy = int(prev_cy * (1 - smooth_factor) + new_cy * smooth_factor)
            size = int(prev_size * (1 - smooth_factor) + new_size * smooth_factor)
        else:
            cx, cy, size = new_cx, new_cy, new_size

        # 최소 크기 이하로 작아지지 않도록
        if size < min_size:
            size = min_size

        # 다음 프레임을 위해 현재 값을 저장
        prev_cx, prev_cy, prev_size = cx, cy, size

    # 4) 얼굴 검출 실패 시: 이전 프레임 위치를 그대로 사용
    else:
        if prev_cx is not None and prev_cy is not None and prev_size is not None:
            cx, cy, size = prev_cx, prev_cy, prev_size
        else:
            # 첫 프레임부터 검출에 실패하면 중앙값 사용
            cx, cy = w // 2, h // 2
            size = min(w, h) // 2  # 기본값(대략 중앙 1/2 영역)
            if size < min_size:
                size = min_size
            prev_cx, prev_cy, prev_size = cx, cy, size

    # 5) 최종 크롭 좌표 계산 (이미지 경계 안에 들도록 클램핑)
    half = size // 2
    x1 = max(cx - half, 0)
    y1 = max(cy - half, 0)
    x2 = min(cx + half, w)
    y2 = min(cy + half, h)

    # (만약 경계를 벗어나면, 부족한 영역을 같은 색(검은색) 배경으로 패딩해도 됩니다)
    cropped = img[y1:y2, x1:x2]

    # 6) 원하는 출력 크기(예: 256×256)로 리사이즈
    cropped_resized = cv2.resize(cropped, (256, 256))
    cropped_frames.append(cropped_resized)

# ----------------------------
# 5) GIF로 재조합하여 저장
# ----------------------------
output_path = "/Users/yoosehyeok/Documents/CG_VTK/cropped_face_follow_fixed.gif"
# imageio.mimsave은 RGB 배열을 기대하므로, BGR → RGB 순서 확인
# (위에서 이미 RGB 형태로 유지했으므로 별도 변환 불필요)
imageio.mimsave(output_path, cropped_frames, fps=fps)

print("✅ 완료: 다음 경로에 저장되었습니다 →", output_path)
