import streamlit as st 
import pandas as pd 
import pytesseract 
from PIL 
import Image 
import re 
import io 
import os 
import cv2 
import numpy as np 
from pyzbar.pyzbar 
import decode

ตั้งค่า path ของ Tesseract บน Windows

if os.name == 'nt': pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

st.set_page_config(page_title="ระบบสแกนสลิป", layout="wide") st.title("ระบบสแกนสลิปโอนเงิน")

uploaded_files = st.file_uploader("อัปโหลดสลิปภาพ (รองรับหลายไฟล์)", type=["png", "jpg", "jpeg"], accept_multiple_files=True)

all_results = [] uploaded_history = [] duplicate_slips = [] detected_texts = []

ฟังก์ชัน OCR และแยกข้อมูลจากข้อความ

def extract_transaction_data(text): date_pattern = r"\d{2}/\d{2}/\d{2}" time_pattern = r"\d{2}:\d{2}:\d{2}" amount_pattern = r"69,000\sLAK|\d{1,3}(?:,\d{3})\s*LAK" reference_pattern = r"\d{14}" ticket_pattern = r"GPAXZVILPZFM|[A-Z0-9]{12}" receiver_pattern = r"[A-Z]+\s+[A-Z]+\s+MR"

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

ตรวจจับ QR

def decode_qr(image): decoded = decode(image) if decoded: return decoded[0].data.decode('utf-8') return ''

if uploaded_files: st.subheader("OCR Text (คลิกเพื่อแสดง/ซ่อน)") with st.expander("คลิกเพื่อดูข้อความจาก OCR"): for file in uploaded_files: image = Image.open(file) opencv_image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR) qr_text = decode_qr(opencv_image)

text = pytesseract.image_to_string(image, config='--oem 3 --psm 6')
        st.code(text)
        data = extract_transaction_data(text)
        data['QR'] = qr_text

        if any(
            data['Date'] == old['Date'] and
            data['Time'] == old['Time'] and
            data['Amount (LAK)'] == old['Amount (LAK)'] and
            data['Ticket'] == old['Ticket']
            for old in uploaded_history
        ):
            duplicate_slips.append(data)
        else:
            uploaded_history.append(data)
            all_results.append(data)

df_valid = pd.DataFrame(all_results)
df_duplicate = pd.DataFrame(duplicate_slips)
df_history = pd.DataFrame(uploaded_history)

# แสดงผลรวม
total = df_valid['Amount (LAK)'].astype(float).sum() if not df_valid.empty else 0
st.success(f"รวมยอดทั้งหมด: {total:,.0f} LAK")

# แสดงตาราง
st.markdown("## รายการสลิปที่ไม่ซ้ำ:")
st.dataframe(df_valid)

st.markdown("ดาวน์โหลด Excel (ไม่ซ้ำ)")
buffer_valid = io.BytesIO()
df_valid.to_excel(buffer_valid, index=False)
buffer_valid.seek(0)
st.download_button("ดาวน์โหลด", buffer_valid, file_name="valid_slips.xlsx")

st.markdown("## รายการสลิปที่ตรวจพบว่าซ้ำ:")
st.dataframe(df_duplicate.style.set_properties(**{'background-color': '#FFCCCC'}))

st.markdown("ดาวน์โหลด Excel (ซ้ำ)")
buffer_dup = io.BytesIO()
df_duplicate.to_excel(buffer_dup, index=False)
buffer_dup.seek(0)
st.download_button("ดาวน์โหลด", buffer_dup, file_name="duplicate_slips.xlsx")

st.markdown("## ประวัติทั้งหมดของสลิป (รวมทั้งซ้ำและไม่ซ้ำ):")
st.dataframe(df_history)

