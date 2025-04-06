import streamlit as st
import pandas as pd
import pytesseract
from PIL import Image
import re
import io
import os

# กำหนด path Tesseract ตามระบบ
if os.name == 'nt':
    pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
else:
    pytesseract.pytesseract.tesseract_cmd = 'tesseract'

# UI หน้าหลัก
st.set_page_config(page_title="ระบบสแกนสลิป & สรุปยอด", layout="wide")
st.title("ระบบสแกนสลิปโอนเงิน")

uploaded_files = st.file_uploader("อัปโหลดสลิปภาพ (รองรับหลายไฟล์)", type=["png", "jpg", "jpeg"], accept_multiple_files=True)

# อ่านข้อมูลจาก text OCR
def extract_transaction_data(text):
    date_pattern = r'\d{2}/\d{2}/\d{2}'
    time_pattern = r'\d{2}:\d{2}:\d{2}'
    amount_pattern = r'(\d{1,3}(?:,\d{3})+|\d+)\s*LAK'
    ref_pattern = r'\d{14}'
    ticket_pattern = r'(?<=Ticket\s)[A-Z0-9]+'
    receiver_pattern = r'[A-Z]+\s+[A-Z]+\s+MR'

    date = re.search(date_pattern, text)
    time = re.search(time_pattern, text)
    amounts = re.findall(amount_pattern, text)

    amount = max([int(a.replace(',', '')) for a in amounts]) if amounts else ''

    reference = re.search(ref_pattern, text)
    ticket = re.search(ticket_pattern, text)
    receiver = re.search(receiver_pattern, text)

    return {
        'Date': date.group() if date else '',
        'Time': time.group() if time else '',
        'Amount (LAK)': amount,
        'Reference': reference.group() if reference else '',
        'Ticket': ticket.group().strip() if ticket else '',
        'Receiver': receiver.group().strip() if receiver else '',
        'Text': text  # เก็บไว้ตรวจสอบย้อนหลัง
    }

# สำหรับประวัติทั้งหมด
all_results = []
duplicate_results = []

# Session เก็บประวัติ
if 'all_history' not in st.session_state:
    st.session_state['all_history'] = []

if uploaded_files:
    for file in uploaded_files:
        image = Image.open(file)
        text = pytesseract.image_to_string(image, config='--oem 3 --psm 6')
        data = extract_transaction_data(text)

        # ป้องกันซ้ำ (ดูจาก Date+Time+Amount+Ticket)
        duplicate = False
        for old in st.session_state['all_history']:
            if (data['Date'], data['Time'], data['Amount (LAK)'], data['Ticket']) == \
               (old['Date'], old['Time'], old['Amount (LAK)'], old['Ticket']):
                duplicate = True
                break

        if duplicate:
            data['duplicate'] = True
            duplicate_results.append(data)
        else:
            data['duplicate'] = False
            all_results.append(data)
            st.session_state['all_history'].append(data)

    # แสดงตาราง
    if all_results:
        df_new = pd.DataFrame(all_results)
        df_new['Amount (LAK)'] = pd.to_numeric(df_new['Amount (LAK)'], errors='coerce')
        st.success(f"รวมยอดทั้งหมด: {df_new['Amount (LAK)'].sum():,.0f} LAK")
        st.markdown("### รายการสลิปที่ไม่ซ้ำ:")
        st.dataframe(df_new)

        buffer = io.BytesIO()
        df_new.to_excel(buffer, index=False)
        buffer.seek(0)

        st.download_button(
            label="ดาวน์โหลด Excel (ไม่ซ้ำ)",
            data=buffer,
            file_name="unique_slips.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    if duplicate_results:
        df_dup = pd.DataFrame(duplicate_results)
        st.markdown("### รายการสลิปที่ตรวจพบว่าซ้ำ:", unsafe_allow_html=True)
        st.dataframe(df_dup.style.applymap(lambda v: 'background-color: #ffcccc', subset=pd.IndexSlice[:, :]))

        buffer2 = io.BytesIO()
        df_dup.to_excel(buffer2, index=False)
        buffer2.seek(0)

        st.download_button(
            label="ดาวน์โหลด Excel (ซ้ำ)",
            data=buffer2,
            file_name="duplicate_slips.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    # ประวัติทั้งหมด
    if st.session_state['all_history']:
        df_all = pd.DataFrame(st.session_state['all_history'])
        st.markdown("### ประวัติทั้งหมดของสลิป (รวมทั้งซ้ำและไม่ซ้ำ):")
        st.dataframe(df_all)

        #
