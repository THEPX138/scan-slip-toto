import streamlit as st
import pandas as pd
import pytesseract
from PIL import Image
import re
import io
import os

# ตั้งค่า path ของ Tesseract ตามระบบปฏิบัติการ
if os.name == 'nt':  # Windows
    pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
else:  # Linux/Streamlit Cloud
    pytesseract.pytesseract.tesseract_cmd = 'tesseract'

# ตั้งค่าหน้าเว็บ
st.set_page_config(page_title="ระบบสแกนสลิป & สรุปยอด", layout="wide")
st.title("ระบบสแกนสลิปโอนเงิน")

# อัปโหลดไฟล์ภาพ
uploaded_files = st.file_uploader("อัปโหลดสลิปภาพ (รองรับหลายไฟล์)", type=["png", "jpg", "jpeg"], accept_multiple_files=True)

# ฟังก์ชันแยกข้อมูลจากข้อความ OCR
def extract_transaction_data(text):
    date_pattern = r'\d{2}/\d{2}/\d{2}'
    time_pattern = r'\d{2}:\d{2}:\d{2}'
    amount_pattern = r'(\d{1,3}(?:,\d{3})*)\s*LAK'  # แก้ตรงนี้เพื่อให้จับจำนวนเงิน 69,000 ได้
    ref_pattern = r'\d{14}'
    receiver_pattern = r'[A-Z]+\s+[A-Z]+\s+MR'

    date = re.search(date_pattern, text)
    time = re.search(time_pattern, text)
    amount = re.search(amount_pattern, text)
    reference = re.search(ref_pattern, text)
    receiver = re.search(receiver_pattern, text)

    return {
        'Date': date.group() if date else '',
        'Time': time.group() if time else '',
        'Amount (LAK)': amount.group(1).replace(',', '').strip() if amount else '',
        'Reference': reference.group() if reference else '',
        'Receiver': receiver.group().strip() if receiver else ''
    }

# ประมวลผลภาพ
if uploaded_files:
    results = []
    for file in uploaded_files:
        image = Image.open(file)
        text = pytesseract.image_to_string(image, config='--oem 3 --psm 6')
        st.markdown("#### OCR Text (แสดงผลข้อความจากภาพ):")
        st.code(text, language='text')
        data = extract_transaction_data(text)
        results.append(data)

    # ตรวจสอบว่ามีข้อมูลจาก OCR หรือไม่ ก่อนสร้างตาราง
    if results:
        df = pd.DataFrame(results)
        df['Amount (LAK)'] = pd.to_numeric(df['Amount (LAK)'], errors='coerce')
        df = df.dropna(subset=['Amount (LAK)'])
        df.sort_values(by=['Date', 'Time'], inplace=True)
        df.reset_index(drop=True, inplace=True)

        st.success(f"รวมยอดทั้งหมด: {df['Amount (LAK)'].sum():,.0f} LAK")
        st.dataframe(df)

        buffer = io.BytesIO()
        df.to_excel(buffer, index=False)
        buffer.seek(0)

        st.download_button(
            label="ดาวน์โหลดไฟล์ Excel",
            data=buffer,
            file_name="summary.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    else:
        st.warning("ไม่พบข้อมูลที่อ่านได้จากภาพที่อัปโหลด")
