import Jetson.GPIO as GPIO
import cv2
import os
import time
from pynput import keyboard
from threading import Thread

# GPIO 핀 설정
SERVO_PIN = 32  # 서보모터 핀 번호 (BOARD Pin 32)
IN1 = 31        # DC 모터 IN1 핀 번호 (BOARD Pin 31)
IN2 = 29        # DC 모터 IN2 핀 번호 (BOARD Pin 29)
ENA = 33        # DC 모터 ENA 핀 번호 (BOARD Pin 33, PWM 핀)

# GPIO 모드 설정
GPIO.setmode(GPIO.BOARD)
GPIO.setup(SERVO_PIN, GPIO.OUT)
GPIO.setup(IN1, GPIO.OUT)
GPIO.setup(IN2, GPIO.OUT)
GPIO.setup(ENA, GPIO.OUT)

# PWM 설정
servo_pwm = GPIO.PWM(SERVO_PIN, 50)  # 서보모터: 50Hz
dc_motor_pwm = GPIO.PWM(ENA, 100)    # DC 모터: 100Hz

# PWM 시작
servo_pwm.start(0)
dc_motor_pwm.start(0)

# 초기값 설정
current_angle = 90
current_speed = 0

# 데이터셋 폴더 설정
BASE_DIR = "dataset"
os.makedirs(BASE_DIR, exist_ok=True)

# 각도 범위에 따른 폴더 설정
ANGLE_BUCKETS = {
    "50_69": (50, 69),
    "70_89": (70, 89),
    "90": (90, 90),
    "91_110": (91, 110),
    "111_130": (111, 130)
}
for folder_name in ANGLE_BUCKETS.keys():
    os.makedirs(os.path.join(BASE_DIR, folder_name), exist_ok=True)

# 서보모터 각도 설정 함수
def set_servo_angle(angle):
    # 각도를 듀티 사이클로 변환 (0도 = 2%, 180도 = 12%)
    duty = 2 + (angle / 18)
    servo_pwm.ChangeDutyCycle(duty)
    time.sleep(0.1)
    servo_pwm.ChangeDutyCycle(0)  # 과열 방지

# DC 모터 전진 함수 (속도 증가)
def motor_forward():
    global current_speed
    if current_speed < 100:
        current_speed += 5
    GPIO.output(IN1, GPIO.LOW)
    GPIO.output(IN2, GPIO.HIGH)
    dc_motor_pwm.ChangeDutyCycle(current_speed)
    print(f"전진: 속도 {current_speed}%")

# DC 모터 속도 감소 함수
def motor_slow_down():
    global current_speed
    if current_speed > 0:
        current_speed -= 5
    GPIO.output(IN1, GPIO.LOW)
    GPIO.output(IN2, GPIO.HIGH)
    dc_motor_pwm.ChangeDutyCycle(current_speed)
    print(f"속도 감소: 속도 {current_speed}%")

# 모터 정지 함수
def motor_stop():
    global current_speed
    current_speed = 0
    GPIO.output(IN1, GPIO.LOW)
    GPIO.output(IN2, GPIO.LOW)
    dc_motor_pwm.ChangeDutyCycle(0)
    print("모터 정지")

# 카메라 초기화
camera = cv2.VideoCapture(0)
camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

if not camera.isOpened():
    print("카메라를 열 수 없습니다.")
    GPIO.cleanup()
    exit()

# 이미지 저장 함수
def save_frame():
    while True:
        ret, frame = camera.read()
        if ret:
            for folder_name, (start, end) in ANGLE_BUCKETS.items():
                if start <= current_angle <= end:
                    folder = os.path.join(BASE_DIR, folder_name)
                    filename = f"{time.time():.6f}.jpg"
                    filepath = os.path.join(folder, filename)
                    cv2.imwrite(filepath, frame)
                    print(f"이미지 저장: {filepath}")
                    break
        time.sleep(0.1)  # 1초에 10장 저장

# 초기 서보모터 각도 설정 (90도)
set_servo_angle(current_angle)

# 각도 변화량 설정
ANGLE_INCREMENT = 20

# 키 입력 처리 함수
def on_press(key):
    global current_angle
    try:
        if key == keyboard.Key.up:  # 위쪽 방향키: DC 모터 전진 (속도 증가)
            motor_forward()
        elif key == keyboard.Key.down:  # 아래쪽 방향키: DC 모터 속도 감소
            motor_slow_down()
        elif key == keyboard.Key.left:  # 왼쪽 방향키: 서보모터 왼쪽 회전
            current_angle = max(40, current_angle - ANGLE_INCREMENT)
            set_servo_angle(current_angle)
            print(f"서보모터 왼쪽 회전: 각도 {current_angle}도")
        elif key == keyboard.Key.right:  # 오른쪽 방향키: 서보모터 오른쪽 회전
            current_angle = min(140, current_angle + ANGLE_INCREMENT)
            set_servo_angle(current_angle)
            print(f"서보모터 오른쪽 회전: 각도 {current_angle}도")
        elif key == keyboard.Key.space:  # Space 키: 모터 정지
            motor_stop()
    except AttributeError:
        pass

def on_release(key):
    if key == keyboard.Key.esc:
        # ESC 키를 누르면 프로그램 종료
        print("프로그램을 종료합니다.")
        return False

# 키보드 리스너 시작
print("키 입력을 기다리는 중입니다...")
listener = keyboard.Listener(on_press=on_press, on_release=on_release)
listener.start()

# 이미지 저장 쓰레드 시작
image_saving_thread = Thread(target=save_frame)
image_saving_thread.daemon = True
image_saving_thread.start()

# 메인 루프
try:
    listener.join()  # 키보드 리스너가 종료될 때까지 대기
except KeyboardInterrupt:
    pass
finally:
    # 프로그램 종료 시 GPIO 핀 초기화 및 카메라 해제
    servo_pwm.stop()
    dc_motor_pwm.stop()
    GPIO.cleanup()
    camera.release()
    cv2.destroyAllWindows()
    print("프로그램을 종료합니다.")
