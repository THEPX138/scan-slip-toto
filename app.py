# ระบบสแกนสลิปโอนเงิน (เวอร์ชั่น 0.3.3) จากสลิป BCEL One
import streamlit as st
import pandas as pd
import pytesseract
from PIL import Image
import numpy as np
import io
import re
import cv2
import requests

# ===== CONFIG =====
TELEGRAM_BOT_TOKEN = "7194336087:AAGSbq63qi4vpXJqZ2rwS940PVSnFWNHNtc"
TELEGRAM_CHAT_ID = "-4745577562"

def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": TELEGRAM_CHAT_ID, "text": message})

def send_telegram_photo(image, caption=""):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
    buffered = io.BytesIO()
    image.save(buffered, format="JPEG")
    buffered.seek(0)
    files = {"photo": buffered}
    requests.post(url, files=files, data={"chat_id": TELEGRAM_CHAT_ID, "caption": caption})

# ===== Streamlit UI =====
st.set_page_config(page_title="ระบบสแกนสลิปโอนเงิน", layout="wide")
st.title("ระบบสแกนสลิปโอนเงิน (เวอร์ชั่น 0.3.3) จากสลิป BCEL One")

uploaded_files = st.file_uploader(
    "อัปโหลดสลิปภาพ (รองรับหลายไฟล์)", 
    type=["jpg", "jpeg", "png"], 
    accept_multiple_files=True,
    label_visibility="collapsed"  # << ซ่อนชื่อไฟล์
)

show_ocr = st.checkbox("แสดงข้อความ OCR ทั้งหมด")

columns = ["Date", "Time", "Amount (LAK)", "Reference", "Sender", "Receiver", "QR Data"]
df_history = pd.DataFrame(columns=columns)
uploaded_hashes = set()

def extract_amount_region(image):
    img_np = np.array(image)
    hsv = cv2.cvtColor(img_np, cv2.COLOR_RGB2HSV)
    lower_red = np.array([0, 100, 100])
    upper_red = np.array([10, 255, 255])
    mask = cv2.inRange(hsv, lower_red, upper_red)
    result = cv2.bitwise_and(img_np, img_np, mask=mask)
    gray = cv2.cvtColor(result, cv2.COLOR_RGB2GRAY)
    _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return Image.fromarray(thresh)

def read_qr_code(img_np):
    return ""  # Streamlit Cloud ไม่รองรับ pyzbar, placeholder ไว้ก่อน

for file in uploaded_files:
    image = Image.open(file)
    text = pytesseract.image_to_string(image, lang='eng+lao')

    red_area = extract_amount_region(image)
    red_text = pytesseract.image_to_string(red_area, config='--psm 6 digits')

    date = re.search(r"\d{2}/\d{2}/\d{2,4}", text)
    time = re.search(r"\d{2}:\d{2}:\d{2}", text)
    reference = re.search(r"\d{15,20}", text)
    sender = re.search(r"[A-Z ]+MS|MR", text)
    receiver = re.findall(r"[A-Z ]+MR|MS", text)
    qr_data = read_qr_code(np.array(image))

    amount_match = re.search(r"\d{1,3}(?:,\d{3})*", red_text)
    amount = amount_match.group().replace(",", "") if amount_match else ""

    sent_slips = set()  # เก็บ hash ของ slip ที่เคยส่งแล้ว

...

slip_key = f"{date.group() if date else ''}-{time.group() if time else ''}-{amount}-{reference.group() if reference else ''}"
slip_hash = hashlib.md5(slip_key.encode()).hexdigest()

if slip_hash in uploaded_hashes:
    st.warning(f"สลิปซ้ำ: {reference.group() if reference else 'N/A'}")
    
   for file in uploaded_files:
    ...
    if slip_key in uploaded_hashes:
        st.warning(f"สลิปซ้ำ: {reference.group() if reference else 'N/A'}")
        if slip_key not in notified_hashes:
            send_telegram_message(f"🚨 พบสลิปซ้ำ: เลขอ้างอิง {reference.group() if reference else 'N/A'}")
            notified_hashes.add(slip_key)
        continue  # ✅ ตรงนี้ต้องอยู่ใน for-loop เท่านั้น



    uploaded_hashes.add(slip_key)

    row = {
        "Date": date.group() if date else "",
        "Time": time.group() if time else "",
        "Amount (LAK)": amount,
        "Reference": reference.group() if reference else "",
        "Sender": sender.group() if sender else "",
        "Receiver": receiver[1] if len(receiver) > 1 else "",
        "QR Data": qr_data
    }
    df_history.loc[len(df_history)] = row

    send_telegram_photo(image, caption=f"🧾 สลิปใหม่: {reference.group() if reference else 'ไม่มีเลขอ้างอิง'}")

    if show_ocr:
        st.subheader(f"OCR: {reference.group() if reference else 'N/A'}")
        st.code(text)

# ===== สรุปยอดและดาวน์โหลด =====
if not df_history.empty:
    try:
        total = df_history["Amount (LAK)"].astype(str).str.replace(",", "").astype(float).sum()
        st.success(f"รวมยอดทั้งหมด: {int(total):,} LAK")
    except:
        st.warning("ไม่สามารถรวมยอดได้ เนื่องจากข้อมูลจำนวนเงินไม่ถูกต้องทั้งหมด")

    st.dataframe(df_history)

    buffer = io.BytesIO()
    df_history.to_excel(buffer, index=False)
    st.download_button(
        "ดาวน์โหลดไฟล์ Excel", 
        data=buffer.getvalue(),
        file_name="slip_summary.xlsx", 
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
