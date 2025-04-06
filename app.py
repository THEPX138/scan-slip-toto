import streamlit as st
import pandas as pd
import pytesseract
from PIL import Image
import re
import io
import os

# ตั้งค่า path ของ Tesseract OCR ตามระบบปฏิบัติการ
if os.name == 'nt':  # Windows
    pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
else:  # Linux/Streamlit Cloud
    pytesseract.pytesseract.tesseract_cmd = 'tesseract'

# ตั้งค่าหน้าเว็บ
st.set_page_config(page_title="ระบบสแกนสลิป & สรุปยอด", layout="wide")
st.title("ระบบสแกนสลิปโอนเงิน")

# อัปโหลดไฟล์
uploaded_files = st.file_uploader("อัปโหลดสลิปภาพ (รองรับหลายไฟล์)", type=["png", "jpg", "jpeg"], accept_multiple_files=True)

# ฟังก์ชันดึงข้อมูลจากข้อความ OCR
def extract_transaction_data(text):
    date_pattern = r'\d{2}/\d{2}/\d{2}'
    time_pattern = r'\d{2}:\d{2}:\d{2}'
    amount_patterns = [
        r'(?<=\b)\d{1,3}(?:,\d{3})+(?:\.\d{2})?\s*LAK',  # 69,000 LAK
        r'\d{2,6}\s*LAK',                               # 69000 LAK
        r'(?<=\n)\d{2,6}(?=\n)'                         # บรรทัดเดี่ยว เช่น 69000
    ]
    ref_pattern = r'\d{14}'
    receiver_pattern = r'[A-Z]+\s+[A-Z]+\s+MR'

    date = re.search(date_pattern, text)
    time = re.search(time_pattern, text)
    reference = re.search(ref_pattern, text)
    receiver = re.search(receiver_pattern, text)

    # หายอดที่เป็นไปได้ทั้งหมด แล้วเลือกค่าสูงสุด
    amounts = []
    for pattern in amount_patterns:
        matches = re.findall(pattern, text)
        for match in matches:
            cleaned = match.replace(',', '').replace('LAK', '').strip()
            if cleaned.isdigit():
                amounts.append(int(cleaned))
    max_amount = max(amounts) if amounts else ''

    return {
        'Date': date.group() if date else '',
        'Time': time.group() if time else '',
        'Amount (LAK)': max_amount,
        'Reference': reference.group() if reference else '',
        'Receiver': receiver.group().strip() if receiver else ''
    }

# ประมวลผล
if uploaded_files:
    results = []
    for file in uploaded_files:
        image = Image.open(file)
        text = pytesseract.image_to_string(image, config='--oem 3 --psm 6')

        st.markdown("#### OCR Text (ผลลัพธ์ข้อความจากภาพ):")
        st.code(text, language='text')

        data = extract_transaction_data(text)
        results.append(data)

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
