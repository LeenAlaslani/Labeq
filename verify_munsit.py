"""Generate one real short clip with Maha, then listen locally on macOS."""
import asyncio
import base64
from pathlib import Path

from app import munsit_speak, MUNSIT_API_KEY, MUNSIT_VOICE_ID

if not MUNSIT_API_KEY or not MUNSIT_VOICE_ID:
    raise SystemExit('إعداد مها غير مكتمل. نفذي: python setup_munsit.py')

print('منصت قد يخصم رصيدًا بحسب طول النص. هذا الاختبار يولد جملة قصيرة واحدة.')
if input('هل تبدئين الاختبار؟ اكتبي نعم: ').strip() != 'نعم':
    raise SystemExit('تم الإلغاء قبل طلب الصوت.')

text = 'يا هلا، أنا لبِق! وش تحبين أناديك؟'
result = asyncio.run(munsit_speak(text))
audio = base64.b64decode(result['audio_base64'])
if not audio.startswith(b'RIFF') or len(audio) < 500:
    raise SystemExit('الاستجابة ليست ملف WAV صالحًا.')
output = Path(__file__).resolve().parent / 'maha_test.wav'
output.write_bytes(audio)
print('نجح إنشاء صوت جديد بصوت مها:', output.name)
print('مزامنة النص:', result['sync_mode'])
print('شغّليه على الماك: afplay maha_test.wav')
print('ثم لتشغيل الموقع: python -m uvicorn app:app --reload --port 8001')
