"""Connect LABEQ to Munsit's public Maha voice. Does not synthesize paid audio."""
import os
import re
from getpass import getpass
from pathlib import Path
from urllib.parse import urlsplit

import httpx

ROOT = Path(__file__).resolve().parent
ENV = ROOT / '.env'
ENV_EXAMPLE = ROOT / '.env.example'
SAMPLE_FILENAME = 'IPK8qQ3F5NMiQLWFz1a83TG3.wav'
REGIONS = {
    '1': 'https://api.munsit.com/api/v1',
    '2': 'https://ae.api.faseeh.ai/api/v1',
}


def get_voice_list(payload):
    """Handle array and common wrapped API response structures."""
    if isinstance(payload, list):
        return [x for x in payload if isinstance(x, dict) and x.get('voice_id')]
    if isinstance(payload, dict):
        for k in ('data', 'voices', 'results', 'items', 'public_voices'):
            if k in payload:
                found = get_voice_list(payload[k])
                if found:
                    return found
    return []


def matches_sample(voice):
    sample = str(voice.get('sample_url') or '')
    return Path(urlsplit(sample).path).name.casefold() == SAMPLE_FILENAME.casefold()


def matches_maha(voice):
    name = str(voice.get('name') or '').strip().casefold()
    dialect = voice.get('dialect') or voice.get('dialects') or []
    if isinstance(dialect, str):
        dialect = [dialect]
    is_najdi = any(d.lower() in ('najdi', 'saudi', 'saudi_najdi') for d in dialect if isinstance(d, str))
    female = str(voice.get('gender') or '').casefold() in ('female', 'woman', 'f', '')
    return name in ('maha', 'مها') and is_najdi and female


def select_maha(voices):
    exact = [x for x in voices if matches_sample(x)]
    if len(exact) == 1:
        return exact[0], 'sample'
    if len(exact) > 1:
        raise ValueError('Found multiple voices with the selected sample; cannot choose safely.')
    names = [x for x in voices if matches_maha(x)]
    if len(names) == 1:
        return names[0], 'name'
    raise ValueError('Could not uniquely identify Maha. Please check the voices list in Munsit dashboard.')


def update_env(updates):
    content = ENV.read_text(encoding='utf-8') if ENV.exists() else ENV_EXAMPLE.read_text(encoding='utf-8')
    for name, value in updates.items():
        line = f'{name}={value}'
        pat = re.compile(rf'^{re.escape(name)}=.*$', re.MULTILINE)
        content = pat.sub(lambda _: line, content) if pat.search(content) else content.rstrip() + '\n' + line + '\n'
    ENV.write_text(content, encoding='utf-8')
    os.chmod(ENV, 0o600)


def main():
    print('لَبِق — إعداد صوت مها (منصت Munsit)')
    print('افتحي https://app.munsit.com وأنشئي API Key إذا ما عندك.')
    print('مفتاح منصت مختلف عن مفتاح Azure؛ لا تلصقين مفتاح Azure هنا.\n')
    print('1) Global — app.munsit.com')
    print('2) UAE — ae.app.munsit.com')
    selection = input('نوع حساب منصت [1]: ').strip() or '1'
    if selection not in REGIONS:
        raise SystemExit('اختاري 1 أو 2.')
    base = REGIONS[selection]
    key = getpass('Munsit API Key (مخفي): ').strip()
    if len(key) < 12 or '\n' in key or '\r' in key:
        raise SystemExit('مفتاح غير صالح شكليًا. لم يُحفظ شيء.')
    print('أتحقق من قائمة الأصوات بدون طلب صوت مدفوع...')
    try:
        with httpx.Client(timeout=30.0) as client:
            res = client.get(base + '/voices', headers={'x-api-key': key})
            res.raise_for_status()
            voices = get_voice_list(res.json())
    except httpx.HTTPStatusError as exc:
        code = exc.response.status_code
        raise SystemExit(f'فشل التحقق من منصت HTTP {code}. تأكدي من المفتاح ومنطقة الحساب.') from exc
    except (httpx.HTTPError, ValueError) as exc:
        raise SystemExit(f'فشل الاتصال بمنصت: {type(exc).__name__}. تأكدي من الإنترنت.') from exc
    if not voices:
        raise SystemExit('قائمة الأصوات فارغة أو بشكل غير متوقع. لا يمكن اختيار مها بأمان.')
    try:
        voice, how = select_maha(voices)
    except ValueError:
        print('\nالأصوات السعودية النسائية التي ظهرت (الأسماء فقط):')
        candidates = [v for v in voices if str(v.get('gender') or '').lower() == 'female']
        for v in candidates[:25]:
            print(' -', v.get('name'), ':', ', '.join(v.get('dialect') or []))
        raise SystemExit('لم أستطع مطابقة عينة مها. لا أنصح باختيار صوت آخر بالخطأ.')
    print('تم العثور على:', voice.get('name'), '| اللهجة:', voice.get('dialect'))
    if how == 'sample':
        print('تطابق رابط العينة المرسلة تمامًا.')
    else:
        print('تطابق الاسم واللهجة، لكن رابط العينة لم يظهر مطابقًا في بيانات API.')
        print('المعاينة الموجودة لدى منصت:', voice.get('sample_url') or 'غير متاحة')
        if input('هل هذا هو صوت مها المطلوب؟ اكتبي نعم للمتابعة: ').strip() != 'نعم':
            raise SystemExit('تم الإلغاء دون تعديل الإعدادات.')
    voice_id = str(voice['voice_id'])
    if '\n' in voice_id or '\r' in voice_id:
        raise SystemExit('Voice ID غير صالح؛ لم تُحفظ الإعدادات.')
    update_env({
        'LABEQ_TTS_PROVIDER': 'munsit',
        'MUNSIT_API_KEY': key,
        'MUNSIT_VOICE_ID': voice_id,
        'MUNSIT_BASE_URL': base,
    })
    print('\nتم ربط إعدادات مها محليًا بملف .env دون تغيير بيانات Azure القديمة.')
    print('الخطوة التالية: python verify_munsit.py')


if __name__ == '__main__':
    main()
