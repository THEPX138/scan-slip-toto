import streamlit as st
import pandas as pd
import pytesseract
from PIL import Image
import re
import io
import os
import cv2
import numpy as np
from pyzbar.pyzbar import decode

# ตั้งค่า path ของ Tesseract ตามระบบปฏิบัติการ
if os.name == 'nt':
    pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# ตั้งค่าหน้าเว็บ
st.set_page_config(page_title="ระบบสแกนสลิปโอนเงิน", layout="wide")
st.title("ระบบสแกนสลิปโอนเงิน")

# สำหรับบันทึกประวัติทั้งหมด
if 'history' not in st.session_state:
    st.session_state.history = []

# ฟังก์ชันแยกข้อมูลจากข้อความ OCR
def extract_transaction_data(text):
    date_pattern = r'\d{2}/\d{2}/\d{2}'
    time_pattern = r'\d{2}:\d{2}:\d{2}'
    amount_pattern = r'\b\d{1,3}(?:,\d{3})+\b(?=\s*LAK)'  # ตัวเลขหลักพันขึ้นไป
    reference_pattern = r'\b\d{14}\b'
    ticket_pattern = r'GP[A-Z0-9]{10,}'
    receiver_pattern = r'[A-Z]+\s+[A-Z]+\s+MR'

    return {
        'Date': re.search(date_pattern, text).group() if re.search(date_pattern, text) else '',
        'Time': re.search(time_pattern, text).group() if re.search(time_pattern, text) else '',
        'Amount (LAK)': re.search(amount_pattern, text).group().replace(',', '') if re.search(amount_pattern, text) else '',
        'Reference': re.search(reference_pattern, text).group() if re.search(reference_pattern, text) else '',
        'Ticket': re.search(ticket_pattern, text).group() if re.search(ticket_pattern, text) else '',
        'Receiver': re.search(receiver_pattern, text).group() if re.search(receiver_pattern, text) else '',
        'Text': text
    }

# ฟังก์ชันอ่าน QR code
@st.cache_data
def read_qr_code(image):
    decoded_objects = decode(image)
    if decoded_objects:
        return decoded_objects[0].data.decode('utf-8')
    return ''

# ฟังก์ชันตัดเฉพาะตัวเลขสีแดง (ประมาณค่าตำแหน่งจากภาพสลิป)
def crop_red_amount_area(image):
    img = np.array(image)
    hsv = cv2.cvtColor(img, cv2.COLOR_RGB2HSV)
    mask1 = cv2.inRange(hsv, (0, 50, 50), (10, 255, 255))
    mask2 = cv2.inRange(hsv, (160, 50, 50), (180, 255, 255))
    mask = mask1 | mask2
    red_area = cv2.bitwise_and(img, img, mask=mask)
    gray = cv2.cvtColor(red_area, cv2.COLOR_RGB2GRAY)
    _, thresh = cv2.threshold(gray, 50, 255, cv2.THRESH_BINARY)
    return Image.fromarray(thresh)

uploaded_files = st.file_uploader("อัปโหลดสลิปภาพ (PNG, JPG, JPEG)", type=["png", "jpg", "jpeg"], accept_multiple_files=True)

if uploaded_files:
    success_data, duplicate_data = [], []
    qr_codes_seen = set()

    for file in uploaded_files:
        image = Image.open(file)
        text = pytesseract.image_to_string(image, config='--oem 3 --psm 6')
        cropped_img = crop_red_amount_area(image)
        red_text = pytesseract.image_to_string(cropped_img, config='--psm 6 digits')

        data = extract_transaction_data(text)

        # ใช้ตัวเลขจากตัวหนังสือสีแดงถ้าดึงได้
        red_amount_match = re.search(r'\d{1,3}(?:,\d{3})+', red_text)
        if red_amount_match:
            data['Amount (LAK)'] = red_amount_match.group().replace(',', '')

        qr_result = read_qr_code(image)
        data['QR'] = qr_result

        # ตรวจสอบซ้ำ
        key = (data['Date'], data['Time'], data['Amount (LAK)'], data['Ticket'], qr_result)
        is_duplicate = any(
            (row['Date'], row['Time'], row['Amount (LAK)'], row['Ticket'], row['QR']) == key for row in st.session_state.history
        )
        data['duplicate'] = is_duplicate

        st.session_state.history.append(data)
        (duplicate_data if is_duplicate else success_data).append(data)

    # แสดงข้อมูล
    if success_data:
        df = pd.DataFrame(success_data)
        df['Amount (LAK)'] = pd.to_numeric(df['Amount (LAK)'], errors='coerce')
        st.success(f"รวมยอดทั้งหมด: {df['Amount (LAK)'].sum():,.0f} LAK")
        st.subheader("รายการสลิปที่ไม่ซ้ำ:")
        st.dataframe(df)

        buffer = io.BytesIO()
        df.to_excel(buffer, index=False)
        st.download_button("ดาวน์โหลด Excel (ไม่ซ้ำ)", buffer.getvalue(), file_name="unique_slips.xlsx")

    if duplicate_data:
        df_dup = pd.DataFrame(duplicate_data)
        st.error("รายการสลิปที่ตรวจพบว่าซ้ำ:")
        st.dataframe(df_dup)

        buffer2 = io.BytesIO()
        df_dup.to_excel(buffer2, index=False)
        st.download_button("ดาวน์โหลด Excel (ซ้ำ)", buffer2.getvalue(), file_name="duplicate_slips.xlsx")

    # แสดงประวัติทั้งหมด
    st.subheader("ประวัติทั้งหมดของสลิป (รวมทั้งซ้ำและไม่ซ้ำ):")
    st.dataframe(pd.DataFrame(st.session_state.history))

    # ปุ่มโชว์/ซ่อน OCR Text
    with st.expander("OCR Text (คลิกเพื่อดู/ซ่อน)"):
        for data in st.session_state.history:
            st.code(data['Text'])
