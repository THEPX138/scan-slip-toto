import streamlit as st
import pandas as pd
import pytesseract
from PIL import Image
import numpy as np
import cv2
import io
import os

# กำหนด path Tesseract
if os.name == 'nt':
    pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

st.set_page_config(page_title="Scan Slip BCEL", layout="wide")
st.title("ระบบสแกนจำนวนเงินจากสลิป BCELOne (อ่านตัวหนังสือสีแดง)")

uploaded_files = st.file_uploader("อัปโหลดสลิป (JPG/PNG)", type=["jpg", "jpeg", "png"], accept_multiple_files=True)

results = []

def extract_red_amount(img):
    # ครอบเฉพาะตำแหน่ง "จำนวนเงิน" ตัวแดงในภาพ (ต้องปรับให้เหมาะกับ resolution)
    cropped = img[530:580, 160:430]  # ปรับตำแหน่งให้ตรงภาพจริง

    # แปลงเป็น grayscale และปรับ contrast
    gray = cv2.cvtColor(cropped, cv2.COLOR_BGR2GRAY)
    enhanced = cv2.convertScaleAbs(gray, alpha=2.5, beta=0)

    pil_img = Image.fromarray(enhanced)

    # OCR อ่านตัวอักษร
    raw_text = pytesseract.image_to_string(pil_img, config='--oem 3 --psm 6')
    
    # หาเฉพาะจำนวนเงิน
    import re
    match = re.search(r'(\d{1,3}(?:,\d{3})*)', raw_text)
    amount = match.group(1).replace(",", "") if match else ""

    return raw_text.strip(), amount

if uploaded_files:
    for file in uploaded_files:
        # ใช้ OpenCV อ่าน
        file_bytes = np.asarray(bytearray(file.read()), dtype=np.uint8)
        image = cv2.imdecode(file_bytes, 1)

        ocr_text, amount = extract_red_amount(image)
        results.append({
            'Filename': file.name,
            'Amount (LAK)': amount,
            'Raw OCR Text': ocr_text
        })

    df = pd.DataFrame(results)

    st.success(f"รวมยอดทั้งหมด: {df['Amount (LAK)'].astype(float).sum():,.0f} LAK")
    st.dataframe(df)

    # ดาวน์โหลด
    buffer = io.BytesIO()
    df.to_excel(buffer, index=False)
    buffer.seek(0)
    st.download_button("ดาวน์โหลด Excel", buffer, file_name="summary.xlsx")
