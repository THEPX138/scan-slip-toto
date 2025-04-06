# ระบบสแกนสลิปโอนเงิน (เวอร์ชัน 0.2.2) จากสลิป BCEL One
import streamlit as st
import pandas as pd
import pytesseract
from PIL import Image
import re
import io
import os
import numpy as np
import cv2

# ตั้งค่า pytesseract หากใช้บน Windows
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

st.set_page_config(page_title="ระบบสแกนสลิปโอนเงิน", layout="wide")
st.title("ระบบสแกนสลิปโอนเงิน (เวอร์ชัน 0.2.2) จากสลิป BCEL One")

uploaded_files = st.file_uploader("อัปโหลดสลิปภาพ (รองรับหลายไฟล์)", type=["jpg", "jpeg", "png"], accept_multiple_files=True)
show_ocr = st.checkbox("แสดงข้อความ OCR ทั้งหมด")

# เก็บประวัติสลิป
df_history = pd.DataFrame(columns=["Date", "Time", "Amount (LAK)", "Reference"])

def extract_info(image):
    text = pytesseract.image_to_string(image, lang='eng+lao')

    date_match = re.search(r"(\d{2}/\d{2}/\d{2})", text)
    time_match = re.search(r"(\d{2}:\d{2}:\d{2})", text)
    amount_match = re.search(r"([\d,]+)\s?LAK", text)
    ref_match = re.search(r"(20\d{10,})", text)

    date = date_match.group(1) if date_match else ""
    time = time_match.group(1) if time_match else ""
    amount = amount_match.group(1).replace(",", "") if amount_match else "0"
    reference = ref_match.group(1) if ref_match else ""

    return {"Date": date, "Time": time, "Amount (LAK)": int(amount), "Reference": reference}, text

if uploaded_files:
    results = []
    texts = []
    for uploaded_file in uploaded_files:
        image = Image.open(uploaded_file)
        info, raw_text = extract_info(image)
        results.append(info)
        texts.append(raw_text)

    df = pd.DataFrame(results)

    # ตรวจจับสลิปซ้ำ
    merged = df.merge(df_history, on=["Date", "Time", "Amount (LAK)", "Reference"], how='left', indicator=True)
    df["ซ้ำ"] = merged["_merge"] == "both"

    df_history = pd.concat([df_history, df]).drop_duplicates(subset=["Date", "Time", "Amount (LAK)", "Reference"])

    total = df[~df["ซ้ำ"]]["Amount (LAK)"].sum()
    st.success(f"รวมยอดทั้งหมด: {total:,} LAK")

    def highlight_duplicate(val):
        return 'background-color: red; color: white' if val else ''

    st.dataframe(df.drop(columns=["ซ้ำ"]).style.applymap(highlight_duplicate, subset=["ซ้ำ"]))

    if show_ocr:
        for i, t in enumerate(texts):
            st.text_area(f"OCR Text {i+1}", t, height=200)

    buffer = io.BytesIO()
    df.to_excel(buffer, index=False)
    st.download_button("ดาวน์โหลดไฟล์ Excel", buffer.getvalue(), file_name="slip_result_v0.2.2.xlsx")
