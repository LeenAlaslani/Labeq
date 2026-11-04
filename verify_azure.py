"""Validate Azure's real Zariyah TTS with one short network request."""
import os
from pathlib import Path
from xml.sax.saxutils import escape

import httpx
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / '.env', override=True)
region = os.getenv('AZURE_SPEECH_REGION', '').strip().lower()
key = os.getenv('AZURE_SPEECH_KEY', '').strip()
if not key or not region:
    raise SystemExit('المفتاح أو المنطقة غير موجودة. نفذي أولًا: python setup_azure.py')

text = 'يا هلا! أنا لبق، وش تحبين أناديك؟'
ssml = ("<speak version='1.0' xml:lang='ar-SA'>"
        "<voice name='ar-SA-ZariyahNeural'>"
        f'{escape(text)}'
        '</voice></speak>')
url = f'https://{region}.tts.speech.microsoft.com/cognitiveservices/v1'
print('أختبر الصوت السعودي زاريّة عبر Azure...')
try:
    with httpx.Client(timeout=45) as client:
        res = client.post(url, headers={
            'Ocp-Apim-Subscription-Key': key,
            'Content-Type': 'application/ssml+xml',
            'X-Microsoft-OutputFormat': 'audio-24khz-48kbitrate-mono-mp3',
            'User-Agent': 'LABEQ-Showcase',
        }, content=ssml.encode('utf-8'))
except httpx.HTTPError as exc:
    raise SystemExit(f'تعذر الاتصال بـ Azure: {type(exc).__name__}. تأكدي من الإنترنت والـ Region.') from exc

if res.status_code != 200:
    reason = {401: 'راجعي المفتاح KEY 1.', 403: 'تحققي من صلاحيات المورد وتفعيله.',
              404: 'راجعي Region المختارة.', 429: 'وصلتِ إلى حد الاستخدام أو تحتاجين مراجعة الخطة.'}.get(
        res.status_code, 'افتحي Azure وتحققي من المورد والمنطقة والاشتراك.')
    raise SystemExit(f'فشل اختبار Azure (HTTP {res.status_code}). {reason}')
if len(res.content) < 256:
    raise SystemExit('الخدمة ردت لكن ملف الصوت فارغ أو غير صالح.')
file = ROOT / 'zariyah_test.mp3'
file.write_bytes(res.content)
print('نجح الاختبار! تم إنشاء ملف صوت حقيقي: zariyah_test.mp3')
print('شغّليه على الماك بالأمر: afplay zariyah_test.mp3')
print('الآن لتشغيل الموقع: python -m uvicorn app:app --reload --port 8000')
