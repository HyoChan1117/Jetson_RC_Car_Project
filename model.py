import os
import torch
import torchvision.transforms as transforms
import Jetson.GPIO as GPIO
import cv2
import time
import numpy as np
from PIL import Image  # Import PIL

# Suppress warnings
GPIO.setwarnings(False)

# GPIO 핀 설정
SERVO_PIN = 32  # 서보모터 핀 번호
IN1 = 31        # DC 모터 IN1 핀 번호
IN2 = 29        # DC 모터 IN2 핀 번호
ENA = 33        # DC 모터 ENA 핀 번호 (PWM 핀)

GPIO.setmode(GPIO.BOARD)
GPIO.setup(SERVO_PIN, GPIO.OUT)
GPIO.setup(IN1, GPIO.OUT)
GPIO.setup(IN2, GPIO.OUT)
GPIO.setup(ENA, GPIO.OUT)

# PWM 설정
servo_pwm = GPIO.PWM(SERVO_PIN, 50)
dc_motor_pwm = GPIO.PWM(ENA, 100)
servo_pwm.start(0)
dc_motor_pwm.start(0)

# 서보모터 각도 조정 함수
def set_servo_angle(angle):
    duty = (angle / 18) + 2
    servo_pwm.ChangeDutyCycle(duty)
    time.sleep(0.1)
    servo_pwm.ChangeDutyCycle(0)

# DC 모터 전진 함수
def motor_forward(speed=50):
    GPIO.output(IN1, GPIO.LOW)
    GPIO.output(IN2, GPIO.HIGH)
    dc_motor_pwm.ChangeDutyCycle(speed)

# DC 모터 정지 함수
def motor_stop():
    GPIO.output(IN1, GPIO.LOW)
    GPIO.output(IN2, GPIO.LOW)
    dc_motor_pwm.ChangeDutyCycle(0)

# CNN 모델 정의
class CNNModel(torch.nn.Module):
    def __init__(self, num_classes):
        super(CNNModel, self).__init__()
        self.conv1 = torch.nn.Conv2d(3, 16, kernel_size=3, stride=1, padding=1)
        self.conv2 = torch.nn.Conv2d(16, 32, kernel_size=3, stride=1, padding=1)
        self.conv3 = torch.nn.Conv2d(32, 64, kernel_size=3, stride=1, padding=1)
        self.pool = torch.nn.MaxPool2d(kernel_size=2, stride=2)
        self.fc1 = torch.nn.Linear(64 * 8 * 8, 128)
        self.fc2 = torch.nn.Linear(128, num_classes)

    def forward(self, x):
        x = self.pool(torch.relu(self.conv1(x)))
        x = self.pool(torch.relu(self.conv2(x)))
        x = self.pool(torch.relu(self.conv3(x)))
        x = x.view(-1, 64 * 8 * 8)
        x = torch.relu(self.fc1(x))
        x = self.fc2(x)
        return x

# 모델 로드
model = CNNModel(num_classes=5)  # Correct number of output classes
try:
    model.load_state_dict(torch.load("my_model.pth", map_location=torch.device("cpu")))
    model.eval()
except FileNotFoundError:
    print("Model file not found! Please provide a valid model file.")
    GPIO.cleanup()
    exit()

# 데이터 전처리
transform = transforms.Compose([
    transforms.Resize((64, 64)),
    transforms.ToTensor(),
    transforms.Normalize([0.5, 0.5, 0.5], [0.5, 0.5, 0.5])
])

# 클래스에 따른 각도 매핑
angle_map = {
    0: 50,   # "50_69" 클래스
    1: 60,   # "70_89" 클래스
    2: 90,   # "90" 클래스
    3: 120,   # "91_110" 클래스
    4: 130,   # "111_130" class
}

# Jetson 설정 명령 실행
os.system("sudo busybox devmem 0x700031fc 32 0x45")
os.system("sudo busybox devmem 0x6000d504 32 0x2")

# 카메라 설정
camera = cv2.VideoCapture(0)
camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

if not camera.isOpened():
    print("Unable to access the camera.")
    GPIO.cleanup()
    exit()

try:
    while True:
        ret, frame = camera.read()
        if not ret:
            print("Failed to capture frame.")
            break

        # 이미지 전처리
        img = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        img = Image.fromarray(img)  # Convert to PIL image
        img_tensor = transform(img).unsqueeze(0)

        # 모델 예측
        with torch.no_grad():
            outputs = model(img_tensor)
            _, predicted = torch.max(outputs, 1)
            label = predicted.item()

        # 각도 매핑 및 서보모터 제어
        angle = angle_map[label]
        set_servo_angle(angle)

        # 직진 속도 유지
        motor_forward(speed=20)

        # 결과 출력
        cv2.putText(frame, f"Angle: {angle}, Predicted: {label}", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        cv2.imshow("Driving Test", frame)

        # ESC 키로 종료
        if cv2.waitKey(1) & 0xFF == 27:
            break

except KeyboardInterrupt:
    print("Test interrupted.")

finally:
    # 자원 해제
    camera.release()
    cv2.destroyAllWindows()
    servo_pwm.stop()
    dc_motor_pwm.stop()
    GPIO.cleanup()  # Ensure GPIO cleanup

