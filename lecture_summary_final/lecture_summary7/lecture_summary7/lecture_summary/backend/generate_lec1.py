import os
from dotenv import load_dotenv
from google import genai
import sys

# Ensure console output uses UTF-8 (avoids Windows cp1252 errors)
try:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

# تحميل متغيرات البيئة من .env
load_dotenv()

# قراءة الـ API Key
api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")

if not api_key:
    raise RuntimeError(
        "خطأ: ما في API key. ضعي GEMINI_API_KEY في ملف .env أو عيّني المتغير في النظام."
    )

# تهيئة عميل Gemini
client = genai.Client(api_key=api_key)

# قراءة نص المحاضرة
with open("input.txt", "r", encoding="utf-8") as f:
    short_text = f.read()

# إعداد Prompt قوي ومنسق لتنظيم النص كملاحظات محاضرة
prompt = f"""
أنت مساعد ذكي لتنظيم الملاحظات الدراسية. حول النص التالي إلى ملاحظات محاضرة منظمة بحيث:

1. تقسيم النص لأقسام وفصول
2. وضع عنوان واضح لكل قسم
3. كتابة نقاط أساسية لكل فكرة
4. إضافة أمثلة وشروح عند الحاجة
5. الحفاظ على الكلمات الإنجليزية كما هي
6. صياغة النص بشكل سلس وسهل للدراسة

النص الأصلي:
{short_text}

المخرجات المطلوبة: ملاحظات منظمة وجاهزة للدراسة
"""

# توليد النص النهائي
try:
    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=prompt
    )
    final_text = response.text or str(response)
except Exception as e:
    raise RuntimeError(f"خطأ أثناء توليد النص: {e}")

# حفظ الناتج في output.txt
with open("output.txt", "w", encoding="utf-8") as f:
    f.write(final_text)

print("تمت المعالجة. الملف الناتج موجود باسم: output.txt")