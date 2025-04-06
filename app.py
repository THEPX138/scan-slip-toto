import streamlit as st
import pandas as pd
import pytesseract
from PIL import Image
import re
import io
import os

# ตั้งค่า path ของ Tesseract
if os.name == 'nt':
    pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
else:
    pytesseract.pytesseract_cmd = 'tesseract'

# ตั้งค่าหน้าเว็บ
st.set_page_config(page_title="ระบบสแกนสลิป & สรุปยอด", layout="wide")
st.title("ระบบสแกนสลิปโอนเงิน")

# ฟังก์ชันดึงข้อมูลจากข้อความ OCR
def extract_transaction_data(text):
    date_pattern = r'\
