import streamlit as st
import pandas as pd
import pytesseract
from PIL import Image
import re
import io
import os

# ✅ กำหนด path Tesseract ตามระบบ
if os.name == 'nt':  # Windows
    pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
else:  # Linux/Cloud
    pytesseract.pytesseract.tesseract_cmd = 'tesseract'

# ✅ ตั้งค่าหน้าเว็บ
st.set_page_config(page_title="ระบบสแกนสลิป", layout="wide")
st.title("ระบบสแกนสลิปโอนเงิน")

# ✅ ตัวแปรเก็บประวัติ
if "history" not in st.session_state:
    st.session_state.history = []

# ✅ ฟังก์ชันดึงข้อมูลจาก OCR
def extract_transaction_data(text):
    date_pattern = r'\d{2}/\d{2}/\d{2}'
    time_pattern = r'\d{2}:\d{2}:\d{2}'
    amount_pattern = r'69,000\s*LAK|\d{1,3}(?:,\d{3})+\s*LAK'
    ref_pattern = r'202\d{10}'
    ticket_pattern = r'[A-Z0-9]{10,}'
    receiver_pattern = r'[A-Z]+\s+[A-Z]+\s+MR'

    date = re.search(date_pattern, text)
    time = re.search(time_pattern, text)
    amount = re.search(amount_pattern, text)
    ref = re.search(ref_pattern, text)
    ticket = re.search(ticket_pattern, text)
    receiver = re.search(receiver_pattern, text)

    return {
        'Date': date.group() if date else '',
        'Time': time.group() if time else '',
        'Amount (LAK)': amount.group().replace(',', '').replace('LAK', '').strip() if amount else '',
        'Reference': ref.group() if ref else '',
        'Ticket': ticket.group() if ticket else '',
        'Receiver': receiver.group().strip() if receiver else '',
        'Text': text  # สำหรับดูย้อนหลัง
    }

# ✅ อัปโหลดไฟล์
uploaded_files = st.file_uploader("อัปโหลดสลิปภาพ (PNG, JPG)", type=["png", "jpg", "jpeg"], accept_multiple_files=True)

# ✅ OCR ประมวลผล
if uploaded_files:
    new_data = []
    for file in uploaded_files:
        image = Image.open(file)
        text = pytesseract.image_to_string(image, config='--oem 3 --psm 6')
        result = extract_transaction_data(text)
        new_data.append(result)

    df_new = pd.DataFrame(new_data)
    df_new['Amount (LAK)'] = pd.to_numeric(df_new['Amount (LAK)'], errors='coerce')
    df_new = df_new.dropna(subset=['Amount (LAK)'])

    # ✅ ตรวจสอบซ้ำกับประวัติ
    df_history = pd.DataFrame(st.session_state.history)
    merged = df_new.merge(df_history, how='left', on=["Date", "Time", "Amount (LAK)", "Ticket"], indicator=True)

    df_not_duplicate = merged[merged['_merge'] == 'left_only'].copy()
    df_duplicate = merged[merged['_merge'] == 'both'].copy()

    # ✅ เพิ่มในประวัติ
    if not df_not_duplicate.empty:
        st.session_state.history.extend(df_not_duplicate[df_new.columns].to_dict(orient="records"))

    # ✅ แสดงผล
    st.success(f"รวมยอดทั้งหมด: {df_not_duplicate['Amount (LAK)'].sum():,.0f} LAK")

    st.markdown("### รายการสลิปที่ไม่ซ้ำ:")
    st.dataframe(df_not_duplicate[df_new.columns])
    buffer = io.BytesIO()
    df_not_duplicate[df_new.columns].to_excel(buffer, index=False)
    buffer.seek(0)
    st.download_button("ดาวน์โหลด Excel (ไม่ซ้ำ)", data=buffer, file_name="not_duplicate.xlsx")

    st.markdown("### รายการสลิปที่ตรวจพบว่าซ้ำ:")
    st.dataframe(df_duplicate[df_new.columns])
    buffer_dup = io.BytesIO()
    df_duplicate[df_new.columns].to_excel(buffer_dup, index=False)
    buffer_dup.seek(0)
    st.download_button("ดาวน์โหลด Excel (ซ้ำ)", data=buffer_dup, file_name="duplicate.xlsx")

    st.markdown("### ประวัติทั้งหมดของสลิป (รวมทั้งซ้ำและไม่ซ้ำ):")
    df_all = pd.DataFrame(st.session_state.history)
    st.dataframe(df_all)

    # ✅ ปุ่มแสดง/ซ่อนข้อความ OCR
    with st.expander("🔍 แสดงข้อความ OCR (จากภาพทั้งหมด)"):
        for i, row in enumerate(new_data):
            st.code(row["Text"], language="text")
