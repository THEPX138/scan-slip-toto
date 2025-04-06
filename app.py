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

# ตั้งค่า path ของ Tesseract บน Windows
if os.name == 'nt':
    pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

st.set_page_config(page_title="ระบบสแกนสลิป", layout="wide")
st.title("ระบบสแกนสลิปโอนเงิน")

uploaded_files = st.file_uploader("อัปโหลดสลิปภาพ (รองรับหลายไฟล์)", type=["png", "jpg", "jpeg"], accept_multiple_files=True)

# แสดง/ซ่อนข้อความ OCR
show_ocr = st.checkbox("แสดงข้อความ OCR ที่ตรวจจับได้")

history = []
unique_slips = []
duplicates = []

# ฟังก์ชันแยกข้อมูลจากข้อความ OCR
def extract_transaction_data(text):
    date_pattern = r'\d{2}/\d{2}/\d{2}'
    time_pattern = r'\d{2}:\d{2}:\d{2}'
    amount_pattern = r'69,000\s*LAK|\d{1,3}(?:,\d{3})*\s*LAK'  # กรอง 69,000 LAK ก่อน
    ref_pattern = r'\d{14}'
    ticket_pattern = r'[A-Z0-9]{12}'
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
        'Ticket': ticket.group() if ticket else '',
        'Receiver': receiver.group().strip() if receiver else '',
        'Text': text
    }

# ฟังก์ชันตัดภาพเฉพาะบริเวณตัวแดง (จำนวนเงิน)
def crop_red_text_area(image):
    img = np.array(image)
    hsv = cv2.cvtColor(img, cv2.COLOR_RGB2HSV)
    lower_red = np.array([0, 50, 50])
    upper_red = np.array([10, 255, 255])
    mask = cv2.inRange(hsv, lower_red, upper_red)
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    for cnt in contours:
        x, y, w, h = cv2.boundingRect(cnt)
        if w > 40 and h > 20:
            cropped = img[y:y+h, x:x+w]
            return Image.fromarray(cropped)
    return image

# ฟังก์ชันสแกน QR code
def scan_qr(image):
    img = np.array(image.convert('RGB'))
    codes = decode(img)
    for code in codes:
        return code.data.decode('utf-8')
    return ''

if uploaded_files:
    for file in uploaded_files:
        image = Image.open(file)

        cropped_image = crop_red_text_area(image)
        text = pytesseract.image_to_string(cropped_image, config='--oem 3 --psm 6')
        full_text = pytesseract.image_to_string(image, config='--oem 3 --psm 6')
        qr_data = scan_qr(image)

        if show_ocr:
            st.markdown("#### OCR Text (ข้อความจากภาพ):")
            st.code(full_text, language='text')

        data = extract_transaction_data(full_text)
        data['QR'] = qr_data

        key = (data['Date'], data['Time'], data['Amount (LAK)'], data['Reference'], data['Ticket'])
        history.append(data)

        if key in [
            (d['Date'], d['Time'], d['Amount (LAK)'], d['Reference'], d['Ticket'])
            for d in unique_slips
        ]:
            duplicates.append(data)
        else:
            unique_slips.append(data)

    # แสดงผลลัพธ์
    if unique_slips:
        df = pd.DataFrame(unique_slips)
        df['Amount (LAK)'] = pd.to_numeric(df['Amount (LAK)'], errors='coerce')
        st.success(f"รวมยอดทั้งหมด: {df['Amount (LAK)'].sum():,.0f} LAK")
        st.markdown("### รายการสลิปที่ไม่ซ้ำ:")
        st.dataframe(df)

        buffer = io.BytesIO()
        df.to_excel(buffer, index=False)
        buffer.seek(0)

        st.download_button(
            label="ดาวน์โหลดไฟล์ Excel (ไม่ซ้ำ)",
            data=buffer,
            file_name="unique_slips.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    if duplicates:
        st.markdown("### รายการสลิปที่ตรวจพบว่าซ้ำ:")
        df_dup = pd.DataFrame(duplicates)
        st.dataframe(df_dup.style.apply(lambda x: ['background-color: red']*len(x), axis=1))

        buffer_dup = io.BytesIO()
        df_dup.to_excel(buffer_dup, index=False)
        buffer_dup.seek(0)

        st.download_button(
            label="ดาวน์โหลดไฟล์ Excel (ซ้ำ)",
            data=buffer_dup,
            file_name="duplicate_slips.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    # ประวัติทั้งหมด
    st.markdown("### ประวัติทั้งหมดของสลิป (รวมทั้งซ้ำและไม่ซ้ำ):")
    st.dataframe(pd.DataFrame(history))
