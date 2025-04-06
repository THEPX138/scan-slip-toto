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
import os

# ========== CONFIG ==========
TELEGRAM_BOT_TOKEN = "ใส่โทเคนบอทของคุณ"
TELEGRAM_CHAT_ID = "ใส่ chat_id กลุ่มหรือบุคคล"

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

# ========== Streamlit UI ==========
st.set_page_config(page_title="ระบบสแกนสลิปโอนเงิน", layout="wide")
st.title("ระบบสแกนสลิปโอนเงิน (เวอร์ชั่น 0.3.3) จากสลิป BCEL One")
uploaded_files = st.file_uploader("อัปโหลดสลิปภาพ (รองรับหลายไฟล์)", type=["jpg", "jpeg", "png"], accept_multiple_files=True)
show_ocr = st.checkbox("แสดงข้อความ OCR ทั้งหมด")

columns = ["Date", "Time", "Amount (LAK)", "Reference", "Sender", "Receiver"]
df_history = pd.DataFrame(columns=columns)
uploaded_hashes = set()
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

    amount_match = re.search(r"\d{1,3}[,\d]{0,10}", red_text)
    amount = amount_match.group().replace(",", "") if amount_match else ""

    slip_key = f"{date.group() if date else ''}-{time.group() if time else ''}-{amount}-{reference.group() if reference else ''}"
    if slip_key in uploaded_hashes:
        st.warning(f"สลิปซ้ำ: {reference.group() if reference else 'N/A'}")
        send_telegram_message(f"🚨 พบสลิปซ้ำ: เลขอ้างอิง {reference.group() if reference else 'N/A'}")
        continue

    uploaded_hashes.add(slip_key)
    new_slip_count += 1

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

# แสดงผลรวม
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

# แจ้ง Telegram เมื่ออัปโหลดครบ
if new_slip_count > 0:
    send_telegram_message(f"📥 มีการอัปโหลดสลิปใหม่จำนวน {new_slip_count} รายการ")
