import streamlit as st
import pandas as pd
import pytesseract
from PIL import Image
import re
import io
import os

# กำหนด path ของ Tesseract
if os.name == 'nt':
    pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
else:
    pytesseract.pytesseract.tesseract_cmd = 'tesseract'

st.set_page_config(page_title="ระบบสแกนสลิป & สรุปยอด", layout="wide")
st.title("ระบบสแกนสลิปโอนเงิน")

uploaded_files = st.file_uploader("อัปโหลดสลิปภาพ (รองรับหลายไฟล์)", type=["png", "jpg", "jpeg"], accept_multiple_files=True)

def extract_transaction_data(text):
    date_pattern = r'\d{2}/\d{2}/\d{2}'
    time_pattern = r'\d{2}:\d{2}:\d{2}'
    amount_pattern = r'(?:\d{1,3}(?:,\d{3})+|\d+)\s*LAK'
    ref_pattern = r'\d{14}'
    receiver_pattern = r'[A-Z]+\s+[A-Z]+\s+MR'

    date = re.search(date_pattern, text)
    time = re.search(time_pattern, text)
    reference = re.search(ref_pattern, text)
    receiver = re.search(receiver_pattern, text)

    # หา amount หลายค่าแล้วเลือกค่าที่มากที่สุด
    amount_matches = re.findall(amount_pattern, text)
    amounts = []
    for match in amount_matches:
        try:
            numeric = float(match.replace(",", "").replace("LAK", "").strip())
            amounts.append(numeric)
        except:
            continue
    amount = max(amounts) if amounts else ''

    return {
        'Date': date.group() if date else '',
        'Time': time.group() if time else '',
        'Amount (LAK)': amount,
        'Reference': reference.group() if reference else '',
        'Receiver': receiver.group().strip() if receiver else ''
    }

if uploaded_files:
    results = []
    for file in uploaded_files:
        image = Image.open(file)
        text = pytesseract.image_to_string(image, config='--oem 3 --psm 6')
        st.markdown("#### OCR Text (แสดงผลข้อความจากภาพ):")
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
