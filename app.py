# ระบบสแกนสลิปโอนเงิน (เวอร์ชั่น 0.2.4) จากสลิป BCEL One
import streamlit as st
import pandas as pd
import pytesseract
from PIL import Image
import re
import os
import io
import numpy as np
import cv2

# ตั้งค่า tesseract สำหรับ Windows
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

st.set_page_config(page_title="ระบบสแกนสลิปโอนเงิน", layout="wide")
st.title("ระบบสแกนสลิปโอนเงิน (เวอร์ชั่น 0.2.4) จากสลิป BCEL One")

# ตัวแปรเก็บประวัติสลิปและข้อมูล OCR
if "history" not in st.session_state:
    st.session_state.history = []

# อัปโหลดภาพ
uploaded_files = st.file_uploader("อัปโหลดสลิปภาพ (รองรับหลายไฟล์)", type=["jpg", "jpeg", "png"], accept_multiple_files=True)
show_ocr = st.checkbox("แสดงข้อความ OCR ทั้งหมด")

# สร้าง DataFrame เปล่า
columns = ["Date", "Time", "Amount (LAK)", "Reference"]
df_result = pd.DataFrame(columns=columns)

# ฟังก์ชันดึงข้อความเฉพาะตัวหนังสือสีแดง (จำนวนเงิน)
def extract_red_amount(img):
    hsv = cv2.cvtColor(img, cv2.COLOR_RGB2HSV)
    lower_red1 = np.array([0, 50, 50])
    upper_red1 = np.array([10, 255, 255])
    lower_red2 = np.array([160, 50, 50])
    upper_red2 = np.array([180, 255, 255])
    mask1 = cv2.inRange(hsv, lower_red1, upper_red1)
    mask2 = cv2.inRange(hsv, lower_red2, upper_red2)
    mask = cv2.bitwise_or(mask1, mask2)
    result = cv2.bitwise_and(img, img, mask=mask)
    gray = cv2.cvtColor(result, cv2.COLOR_RGB2GRAY)
    text = pytesseract.image_to_string(gray)
    amount_match = re.search(r"\d{1,3}(,\d{3})*(\.\d{2})?", text.replace(" ", ""))
    return amount_match.group(0).replace(",", "") if amount_match else ""

# ฟังก์ชันหลักในการดึงข้อมูล
def extract_info(image_file):
    image = Image.open(image_file)
    img_array = np.array(image)
    text = pytesseract.image_to_string(image, lang="eng+lao")

    date = re.search(r"\d{2}/\d{2}/\d{2,4}", text)
    time = re.search(r"\d{2}:\d{2}:\d{2}", text)
    reference = re.search(r"\d{12,}", text)
    amount = extract_red_amount(img_array)

    return {
        "Date": date.group(0) if date else "",
        "Time": time.group(0) if time else "",
        "Amount (LAK)": amount if amount else "",
        "Reference": reference.group(0) if reference else "",
        "OCR": text
    }

# ตรวจสอบซ้ำและแสดงผล
duplicates = []
for file in uploaded_files:
    info = extract_info(file)
    key = (info["Date"], info["Time"], info["Amount (LAK)"], info["Reference"])

    if key in [(
        h["Date"], h["Time"], h["Amount (LAK)"], h["Reference"]
    ) for h in st.session_state.history]:
        info["Duplicate"] = True
        duplicates.append(info)
    else:
        info["Duplicate"] = False
        st.session_state.history.append(info)
        df_result.loc[len(df_result)] = [info[c] for c in columns]

# แสดงผลรวม
if not df_result.empty:
    total = df_result["Amount (LAK)"].replace("", "0").astype(float).sum()
    st.success(f"รวมยอดทั้งหมด: {int(total):,} LAK")

    def highlight_duplicates(row):
        return ["background-color: red" if row.get("Duplicate", False) else ""] * len(row)

    styled_df = df_result.style.apply(highlight_duplicates, axis=1)
    st.dataframe(styled_df, use_container_width=True)

    # ดาวน์โหลด Excel
    buffer = io.BytesIO()
    df_result.to_excel(buffer, index=False)
    st.download_button("ดาวน์โหลดไฟล์ Excel", data=buffer.getvalue(), file_name="result.xlsx")

# แสดงข้อความ OCR
if show_ocr:
    st.subheader("ข้อความ OCR ทั้งหมด")
    for record in st.session_state.history:
        st.text(record["OCR"])
        st.markdown("---")
