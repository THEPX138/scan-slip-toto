# ระบบสแกนสลิปโอนเงิน (เวอร์ชั่น 0.3.4) จากสลิป BCEL One
import streamlit as st
import pandas as pd
import pytesseract
from PIL import Image
import numpy as np
import io
import re
import cv2
import requests

# ===== CONFIG TELEGRAM =====
TELEGRAM_BOT_TOKEN = "7194336087:AAGSbq63qi4vpXJqZ2rwS940PVSnFWNHNtc"
TELEGRAM_CHAT_ID = "-4745577562"  # Group ID (use negative prefix for group)

def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    data = {"chat_id": TELEGRAM_CHAT_ID, "text": message}
    headers = {"Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"}
    requests.post(url, data=data, headers=headers)

def send_telegram_photo(image, caption=""):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
    buffered = io.BytesIO()
    image.save(buffered, format="JPEG")
    buffered.seek(0)
    files = {"photo": buffered}
    data = {"chat_id": TELEGRAM_CHAT_ID, "caption": caption}
    headers = {"Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"}
    requests.post(url, files=files, data=data, headers=headers)

# ===== STREAMLIT UI =====
st.set_page_config(page_title="ระบบสแกนสลิปโอนเงิน", layout="wide")
st.markdown("<h1 style='font-size: 2.5rem;'>ระบบสแกนสลิปโอนเงิน (เวอร์ชั่น 0.3.4) จากสลิป BCEL One</h1>", unsafe_allow_html=True)

uploaded_files = st.file_uploader("อัปโหลดสลิปภาพ (รองรับหลายไฟล์)", type=["jpg", "jpeg", "png"], accept_multiple_files=True)

show_ocr = st.checkbox("แสดงข้อความ OCR ทั้งหมด")

columns = ["Date", "Time", "Amount (LAK)", "Reference", "Sender", "Receiver"]
df_history = pd.DataFrame(columns=columns)
uploaded_hashes = set()
notified_hashes = set()
new_slip_count = 0

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

def read_qr_code(image_np):
    return ""  # ตัดฟังก์ชัน QR ออกในเวอร์ชันง่าย

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

    amount_match = re.search(r"\d{1,3}[,\d]{0,10}", red_text)
    amount = amount_match.group().replace(",", "") if amount_match else ""

    slip_key = f"{date.group() if date else ''}-{time.group() if time else ''}-{amount}-{reference.group() if reference else ''}"

    if slip_key in uploaded_hashes:
        st.warning(f"สลิปซ้ำ: {reference.group() if reference else 'N/A'}")
        if slip_key not in notified_hashes:
            send_telegram_message(f"🚨 พบสลิปซ้ำ: เลขอ้างอิง {reference.group() if reference else 'N/A'}")
            notified_hashes.add(slip_key)
        continue

    uploaded_hashes.add(slip_key)
    new_slip_count += 1

    row = {
        "Date": date.group() if date else "",
        "Time": time.group() if time else "",
        "Amount (LAK)": amount,
        "Reference": reference.group() if reference else "",
        "Sender": sender.group() if sender else "",
        "Receiver": receiver[1] if len(receiver) > 1 else ""
    }
    df_history.loc[len(df_history)] = row

    if slip_key not in notified_hashes:
        send_telegram_photo(image, caption=f"🧾 สลิปใหม่: {reference.group() if reference else 'ไม่มีเลขอ้างอิง'}")
        notified_hashes.add(slip_key)

    if show_ocr:
        st.subheader(f"OCR: {reference.group() if reference else 'N/A'}")
        st.code(text)

# ===== SUMMARY =====
if not df_history.empty:
    try:
        total = df_history["Amount (LAK)"].astype(str).str.replace(",", "").astype(float).sum()
        st.success(f"รวมยอดทั้งหมด: {int(total):,} LAK")
    except:
        st.warning("ไม่สามารถรวมยอดได้ เนื่องจากข้อมูลจำนวนเงินไม่ถูกต้องทั้งหมด")

    st.dataframe(df_history)

    buffer = io.BytesIO()
    df_history.to_excel(buffer, index=False)
    st.download_button("ดาวน์โหลดไฟล์ Excel", data=buffer.getvalue(), file_name="slip_summary.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

# ===== SEND TELEGRAM NOTICE ONCE =====
if new_slip_count > 0:
    send_telegram_message(f"📥 มีการอัปโหลดสลิปใหม่จำนวน {new_slip_count} รายการ")
