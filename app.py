import streamlit as st
import pandas as pd
import pytesseract
from PIL import Image
import re
import io
import os

# Set path for tesseract
if os.name == 'nt':
    pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# Session state สำหรับเก็บประวัติ
if 'history' not in st.session_state:
    st.session_state['history'] = []

# ฟังก์ชันดึงข้อมูลจาก OCR
def extract_transaction_data(text):
    date_pattern = r'\d{2}/\d{2}/\d{2}'
    time_pattern = r'\d{2}:\d{2}:\d{2}'
    amount_pattern = r'69,000 LAK|(?:\d{1,3}(?:,\d{3})+|\d+)\s*LAK'
    reference_pattern = r'\d{14}'
    ticket_pattern = r'[A-Z0-9]{12}'
    receiver_pattern = r'[A-Z]+\s+[A-Z]+\s+MR'

    date = re.search(date_pattern, text)
    time = re.search(time_pattern, text)
    amount = re.search(amount_pattern, text)
    reference = re.search(reference_pattern, text)
    ticket = re.search(ticket_pattern, text)
    receiver = re.search(receiver_pattern, text)

    return {
        'Date': date.group() if date else '',
        'Time': time.group() if time else '',
        'Amount (LAK)': amount.group().replace(',', '').replace('LAK', '').strip() if amount else '',
        'Reference': reference.group() if reference else '',
        'Ticket': ticket.group() if ticket else '',
        'Receiver': receiver.group().strip() if receiver else '',
        'Text': text
    }

# UI
st.set_page_config(page_title="ระบบสแกนสลิปโอนเงิน", layout="wide")
st.title("ระบบสแกนสลิปโอนเงิน")

uploaded_files = st.file_uploader("อัปโหลดสลิปภาพ (PNG, JPG)", type=["png", "jpg", "jpeg"], accept_multiple_files=True)

show_ocr = st.toggle("แสดงข้อความ OCR Text", value=False)

# ประมวลผล
unique_data = []
duplicate_data = []

if uploaded_files:
    for file in uploaded_files:
        image = Image.open(file)
        text = pytesseract.image_to_string(image, config='--oem 3 --psm 6')

        if show_ocr:
            st.markdown("#### OCR Text:")
            st.code(text)

        data = extract_transaction_data(text)
        data['duplicate'] = False

        key = (data['Date'], data['Time'], data['Amount (LAK)'], data['Ticket'])

        # ตรวจสอบซ้ำ
        is_duplicate = any(
            (h['Date'], h['Time'], h['Amount (LAK)'], h['Ticket']) == key
            for h in st.session_state['history']
        )

        if is_duplicate:
            data['duplicate'] = True
            duplicate_data.append(data)
        else:
            unique_data.append(data)

        st.session_state['history'].append(data)

# แสดงผล
if unique_data:
    st.success(f"รวมยอดทั้งหมด: {sum([int(d['Amount (LAK)']) for d in unique_data]):,} LAK")
    df = pd.DataFrame(unique_data)
    st.markdown("### รายการสลิปที่ไม่ซ้ำ:")
    st.dataframe(df)
    buffer = io.BytesIO()
    df.to_excel(buffer, index=False)
    buffer.seek(0)
    st.download_button("ดาวน์โหลด Excel (ไม่ซ้ำ)", data=buffer, file_name="unique.xlsx")

if duplicate_data:
    st.error("ตรวจพบสลิปซ้ำ!")
    df_dup = pd.DataFrame(duplicate_data)
    st.markdown("### รายการสลิปที่ตรวจพบว่าซ้ำ:")
    st.dataframe(df_dup)
    buffer = io.BytesIO()
    df_dup.to_excel(buffer, index=False)
    buffer.seek(0)
    st.download_button("ดาวน์โหลด Excel (ซ้ำ)", data=buffer, file_name="duplicate.xlsx")

if st.session_state['history']:
    st.markdown("### ประวัติทั้งหมดของสลิป (รวมทั้งซ้ำและไม่ซ้ำ):")
    st.dataframe(pd.DataFrame(st.session_state['history']))
