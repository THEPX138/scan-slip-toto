# ระบบสแกนสลิป BCEL One (เวอร์ชัน 0.2.6)
import streamlit as st
import pandas as pd
import pytesseract
from PIL import Image
import re
import os
import io
import numpy as np
import cv2
from pyzbar.pyzbar import decode

# ตั้งค่า tesseract สำหรับ Windows
pytesseract.pytesseract.tesseract_cmd = r"C:\\Program Files\\Tesseract-OCR\\tesseract.exe"

st.set_page_config(page_title="ระบบสแกนสลิปโอนเงิน", layout="wide")
st.title("ระบบสแกนสลิปโอนเงิน (เวอร์ชัน 0.2.6) จากสลิป BCEL One")

uploaded_files = st.file_uploader("อัปโหลดสลิปภาพ (รองรับหลายไฟล์)", type=["jpg", "jpeg", "png"], accept_multiple_files=True)
show_ocr = st.checkbox("แสดงข้อความ OCR ทั้งหมด")

columns = ["Date", "Time", "Amount (LAK)", "Reference", "QR Data"]
df_history = pd.DataFrame(columns=columns)

uploaded_hashes = set()

# ดึงเฉพาะส่วนตัวอักษรสีแดงเพื่ออ่านจำนวนเงิน
def extract_amount_region(image):
    img_np = np.array(image)
    hsv = cv2.cvtColor(img_np, cv2.COLOR_RGB2HSV)
    lower_red = np.array([0, 100, 100])
    upper_red = np.array([10, 255, 255])
    mask = cv2.inRange(hsv, lower_red, upper_red)
    result = cv2.bitwise_and(img_np, img_np, mask=mask)
    gray = cv2.cvtColor(result, cv2.COLOR_RGB2GRAY)
    _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return Image.fromarray(thresh)

# อ่าน QR code
def read_qr_code(image):
    decoded_objects = decode(image)
    for obj in decoded_objects:
        return obj.data.decode('utf-8')
    return ""

for file in uploaded_files:
    image = Image.open(file)
    text = pytesseract.image_to_string(image, lang='eng+lao')

    # อ่านจากตำแหน่งตัวอักษรสีแดงเพื่อหา Amount
    red_area = extract_amount_region(image)
    red_text = pytesseract.image_to_string(red_area, config='--psm 6 digits')

    # ดึงข้อมูลจาก OCR
    date = re.search(r"\d{2}/\d{2}/\d{2,4}", text)
    time = re.search(r"\d{2}:\d{2}:\d{2}", text)
    reference = re.search(r"\d{15,20}", text)

    amount_match = re.search(r"\d{1,3}[,\d]{0,10}", red_text)
    amount = amount_match.group().replace(",", "") if amount_match else ""

    qr_data = read_qr_code(np.array(image))

    slip_key = f"{date.group() if date else ''}-{time.group() if time else ''}-{amount}-{reference.group() if reference else ''}-{qr_data}"
    if slip_key in uploaded_hashes:
        st.warning(f"สลิปซ้ำ: {reference.group() if reference else 'N/A'}")
        continue
    uploaded_hashes.add(slip_key)

    row = {
        "Date": date.group() if date else "",
        "Time": time.group() if time else "",
        "Amount (LAK)": amount,
        "Reference": reference.group() if reference else "",
        "QR Data": qr_data
    }
    df_history.loc[len(df_history)] = row

    if show_ocr:
        st.subheader(f"สลิปที่: {reference.group() if reference else 'N/A'}")
        st.code(text)

if not df_history.empty:
    total = df_history["Amount (LAK)"].astype(str).str.replace(",", "").astype(float).sum()
    st.success(f"รวมยอดทั้งหมด: {int(total):,} LAK")
    st.dataframe(df_history)

    buffer = io.BytesIO()
    df_history.to_excel(buffer, index=False)
    st.download_button("ดาวน์โหลดไฟล์ Excel", data=buffer.getvalue(), file_name="slip_summary.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
