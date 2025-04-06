เวอร์ชั่น: 0.1

ระบบตัดตัวหนังสือสีแดง (ยอดเงินจริง) จากสลิป BCEL One

import cv2 import pytesseract from PIL import Image import numpy as np import re import streamlit as st import io

ตั้ง path ของ tesseract หากใช้ Windows

pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

def extract_red_amount(image): # แปลงภาพเป็น numpy array หากเป็น PIL if isinstance(image, Image.Image): image = np.array(image)

# ครอปเฉพาะบริเวณตัวหนังสือสีแดง (คาดว่าเป็นยอดเงินโอน)
h, w = image.shape[:2]
crop_img = image[int(h*0.55):int(h*0.7), int(w*0.25):int(w*0.85)]

# แปลงเป็นเทา แล้วปรับ contrast
gray = cv2.cvtColor(crop_img, cv2.COLOR_BGR2GRAY)
_, thresh = cv2.threshold(gray, 160, 255, cv2.THRESH_BINARY_INV)

# ใช้ OCR เฉพาะบริเวณที่ตัดมา
text = pytesseract.image_to_string(thresh, lang='eng+lao')

# ใช้ regex ดึงจำนวนเงิน เช่น 69,000 LAK
matches = re.findall(r'\d{1,3}(,\d{3})?\s?LAK', text)
amount = matches[0] if matches else "ไม่พบจำนวนเงิน"
return amount, text, crop_img

ส่วน Streamlit

st.set_page_config(page_title="ระบบแยกยอดเงินจากตัวหนังสือสีแดง", layout="centered") st.title("ระบบแยกยอดเงินตัวหนังสือสีแดงจากสลิปโอน BCEL")

uploaded_file = st.file_uploader("อัปโหลดภาพสลิป (PNG, JPG)", type=["png", "jpg", "jpeg"])

if uploaded_file: image = Image.open(uploaded_file) st.image(image, caption='ภาพต้นฉบับ', use_column_width=True)

with st.spinner("กำลังประมวลผล OCR..."):
    amount, ocr_text, cropped_image = extract_red_amount(image)

st.success(f"ยอดเงินที่ตรวจพบ: {amount}")
st.image(cropped_image, caption='บริเวณตัวหนังสือสีแดงที่ครอปมา', use_column_width=True)

if st.checkbox("แสดงข้อความ OCR เต็ม"):
    st.code(ocr_text)
