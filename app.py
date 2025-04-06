# ระบบสแกนสลิปโอนเงิน (เวอร์ชั่น 0.3.3) สำหรับ Streamlit Cloud
import streamlit as st
import pandas as pd
import pytesseract
from PIL import Image
import re
import io

st.set_page_config(page_title="ระบบสแกนสลิปโอนเงิน", layout="wide")
st.title("ระบบสแกนสลิปโอนเงิน (เวอร์ชั่น 0.3.3) จากสลิป BCEL One")

uploaded_files = st.file_uploader("อัปโหลดสลิปภาพ (รองรับหลายไฟล์)", type=["jpg", "jpeg", "png"], accept_multiple_files=True)
show_ocr = st.checkbox("แสดงข้อความ OCR ทั้งหมด")

columns = ["Date", "Time", "Amount (LAK)", "Reference", "Sender", "Receiver"]
df_history = pd.DataFrame(columns=columns)
uploaded_hashes = set()

# ประมวลผลแต่ละสลิป
for file in uploaded_files:
    image = Image.open(file)
    text = pytesseract.image_to_string(image, lang="eng")

    # ดึงข้อมูลด้วย regex
    date = re.search(r"\d{2}/\d{2}/\d{2,4}", text)
    time = re.search(r"\d{2}:\d{2}:\d{2}", text)
    amount_match = re.search(r"(\d{1,3}(,\d{3})+)\s?LAK", text)
    amount = amount_match.group(1).replace(",", "") if amount_match else ""

    reference = re.search(r"\d{10,20}", text)
    sender = re.search(r"From account\s+([A-Z ]+MR|MS)", text)
    receiver = re.search(r"To account\s+([A-Z ]+MR|MS)", text)


    slip_key = f"{date.group() if date else ''}-{time.group() if time else ''}-{amount}-{reference.group() if reference else ''}"
    if slip_key in uploaded_hashes:
        st.warning(f"สลิปซ้ำ: {reference.group() if reference else 'N/A'}")
        continue
    uploaded_hashes.add(slip_key)

    df_history.loc[len(df_history)] = [
        date.group() if date else "",
        time.group() if time else "",
        amount,
        reference.group() if reference else "",
        sender.group().strip() if sender else "",
        receiver.group().strip() if receiver else ""
    ]

    if show_ocr:
        st.subheader(f"OCR สลิป: {reference.group() if reference else 'N/A'}")
        st.code(text)

# แสดงผลลัพธ์
if not df_history.empty:
    try:
    df_amount = pd.to_numeric(df_history["Amount (LAK)"].str.replace(",", ""), errors="coerce")
    total = df_amount.sum()
    st.success(f"รวมยอดทั้งหมด: {int(total):,} LAK")
except:
    st.warning("ไม่สามารถรวมยอดได้ เนื่องจากข้อมูลจำนวนเงินไม่ถูกต้องทั้งหมด")

    st.dataframe(df_history)

    buffer = io.BytesIO()
    df_history.to_excel(buffer, index=False)
    st.download_button("ดาวน์โหลดไฟล์ Excel", data=buffer.getvalue(), file_name="slip_summary.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
