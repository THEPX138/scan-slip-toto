import streamlit as st
import pandas as pd
import pytesseract
from PIL import Image
import re
import io
import os

# กำหนด path Tesseract ให้เหมาะกับแต่ละระบบปฏิบัติการ
if os.name == 'nt':  # Windows
    pytesseract.pytesseract.tesseract_cmd = r'C:\\Program Files\\Tesseract-OCR\\tesseract.exe'
else:  # Linux / Streamlit Cloud
    pytesseract.pytesseract.tesseract_cmd = 'tesseract'

# ส่วน UI
st.set_page_config(page_title="ระบบสแกนสลิป & สรุปยอด", layout="wide")
st.title("ระบบสแกนสลิปโอนเงิน")

uploaded_files = st.file_uploader(
    "อัปโหลดสลิปภาพ (รองรับหลายไฟล์)",
    type=["png", "jpg", "jpeg"],
    accept_multiple_files=True
)

# ฟังก์ชันแยกข้อมูลจากข้อความ OCR
def extract_transaction_data(text):
    date_pattern = r'\d{2}/\d{2}/\d{2}'
    time_pattern = r'\d{2}:\d{2}:\d{2}'
    amount_pattern = r'[\d,]+\.\d{2}|[\d,]+ LAK'
    ref_pattern = r'\d{14}'

    date = re.search(date_pattern, text)
    time = re.search(time_pattern, text)
    amount = re.search(amount_pattern, text)
    reference = re.search(ref_pattern, text)

    return {
        'Date': date.group() if date else '',
        'Time': time.group() if time else '',
        'Amount (LAK)': amount.group().replace(',', '').replace('LAK', '').strip() if amount else '',
        'Reference': reference.group() if reference else '',
    }

# เมื่อลูกค้าอัปโหลดไฟล์
if uploaded_files:
    results = []
    for file in uploaded_files:
        image = Image.open(file)
        text = pytesseract.image_to_string(image, config='--oem 3 --psm 6')
        data = extract_transaction_data(text)
        results.append(data)

    df = pd.DataFrame(results)
    df['Amount (LAK)'] = pd.to_numeric(df['Amount (LAK)'], errors='coerce')
    df = df.dropna(subset=['Amount (LAK)'])
    df.sort_values(by=['Date', 'Time'], inplace=True)
    df.reset_index(drop=True, inplace=True)

    st.success(f"รวมยอดทั้งหมด: {df['Amount (LAK)'].sum():,.0f} LAK")
    st.dataframe(df)

    buffer = io.BytesIO()
    df.to_excel(buffer, index=False)  # <<< วงเล็บครบแล้ว!
    buffer.seek(0)
