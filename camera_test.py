import cv2

# 카메라 초기화
camera = cv2.VideoCapture(0)
camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

if not camera.isOpened():
    print("카메라를 열 수 없습니다.")
    exit()

# 메인 루프
try:
    while True:
        ret, frame = camera.read()
        if not ret:
            print("프레임을 읽을 수 없습니다.")
            break

        # 640x640 크기로 리사이즈
        frame_resized = cv2.resize(frame, (640, 480))

        # 화면에 출력
        cv2.imshow("Camera Feed", frame_resized)

        # ESC 키를 누르면 종료
        if cv2.waitKey(1) & 0xFF == 27:
            print("프로그램을 종료합니다.")
            break

finally:
    # 카메라 및 창 리소스 해제
    camera.release()
    cv2.destroyAllWindows()
