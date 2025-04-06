# ระบบสแกนสลิปโอนเงิน (เวอร์ชั่น 0.3.8) จากสลิป BCEL One
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
    try:
        requests.post(url, data={"chat_id": TELEGRAM_CHAT_ID, "text": message})
    except Exception as e:
        st.error(f"ส่งข้อความ Telegram ล้มเหลว: {e}")

def send_telegram_photo(image, caption=""):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
    buffered = io.BytesIO()
    image.save(buffered, format="JPEG")
    buffered.seek(0)
    files = {"photo": buffered}
    try:
        requests.post(url, files=files, data={"chat_id": TELEGRAM_CHAT_ID, "caption": caption})
    except Exception as e:
        st.error(f"ส่งภาพ Telegram ล้มเหลว: {e}")

# ===== Session State =====
if "notified_slips" not in st.session_state:
    st.session_state.notified_slips = set()
if "duplicate_slips" not in st.session_state:
    st.session_state.duplicate_slips = set()

# ===== UI =====
st.set_page_config(page_title="ระบบสแกนสลิปโอนเงิน", layout="wide")
st.title("ระบบสแกนสลิปโอนเงิน (เวอร์ชั่น 0.3.8) จากสลิป BCEL One")

uploaded_files = st.file_uploader("อัปโหลดสลิปภาพ (รองรับหลายไฟล์)", type=["jpg", "jpeg", "png"], accept_multiple_files=True)
show_ocr = st.checkbox("แสดงข้อความ OCR ทั้งหมด")

columns = ["Date", "Time", "Amount (LAK)", "Reference", "Sender", "Receiver", "QR Data"]
df_history = pd.DataFrame(columns=columns)
session_hashes = set()

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
    return ""

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

    slip_key = f"{date.group() if date else ''}-{time.group() if time else ''}-{amount}-{reference.group() if reference else ''}"

    # ตรวจสอบสลิปซ้ำจาก session
    is_duplicate = slip_key in st.session_state.duplicate_slips

    if is_duplicate:
        st.warning(f"สลิปซ้ำ: {reference.group() if reference else 'N/A'}")
        if slip_key not in st.session_state.notified_slips:
            send_telegram_message(f"🚨 พบสลิปซ้ำ: เลขอ้างอิง {reference.group() if reference else 'N/A'}")
            st.session_state.notified_slips.add(slip_key)
        continue
    else:
        st.session_state.duplicate_slips.add(slip_key)

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

    if slip_key not in st.session_state.notified_slips:
        send_telegram_photo(image, caption=f"🧾 สลิปใหม่: {reference.group() if reference else 'ไม่มีเลขอ้างอิง'}")
        st.session_state.notified_slips.add(slip_key)

    if show_ocr:
        st.subheader(f"OCR: {reference.group() if reference else 'N/A'}")
        st.code(text)

# ===== สรุปยอด =====
if not df_history.empty:
    try:
        total = df_history["Amount (LAK)"].astype(str).str.replace(",", "").astype(float).sum()
        st.success(f"รวมยอดทั้งหมด: {int(total):,} LAK")
    except:
        st.warning("ไม่สามารถรวมยอดได้ เพราะมีข้อมูลจำนวนเงินผิดพลาด")

    st.dataframe(df_history)

    buffer = io.BytesIO()
    df_history.to_excel(buffer, index=False)
    st.download_button("ดาวน์โหลด Excel", data=buffer.getvalue(), file_name="slip_summary.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
