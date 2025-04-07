# ระบบสแกนสลิปโอนเงิน (เวอร์ชั่น 0.3.9) จากสลิป BCEL One

import streamlit as st
import pandas as pd
import pytesseract
from PIL import Image
import re
import os
import io
import numpy as np
import cv2
import requests
import json

from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

# ===== CONFIG =====
print("📂 Folder ID คือ: 1LdK4GBanj3EhFNfn0QcPeC7QUUGrSRNW")
GDRIVE_FOLDER_ID = "1ldK4GBanj3EhFhFNfN0QcPeC7QUUGrSRNW"

# โหลด service account credentials จากไฟล์ JSON
with open("scanslipuploader-df6c15243236.json") as source:
    info = json.load(source)
    credentials = Credentials.from_service_account_info(info, scopes=["https://www.googleapis.com/auth/drive.file"])
drive_service = build("drive", "v3", credentials=credentials)

# ========== ฟังก์ชัน OCR และวิเคราะห์ภาพ ==========
def extract_ocr_text(image):
    text = pytesseract.image_to_string(image, lang='eng+lao')
    return text

def extract_amount_by_color(image):
    hsv = cv2.cvtColor(image, cv2.COLOR_RGB2HSV)
    lower_red = np.array([0, 100, 100])
    upper_red = np.array([10, 255, 255])
    mask = cv2.inRange(hsv, lower_red, upper_red)
    result = cv2.bitwise_and(image, image, mask=mask)
    gray = cv2.cvtColor(result, cv2.COLOR_RGB2GRAY)
    text = pytesseract.image_to_string(gray, config="--psm 6")
    return text

def extract_info_from_text(text):
    date_match = re.search(r"(\d{2}/\d{2}/\d{4})", text)
    time_match = re.search(r"(\d{2}:\d{2}:\d{2})", text)
    amount_match = re.search(r"([\d,]+\.\d{2})", text)
    ref_match = re.search(r"(Ref|REFERENCE|Ticket No)[^\d]*(\d+)", text, re.IGNORECASE)
    receiver_match = re.search(r"(to|TO):?\s*([\w\s]+)", text)

    return {
        "Date": date_match.group(1) if date_match else "",
        "Time": time_match.group(1) if time_match else "",
        "Amount (LAK)": amount_match.group(1).replace(",", "") if amount_match else "",
        "Reference": ref_match.group(2) if ref_match else "",
        "Receiver": receiver_match.group(2).strip() if receiver_match else "",
        "Full Text": text
    }

def upload_to_drive(file_bytes, filename, folder_id):
    file_metadata = {"name": filename, "parents": [folder_id]}
    media = MediaIoBaseUpload(io.BytesIO(file_bytes), mimetype="image/jpeg")
    file = drive_service.files().create(body=file_metadata, media_body=media, fields='id').execute()
    return file.get("id")

def notify_telegram(message, image_bytes=None):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    data = {"chat_id": TELEGRAM_CHAT_ID, "text": message}
    requests.post(url, data=data)

    if image_bytes:
        photo_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
        files = {"photo": image_bytes}
        data = {"chat_id": TELEGRAM_CHAT_ID}
        requests.post(photo_url, data=data, files=files)

# ========== UI ==========
st.set_page_config(page_title="ระบบสแกนสลิป", layout="wide")
st.title("ระบบสแกนสลิปโอนเงิน (เวอร์ชั่น 0.3.9) จากสลิป BCEL One")
uploaded_files = st.file_uploader("อัปโหลดสลิปภาพ", accept_multiple_files=True, type=["jpg", "jpeg", "png"])
show_ocr = st.checkbox("แสดงข้อความ OCR ทั้งหมด")

if uploaded_files:
    results = []
    st.info(f"คุณอัปโหลด {len(uploaded_files)} ไฟล์")
    for file in uploaded_files:
        image = Image.open(file).convert("RGB")
        image_np = np.array(image)
        ocr_text = extract_ocr_text(image_np)
        red_amount_text = extract_amount_by_color(image_np)

        info = extract_info_from_text(ocr_text + "\n" + red_amount_text)
        results.append(info)

        # อัปโหลดเข้า Google Drive
        file_bytes = file.read()
        drive_id = upload_to_drive(file_bytes, file.name, GDRIVE_FOLDER_ID)

        # ส่งแจ้งเตือน Telegram
        message = f"🧾 สลิปใหม่:\n- 📅 {info['Date']} {info['Time']}\n- 💸 {info['Amount (LAK)']} LAK\n- 🆔 Ref: {info['Reference']}\n- 👤 ผู้รับ: {info['Receiver']}"
        notify_telegram(message, image_bytes=file_bytes)

        # แสดงผล
        st.image(image, caption=file.name, use_column_width=True)
        st.markdown(f"**วันที่:** {info['Date']}  \n**เวลา:** {info['Time']}  \n**จำนวนเงิน:** {info['Amount (LAK)']} LAK  \n**อ้างอิง:** {info['Reference']}  \n**ผู้รับ:** {info['Receiver']}")

        if show_ocr:
            st.code(info["Full Text"])

    df = pd.DataFrame(results)
    st.dataframe(df)
