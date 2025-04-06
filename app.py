# ระบบสแกนสลิปโอนเงิน (เวอร์ชั่น 0.2.3) จากสลิป BCEL One
import streamlit as st
import pandas as pd
import pytesseract
from PIL import Image
import re
import io
import os
import numpy as np

# ตั้งค่า pytesseract สำหรับ Windows (แก้ตาม path เครื่องคุณ)
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# ตั้งค่าหน้า Streamlit
st.set_page_config(page_title="ระบบสแกนสลิปโอนเงิน", layout="wide")
st.title("ระบบสแกนสลิปโอนเงิน (เวอร์ชั่น 0.2.3) จากสลิป BCEL One")

# ตัวอัปโหลดภาพ
uploaded_files = st.file_uploader("อัปโหลดสลิป (รองรับหลายไฟล์)", type=["jpg", "jpeg", "png"], accept_multiple_files=True)
show_ocr = st.checkbox("แสดงข้อความ OCR ทั้งหมด")

# ตารางผลลัพธ์
df_history = pd.DataFrame(columns=["Date", "Time", "Amount (LAK)", "Reference"])

def extract_info(image):
    text = pytesseract.image_to_string(image, lang='eng+lao')
    
    date_match = re.search(r'(\d{2}/\d{2}/\d{2})', text)
    time_match = re.search(r'(\d{2}:\d{2}:\d{2})', text)
    amount_match = re.search(r'([0-9,]+)\s+LAK', text)
    reference_match = re.search(r'\b\d{14}\b', text)

    date = date_match.group(1) if date_match else ""
    time = time_match.group(1) if time_match else ""
    amount_str = amount_match.group(1).replace(",", "") if amount_match else "0"
    amount = int(amount_str)
    reference = reference_match.group(0) if reference_match else ""

    return {
        "Date": date,
        "Time": time,
        "Amount (LAK)": amount,
        "Reference": reference,
        "OCR Text": text
    }

if uploaded_files:
    for uploaded_file in uploaded_files:
        image = Image.open(uploaded_file)
        info = extract_info(image)

        is_duplicate = (
            ((df_history["Date"] == info["Date"]) &
             (df_history["Time"] == info["Time"]) &
             (df_history["Amount (LAK)"] == info["Amount (LAK)"]) &
             (df_history["Reference"] == info["Reference"])).any()
        )

        row_color = "background-color: #ffcccc;" if is_duplicate else ""
        new_row = pd.DataFrame([info])[["Date", "Time", "Amount (LAK)", "Reference"]]
        df_history = pd.concat([df_history, new_row], ignore_index=True)

        if show_ocr:
            st.subheader(f"OCR จากไฟล์: {uploaded_file.name}")
            st.code(info["OCR Text"])

    st.success(f"รวมยอดทั้งหมด: {df_history['Amount (LAK)'].sum():,} LAK")
    st.dataframe(df_history)

    buffer = io.BytesIO()
    df_history.to_excel(buffer, index=False)
    st.download_button("ดาวน์โหลดไฟล์ Excel", buffer.getvalue(), file_name="summary.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
