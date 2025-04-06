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

# ตั้งค่า tesseract สำหรับ Windows (ถ้าใช้ Linux หรือ Mac ให้คอมเมนต์บรรทัดนี้ออก)
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# ตั้งค่าหน้าแอป
st.set_page_config(page_title="ระบบสแกนสลิปโอนเงิน", layout="wide")
st.title("ระบบสแกนสลิปโอนเงิน (เวอร์ชั่น 0.2.4) จากสลิป BCEL One")

# อัปโหลดสลิป
uploaded_files = st.file_uploader("อัปโหลดสลิปภาพ (รองรับหลายไฟล์)", type=["jpg", "jpeg", "png"], accept_multiple_files=True)
show_ocr = st.checkbox("แสดงข้อความ OCR ทั้งหมด")

# เตรียม DataFrame สำหรับสรุปผล
df_history = pd.DataFrame(columns=["Date", "Time", "Amount (LAK)", "Reference"])

def extract_info(image):
    # อ่านข้อความจากภาพ
    text = pytesseract.image_to_string(image, lang='eng+lao')
    
    if show_ocr:
        st.code(text)

    # ดึงข้อมูลด้วย regex
    date = re.search(r"\d{2}/\d{2}/\d{2,4}", text)
    time = re.search(r"\d{2}:\d{2}:\d{2}", text)
    amount = re.search(r"69,000|[1-9]\d{0,2}(?:,\d{3})*", text)
    reference = re.search(r"\d{14}", text)

    return {
        "Date": date.group() if date else "",
        "Time": time.group() if time else "",
        "Amount (LAK)": amount.group().replace(",", "") if amount else "",
        "Reference": reference.group() if reference else ""
    }

# ประมวลผลแต่ละไฟล์
for file in uploaded_files:
    image = Image.open(file)
    info = extract_info(image)

    # ตรวจสอบสลิปซ้ำจาก Reference
    if not df_history[
        (df_history["Date"] == info["Date"]) &
        (df_history["Time"] == info["Time"]) &
        (df_history["Amount (LAK)"] == info["Amount (LAK)"]) &
        (df_history["Reference"] == info["Reference"])
    ].empty:
        st.warning(f"สลิปซ้ำ: {info['Reference']}")
        continue

    df_history.loc[len(df_history)] = info

# แสดงผลรวม
if not df_history.empty:
    total = df_history["Amount (LAK)"].astype(str).str.replace(",", "").astype(float).sum()
    st.success(f"รวมยอดทั้งหมด: {int(total):,} LAK")
    st.dataframe(df_history)

    # ดาวน์โหลด Excel
    buffer = io.BytesIO()
    df_history.to_excel(buffer, index=False, engine='openpyxl')
    st.download_button("ดาวน์โหลดไฟล์ Excel", buffer.getvalue(), file_name="summary.xlsx")
