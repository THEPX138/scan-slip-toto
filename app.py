import streamlit as st
import pandas as pd
import pytesseract
from PIL import Image
import re
import io
import os
from datetime import datetime

# ตั้งค่าหน้าเว็บ
st.set_page_config(page_title="ระบบสแกนสลิปโอนเงิน", layout="wide")
st.title("💸 ระบบสแกนสลิปโอนเงิน")

# ตั้ง path สำหรับ Windows (เปลี่ยนตามที่ติดตั้ง)
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# โหลดประวัติ (ถ้ามี)
@st.cache_data
def load_history():
    try:
        return pd.read_csv("upload_history.csv")
    except:
        return pd.DataFrame(columns=["Date", "Time", "Amount (LAK)", "Reference", "Ticket", "Receiver", "Text"])

# ฟังก์ชัน OCR และแยกข้อมูล
def extract_info(image):
    text = pytesseract.image_to_string(image, lang='eng+lao')
    
    # ดึงข้อมูล
    date_match = re.search(r'(\d{2}/\d{2}/\d{2})', text)
    time_match = re.search(r'(\d{2}:\d{2}:\d{2})', text)
    amount_match = re.search(r'69,000|[1-9]\d{0,2}(,\d{3})*\s?LAK', text)
    ref_match = re.search(r'\b(2025\d{10,})\b', text)
    ticket_match = re.search(r'Ticket\s+([A-Z0-9]+)', text, re.IGNORECASE)
    receiver_match = re.search(r'KONGMANY SOMSAMONE MR', text, re.IGNORECASE)

    date = date_match.group(1) if date_match else ""
    time = time_match.group(1) if time_match else ""
    amount = amount_match.group(0).replace("LAK", "").strip() if amount_match else ""
    amount = re.sub(r'[^\d]', '', amount)
    reference = ref_match.group(1) if ref_match else ""
    ticket = ticket_match.group(1) if ticket_match else ""
    receiver = receiver_match.group(0).upper() if receiver_match else ""

    return {
        "Date": date,
        "Time": time,
        "Amount (LAK)": amount,
        "Reference": reference,
        "Ticket": ticket,
        "Receiver": receiver,
        "Text": text
    }

# โหลดข้อมูล
uploaded_files = st.file_uploader("📤 อัปโหลดสลิปภาพ (PNG, JPG)", accept_multiple_files=True, type=["png", "jpg", "jpeg"])
show_ocr = st.checkbox("🔍 แสดงข้อความ OCR ทั้งหมด")

# โหลดประวัติ
df_history = load_history()

new_data = []
duplicate_data = []

for uploaded_file in uploaded_files:
    image = Image.open(uploaded_file)
    info = extract_info(image)

    # ตรวจสอบซ้ำ
    is_duplicate = (
        (df_history["Date"] == info["Date"]) &
        (df_history["Time"] == info["Time"]) &
        (df_history["Amount (LAK)"] == info["Amount (LAK)"]) &
        (df_history["Ticket"] == info["Ticket"])
    ).any()

    if is_duplicate:
        duplicate_data.append(info)
    else:
        new_data.append(info)
        df_history.loc[len(df_history)] = info

# แสดงผล
if new_data:
    st.success(f"รวมยอดทั้งหมด: {sum(int(i['Amount (LAK)']) for i in new_data):,} LAK")
    st.subheader("✅ รายการสลิปที่ไม่ซ้ำ:")
    df_new = pd.DataFrame(new_data)
    st.dataframe(df_new)
    st.download_button("📥 ดาวน์โหลด Excel (ไม่ซ้ำ)", df_new.to_csv(index=False).encode(), file_name="non_duplicates.csv")

if duplicate_data:
    st.error(f"🔴 พบสลิปซ้ำจำนวน {len(duplicate_data)} รายการ")
    st.subheader("❌ รายการสลิปที่ตรวจพบว่าซ้ำ:")
    df_dup = pd.DataFrame(duplicate_data)
    st.dataframe(df_dup.style.applymap(lambda x: 'color: red', subset=pd.IndexSlice[:, ["Amount (LAK)"]]))
    st.download_button("📥 ดาวน์โหลด Excel (ซ้ำ)", df_dup.to_csv(index=False).encode(), file_name="duplicates.csv")

if not df_history.empty:
    st.subheader("🕓 ประวัติทั้งหมดของสลิป (รวมทั้งซ้ำและไม่ซ้ำ):")
    st.dataframe(df_history)

# ปุ่มดูข้อความ OCR
if show_ocr:
    st.subheader("📝 ข้อความ OCR ที่สกัดจากภาพ")
    for row in df_history.itertuples():
        st.text_area(f"OCR Text (Ref: {row.Reference})", row.Text, height=120)

# บันทึกประวัติ
df_history.to_csv("upload_history.csv", index=False)
