from PIL import Image
import pytesseract

# ตั้งค่า path ของ tesseract.exe
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# โหลดภาพ
image = Image.open("photo_2025-04-06_15-40-36.jpg")

# ดึงข้อความจากภาพ
text = pytesseract.image_to_string(image, lang='eng+lao')

# แสดงผล
print("ข้อความที่อ่านได้จากภาพ:")
print(text)
