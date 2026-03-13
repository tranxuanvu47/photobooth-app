import cv2
import time

print("Testing OpenCV MSMF backend...")
start = time.time()
cap = cv2.VideoCapture(0, cv2.CAP_MSMF)
print(f"MSMF time: {time.time() - start:.2f}s, opened: {cap.isOpened()}")
if cap.isOpened(): cap.release()

print("Testing OpenCV DSHOW backend...")
start = time.time()
cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
print(f"DSHOW time: {time.time() - start:.2f}s, opened: {cap.isOpened()}")
if cap.isOpened(): cap.release()

print("Done")
