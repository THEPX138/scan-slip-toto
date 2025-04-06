import streamlit as st
import pandas as pd
import pytesseract
from PIL import Image
import re
import io
import os

# ตั้งค่า path ของ Tesseract
if os.name == 'nt':
    pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
else:
    pytesseract.pytesseract.tesseract_cmd = 'tesseract'

# ตั้งค่าหน้าเว็บ
st.set_page_config(page_title="ระบบสแกนสลิป & สรุปยอด", layout="wide")
st.title("ระบบสแกนสลิปโอนเงิน")

# ฟังก์ชันดึงข้อมูลจากข้อความ OCR
def extract_transaction_data(text):
    date_pattern = r'\d{2}/\d{2}/\d{2}'
    time_pattern = r'\d{2}:\d{2}:\d{2}'
    amount_pattern = r'69,000\s*LAK|[\d,]+\s*LAK'
    ref_pattern = r'\d{14}'
    ticket_pattern = r'(?<=Ticket\s)[A-Z0-9]+'
    receiver_pattern = r'[A-Z]+\s+[A-Z]+\s+MR'

    date = re.search(date_pattern, text)
    time = re.search(time_pattern, text)
    amount = re.search(amount_pattern, text)
    reference = re.search(ref_pattern, text)
    ticket = re.search(ticket_pattern, text)
    receiver = re.search(receiver_pattern, text)

    return {
        'Date': date.group() if date else '',
        'Time': time.group() if time else '',
        'Amount (LAK)': amount.group().replace(',', '').replace('LAK', '').strip() if amount else '',
        'Reference': reference.group() if reference else '',
        'Ticket': ticket.group().strip() if ticket else '',
        'Receiver': receiver.group().strip() if receiver else ''
    }

# อัปโหลดสลิป
uploaded_files = st.file_uploader("อัปโหลดสลิปภาพ (รองรับหลายไฟล์)", type=["png", "jpg", "jpeg"], accept_multiple_files=True)

# ถ้ามีการอัปโหลด
if uploaded_files:
    unique_results = []
    duplicate_results = []
    all_results = []

    for file in uploaded_files:
        image = Image.open(file)
        text = pytesseract.image_to_string(image, config='--oem 3 --psm 6')

        # ซ่อน OCR Text (ลบหรือคอมเมนต์ไว้)
        # st.markdown("#### OCR Text (แสดงข้อความจากภาพ):")
        # st.code(text, language='text')

        data = extract_transaction_data(text)
        all_results.append(data)

        # ตรวจสอบสลิปซ้ำ
        key_fields = ['Date', 'Time', 'Amount (LAK)', 'Reference', 'Ticket']
        duplicate = any(
            all(existing.get(k) == data.get(k) for k in key_fields)
            for existing in unique_results
        )

        if duplicate:
            st.error(f"**พบสลิปซ้ำ:** {data}")
            duplicate_results.append(data)
        else:
            unique_results.append(data)

    # แสดงตารางสลิปที่ไม่ซ้ำ
    if unique_results:
        df = pd.DataFrame(unique_results)
        df['Amount (LAK)'] = pd.to_numeric(df['Amount (LAK)'], errors='coerce')
        df = df.dropna(subset=['Amount (LAK)'])
        df.sort_values(by=['Date', 'Time'], inplace=True)
        df.reset_index(drop=True, inplace=True)

        st.success(f"รวมยอดทั้งหมด: {df['Amount (LAK)'].sum():,.0f} LAK")
        st.markdown("### รายการสลิปที่ไม่ซ้ำ:")
        st.dataframe(df)

        buffer = io.BytesIO()
        df.to_excel(buffer, index=False)
        buffer.seek(0)
        st.download_button("ดาวน์โหลด Excel (ไม่ซ้ำ)", buffer, file_name="unique_slips.xlsx",
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    # แสดงตารางสลิปที่ซ้ำ
    if duplicate_results:
        df_dup = pd.DataFrame(duplicate_results)
        st.markdown("### รายการสลิปที่ตรวจพบว่าซ้ำ:")
        st.dataframe(df_dup, use_container_width=True)

        buffer_dup = io.BytesIO()
        df_dup.to_excel(buffer_dup, index=False)
        buffer_dup.seek(0)
        st.download_button("ดาวน์โหลด Excel (ซ้ำ)", buffer_dup, file_name="duplicate_slips.xlsx",
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    # แสดงประวัติทั้งหมด (รวมซ้ำและไม่ซ้ำ)
    df_all = pd.DataFrame(all_results)
    st.markdown("### ประวัติทั้งหมดของสลิป (รวมทั้งซ้ำและไม่ซ้ำ):")
    st.dataframe(df_all)

    buffer_all = io.BytesIO()
    df_all.to_excel(buffer_all, index=False)
    buffer_all.seek(0)
    st.download_button("ดาวน์โหลด Excel (ทั้งหมด)", buffer_all, file_name="all_slips.xlsx",
                       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
else:
    st.info("กรุณาอัปโหลดสลิปภาพเพื่อเริ่มต้นประมวลผล")
