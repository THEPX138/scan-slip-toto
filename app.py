import streamlit as st import pandas as pd import pytesseract from PIL import Image import re import io import os import cv2 import numpy as np from pyzbar.pyzbar import decode

ตั้งค่า path ของ Tesseract สำหรับ Windows

if os.name == 'nt': pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

ฟังก์ชันอ่าน QR Code

def read_qr_code(image): qr_codes = decode(image) if qr_codes: return qr_codes[0].data.decode('utf-8') return ''

ฟังก์ชันตัดเฉพาะบริเวณที่มีตัวหนังสือสีแดง

def extract_red_text_area(pil_image): cv_image = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR) hsv = cv2.cvtColor(cv_image, cv2.COLOR_BGR2HSV) lower_red1 = np.array([0, 70, 50]) upper_red1 = np.array([10, 255, 255]) lower_red2 = np.array([160, 70, 50]) upper_red2 = np.array([180, 255, 255]) mask1 = cv2.inRange(hsv, lower_red1, upper_red1) mask2 = cv2.inRange(hsv, lower_red2, upper_red2) mask = cv2.bitwise_or(mask1, mask2) result = cv2.bitwise_and(cv_image, cv_image, mask=mask) red_only = cv2.cvtColor(result, cv2.COLOR_BGR2GRAY) return Image.fromarray(red_only)

ฟังก์ชันแยกข้อมูลจากข้อความ OCR

def extract_transaction_data(text): date = re.search(r'\d{2}/\d{2}/\d{2}', text) time = re.search(r'\d{2}:\d{2}:\d{2}', text) amount = re.search(r'\d{1,3}(?:,\d{3})+\sLAK', text) reference = re.search(r'\d{14}', text) receiver = re.search(r'[A-Z]+\s+[A-Z]+\s+MR', text) ticket = re.search(r'Ticket\s([A-Z0-9]+)', text)

return {
    'Date': date.group() if date else '',
    'Time': time.group() if time else '',
    'Amount (LAK)': amount.group().replace(',', '').replace('LAK', '').strip() if amount else '',
    'Reference': reference.group() if reference else '',
    'Receiver': receiver.group().strip() if receiver else '',
    'Ticket': ticket.group(1) if ticket else '',
    'Text': text
}

st.set_page_config(page_title="ระบบสแกนสลิปโอนเงิน", layout="wide") st.title("ระบบสแกนสลิปโอนเงิน")

uploaded_files = st.file_uploader("อัปโหลดสลิปภาพ (รองรับหลายไฟล์)", type=["png", "jpg", "jpeg"], accept_multiple_files=True)

history = [] duplicates = [] duplicate_keys = set() show_ocr = st.checkbox("แสดงข้อความ OCR จากภาพ")

if uploaded_files: results = [] for file in uploaded_files: image = Image.open(file) red_image = extract_red_text_area(image) red_text = pytesseract.image_to_string(red_image, config='--psm 6')

text = pytesseract.image_to_string(image, config='--psm 6')
    data = extract_transaction_data(text)

    if not data['Amount (LAK)']:
        red_amount = re.search(r'\d{1,3}(?:,\d{3})+', red_text)
        if red_amount:
            data['Amount (LAK)'] = red_amount.group().replace(',', '').strip()

    qr_ticket = read_qr_code(np.array(image))
    if qr_ticket:
        data['Ticket'] = qr_ticket

    key = f"{data['Date']}_{data['Time']}_{data['Amount (LAK)']}_{data['Ticket']}"
    if key in duplicate_keys:
        duplicates.append(data)
    else:
        duplicate_keys.add(key)
        results.append(data)
    history.append(data)

    if show_ocr:
        with st.expander(f"OCR Text: {file.name}"):
            st.code(text)

if results:
    df = pd.DataFrame(results)
    df['Amount (LAK)'] = pd.to_numeric(df['Amount (LAK)'], errors='coerce')
    df.dropna(subset=['Amount (LAK)'], inplace=True)
    st.success(f"รวมยอดทั้งหมด: {df['Amount (LAK)'].sum():,.0f} LAK")
    st.markdown("### รายการสลิปที่ไม่ซ้ำ:")
    st.dataframe(df)

if duplicates:
    st.markdown("### รายการสลิปที่ตรวจพบว่าซ้ำ:")
    st.dataframe(pd.DataFrame(duplicates), height=200)

st.markdown("### ประวัติทั้งหมดของสลิป (รวมทั้งซ้ำและไม่ซ้ำ):")
st.dataframe(pd.DataFrame(history), height=200)

buffer = io.BytesIO()
pd.DataFrame(results).to_excel(buffer, index=False)
buffer.seek(0)
st.download_button("ดาวน์โหลด Excel (ไม่ซ้ำ)", buffer, file_name="result.xlsx")
