
# ระบบสแกนสลิปโอนเงิน (เวอร์ชั่น 0.3.3) จากสลิป BCEL One
import streamlit as st
import pandas as pd
import pytesseract
from PIL import Image
import re
import os
import io
import numpy as np
import cv2

# ตั้งค่า Streamlit
st.set_page_config(page_title="One", layout="wide")
st.title("ระบบสแกนสลิปโอนเงิน (เวอร์ชั่น 0.3.3) จากสลิป BCEL One")

uploaded_files = st.file_uploader("อัปโหลดสลิปภาพ (รองรับหลายไฟล์)", type=["jpg", "jpeg", "png"], accept_multiple_files=True)
show_ocr = st.checkbox("แสดงข้อความ OCR ทั้งหมด")

columns = ["Date", "Time", "Amount (LAK)", "Reference", "Sender", "Receiver"]
df_history = pd.DataFrame(columns=columns)
uploaded_hashes = set()

def extract_amount_region(image):
    img_np = np.array(image)
    hsv = cv2.cvtColor(img_np, cv2.COLOR_RGB2HSV)
    lower_red = np.array([0, 100, 100])
    upper_red = np.array([10, 255, 255])
    mask1 = cv2.inRange(hsv, lower_red, upper_red)
    lower_red2 = np.array([160, 100, 100])
    upper_red2 = np.array([180, 255, 255])
    mask2 = cv2.inRange(hsv, lower_red2, upper_red2)
    mask = cv2.bitwise_or(mask1, mask2)
    result = cv2.bitwise_and(img_np, img_np, mask=mask)
    gray = cv2.cvtColor(result, cv2.COLOR_RGB2GRAY)
    _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return Image.fromarray(thresh)

for file in uploaded_files:
    image = Image.open(file)
    text = pytesseract.image_to_string(image)

    red_area = extract_amount_region(image)
    red_text = pytesseract.image_to_string(red_area, config='--psm 6 digits')

    date = re.search(r"\d{2}/\d{2}/\d{2,4}", text)
    time = re.search(r"\d{2}:\d{2}:\d{2}", text)
    reference = re.search(r"\d{15,20}", text)

    sender = re.search(r"From account[ \n]*([A-Z \-]+ (MR|MS))", text)
    receiver = re.search(r"To account[ \n]*([A-Z \-]+ (MR|MS))", text)

    amount_match = re.search(r"\d{1,3}(,\d{3})*", red_text)
    amount = amount_match.group().replace(",", "") if amount_match else ""

    slip_key = f"{date.group() if date else ''}-{time.group() if time else ''}-{amount}-{reference.group() if reference else ''}"
    if slip_key in uploaded_hashes:
        st.warning(f"สลิปซ้ำ: {reference.group() if reference else 'N/A'}")
        continue
    uploaded_hashes.add(slip_key)

    row = {
        "Date": date.group() if date else "",
        "Time": time.group() if time else "",
        "Amount (LAK)": amount,
        "Reference": reference.group() if reference else "",
        "Sender": sender.group(1).strip() if sender else "",
        "Receiver": receiver.group(1).strip() if receiver else ""
    }
    df_history.loc[len(df_history)] = row

    if show_ocr:
        st.subheader(f"สลิปที่: {reference.group() if reference else 'N/A'}")
        st.code(text)

if not df_history.empty:
    try:
        df_amount = pd.to_numeric(df_history["Amount (LAK)"].astype(str).str.replace(",", ""), errors="coerce")
        total = df_amount.sum()
        st.success(f"รวมยอดทั้งหมด: {int(total):,} LAK")
        st.dataframe(df_history)

        buffer = io.BytesIO()
        df_history.to_excel(buffer, index=False)
        st.download_button("ดาวน์โหลดไฟล์ Excel", data=buffer.getvalue(), file_name="slip_summary.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    except:
        st.warning("ไม่สามารถรวมยอดได้ เนื่องจากข้อมูลจำนวนเงินไม่ถูกต้องทั้งหมด")
