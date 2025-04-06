
import streamlit as st
import pandas as pd
import pytesseract
from PIL import Image
import re
import os
import io
import numpy as np
import cv2

# ตั้งค่า pytesseract บน Windows
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# UI
st.set_page_config(page_title="ระบบแสกนสลิปโอนเงิน", layout="wide")
st.title("ระบบแสกนสลิปโอนเงิน (เวอร์ชั่น 0.2.3) จากสลิป BCEL One")

uploaded_files = st.file_uploader("อัปโหลดสลิปภาพ (รองรับหลายไฟล์)", type=["jpg", "jpeg", "png"], accept_multiple_files=True)
show_ocr = st.checkbox("แสดงข้อความ OCR ทั้งหมด")

df_history = pd.DataFrame(columns=["Date", "Time", "Amount (LAK)", "Reference"])

def extract_info(image):
    text = pytesseract.image_to_string(image, lang='eng+lao')
    if show_ocr:
        st.code(text)

    date = re.search(r"(\d{2}/\d{2}/\d{2})", text)
    time = re.search(r"(\d{2}:\d{2}:\d{2})", text)
    amount = re.search(r"(69,000|\d{1,3}(,\d{3})*\s?LAK)", text)
    ticket = re.search(r"(\d{14,}|GPAX\w+)", text)

    return {
        "Date": date.group(1) if date else "",
        "Time": time.group(1) if time else "",
        "Amount (LAK)": amount.group(1).replace(" LAK", "").replace(",", "") if amount else "",
        "Reference": ticket.group(1) if ticket else ""
    }

# ประมวลผล
if uploaded_files:
    for file in uploaded_files:
        image = Image.open(file)
        info = extract_info(image)
        df_history.loc[len(df_history)] = info

    total = df_history["Amount (LAK)"].astype(str).str.replace(",", "").str.extract(r"(\d+)")[0].astype(float).sum()
    st.success(f"รวมยอดทั้งหมด: {int(total):,} LAK")
    st.dataframe(df_history)

    buffer = io.BytesIO()
    df_history.to_excel(buffer, index=False)
    st.download_button("ดาวน์โหลดไฟล์ Excel", buffer.getvalue(), file_name="summary.xlsx")
