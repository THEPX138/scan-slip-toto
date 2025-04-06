import streamlit as st
import pandas as pd
import pytesseract
from PIL import Image
import re
import os
from datetime import datetime

# ตั้งค่า path ของ Tesseract OCR (เฉพาะ Windows)
pytesseract.pytesseract.tesseract_cmd = r"C:\\Program Files\\Tesseract-OCR\\tesseract.exe"

st.set_page_config(page_title="ระบบสแกนสลิปโอนเงิน V1", layout="wide")
st.title("📤 ระบบสแกนสลิปโอนเงิน (เวอร์ชั่น 0.1) จากสลิป BCEL One")

uploaded_file = st.file_uploader("อัปโหลดสลิป PNG หรือ JPG", type=["png", "jpg", "jpeg"])
show_ocr = st.checkbox("📄 แสดงข้อความ OCR ทั้งหมด")

history_file = "history.csv"
columns = ["Date", "Time", "Amount (LAK)", "Reference", "Ticket", "Receiver", "Text"]

if os.path.exists(history_file):
    df_history = pd.read_csv(history_file)
else:
    df_history = pd.DataFrame(columns=columns)

def extract_info(image):
    text = pytesseract.image_to_string(image, lang='eng+lao')

    # ดึงจำนวนเงินที่เป็นตัวหนังสือสีแดง เช่น "69,000 LAK"
    amount_match = re.search(r"(\d{1,3}(,\d{3})+)\s?LAK", text)
    amount = amount_match.group(1).replace(",", "") if amount_match else ""

    date_match = re.search(r"(\d{2}/\d{2}/\d{2})", text)
    time_match = re.search(r"(\d{2}:\d{2}:\d{2})", text)
    ref_match = re.search(r"(\d{12,})", text)
    ticket_match = re.search(r"Ticket\s*([A-Z0-9]{10,})", text, re.IGNORECASE)
    receiver_match = re.search(r"([A-Z ]+SOMSAMONE MR)", text)

    return {
        "Date": date_match.group(1) if date_match else "",
        "Time": time_match.group(1) if time_match else "",
        "Amount (LAK)": amount,
        "Reference": ref_match.group(1) if ref_match else "",
        "Ticket": ticket_match.group(1) if ticket_match else "",
        "Receiver": receiver_match.group(1).strip() if receiver_match else "",
        "Text": text.strip()
    }

if uploaded_file:
    image = Image.open(uploaded_file)
    info = extract_info(image)

    # ตรวจสอบซ้ำ
    is_duplicate = False
    if not df_history.empty:
        match = df_history[
            (df_history["Date"] == info["Date"]) &
            (df_history["Time"] == info["Time"]) &
            (df_history["Amount (LAK)"] == info["Amount (LAK)"]) &
            (df_history["Ticket"] == info["Ticket"])
        ]
        is_duplicate = not match.empty

    if show_ocr:
        with st.expander("🔍 ข้อความที่อ่านได้จาก OCR"):
            st.text(info["Text"])

    st.subheader("📊 ผลการสแกน:")
    row_style = "background-color:#FFCCCC;" if is_duplicate else "background-color:#E8FFE8;"
    st.markdown(
        f"""
        <table style='width:100%; border:1px solid #ccc; {row_style} padding:10px'>
            <tr><td><b>วันที่</b></td><td>{info['Date']}</td></tr>
            <tr><td><b>เวลา</b></td><td>{info['Time']}</td></tr>
            <tr><td><b>จำนวนเงิน</b></td><td>{info['Amount (LAK)']} LAK</td></tr>
            <tr><td><b>Reference</b></td><td>{info['Reference']}</td></tr>
            <tr><td><b>Ticket</b></td><td>{info['Ticket']}</td></tr>
            <tr><td><b>ผู้รับ</b></td><td>{info['Receiver']}</td></tr>
        </table>
        """, unsafe_allow_html=True
    )

    # บันทึกลง CSV
    df_history = pd.concat([df_history, pd.DataFrame([info])], ignore_index=True)
    df_history.to_csv(history_file, index=False)

    # แสดงประวัติ
    st.subheader("🕘 ประวัติการอัปโหลดสลิปทั้งหมด")
    st.dataframe(df_history)

    # ปุ่มดาวน์โหลด
    output_excel = "สรุปรายการสลิป.xlsx"
    df_history.to_excel(output_excel, index=False)
    with open(output_excel, "rb") as f:
        st.download_button("📥 ดาวน์โหลด Excel", f, file_name=output_excel)
