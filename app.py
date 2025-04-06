ระบบแสกนสลิปโอนเงิน (เวอร์ชัน 0.1) จากสลิป BCEL One

import streamlit as st import pandas as pd import pytesseract from PIL import Image import re import os

หากใช้บน Windows ให้กำหนด path ของ tesseract

pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

st.set_page_config(page_title="ระบบแสกนสลิปโอนเงิน", layout="wide") st.title("ระบบแสกนสลิปโอนเงิน")

uploaded_files = st.file_uploader("อัปโหลดสลิปภาพ (PNG, JPG)", accept_multiple_files=True, type=["png", "jpg", "jpeg"]) show_ocr = st.checkbox("แสดงข้อความ OCR ทั้งหมด")

สำหรับเก็บผลลัพธ์

results = [] history_file = "history.csv" if os.path.exists(history_file): df_history = pd.read_csv(history_file) else: df_history = pd.DataFrame(columns=["Date", "Time", "Amount (LAK)", "Reference", "Ticket", "Receiver", "Text"])

def extract_info(image): text = pytesseract.image_to_string(image, lang='eng+lao') date_match = re.search(r"(\d{2}/\d{2}/\d{2})", text) time_match = re.search(r"(\d{2}:\d{2}:\d{2})", text) amount_match = re.search(r"(\d{1,3}(,\d{3}))\sLAK", text) reference_match = re.search(r"(\d{15,20})", text) ticket_match = re.search(r"[A-Z0-9]{10,}", text) receiver_match = re.search(r"KONGMANY SOMSAMONE MR", text, re.IGNORECASE)

return {
    "Date": date_match.group(1) if date_match else "",
    "Time": time_match.group(1) if time_match else "",
    "Amount (LAK)": amount_match.group(1).replace(",", "") if amount_match else "",
    "Reference": reference_match.group(1) if reference_match else "",
    "Ticket": ticket_match.group(0) if ticket_match else "",
    "Receiver": "KONGMANY SOMSAMONE MR" if receiver_match else "",
    "Text": text
}

for uploaded_file in uploaded_files: image = Image.open(uploaded_file) info = extract_info(image)

# ตรวจสอบข้อมูลซ้ำจากประวัติ
duplicate = df_history[(df_history['Date'] == info['Date']) &
                       (df_history['Time'] == info['Time']) &
                       (df_history['Amount (LAK)'] == info['Amount (LAK)']) &
                       (df_history['Ticket'] == info['Ticket'])]

if not duplicate.empty:
    st.error("พบข้อมูลซ้ำ!")
else:
    st.success("สลิปใหม่ ตรวจสอบแล้วไม่ซ้ำ")

if show_ocr:
    with st.expander(f"OCR Text: {uploaded_file.name}"):
        st.text(info['Text'])

results.append(info)

แสดงผลรวมและตาราง

if results: df = pd.DataFrame(results) st.subheader("รายการสลิปที่อัปโหลด") st.dataframe(df)

# อัปเดตประวัติ
df_history = pd.concat([df_history, df], ignore_index=True)
df_history.drop_duplicates(subset=["Date", "Time", "Amount (LAK)", "Ticket"], keep="first", inplace=True)
df_history.to_csv(history_file, index=False)

st.download_button("ดาวน์โหลด Excel", data=df.to_csv(index=False).encode('utf-8'), file_name="slips.csv", mime="text/csv")

st.subheader("ประวัติสลิปทั้งหมด")
st.dataframe(df_history)
