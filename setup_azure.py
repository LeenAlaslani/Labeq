"""Configure LABEQ Azure Speech on this computer without echoing the secret key."""
from getpass import getpass
from pathlib import Path
import re
import os

ROOT = Path(__file__).resolve().parent
ENV_FILE = ROOT / '.env'
EXAMPLE = ROOT / '.env.example'

print('\nLABEQ — إعداد الصوت النسائي السعودي (زاريّة)')
print('المفتاح لن يظهر في الشاشة. لا ترسليه لأحد.\n')
region = input('Azure Region (مثل uaenorth أو eastus): ').strip().lower()
if not re.fullmatch(r'[a-z0-9-]{3,35}', region):
    raise SystemExit('Region غير صحيح. اكتبي الكود بالإنجليزي مثل uaenorth.')
key = getpass('Azure Speech KEY 1 (الصقي المفتاح هنا ثم Enter): ').strip()
if not re.fullmatch(r'[A-Za-z0-9+/=._-]{12,256}', key):
    raise SystemExit('المفتاح غير صالح شكليًا، لم يتم حفظ شيء.')

content = ENV_FILE.read_text(encoding='utf-8') if ENV_FILE.exists() else EXAMPLE.read_text(encoding='utf-8')
for name, value in (
    ('LABEQ_TTS_PROVIDER', 'azure'),
    ('AZURE_SPEECH_KEY', key),
    ('AZURE_SPEECH_REGION', region),
):
    replacement = f'{name}={value}'
    pattern = re.compile(rf'^{re.escape(name)}=.*$', re.MULTILINE)
    content = pattern.sub(lambda _: replacement, content) if pattern.search(content) else content + '\n' + replacement + '\n'
ENV_FILE.write_text(content, encoding='utf-8')
os.chmod(ENV_FILE, 0o600)
print('\nتم حفظ الإعدادات في .env على جهازك فقط.')
print('الآن نفذي: python verify_azure.py\n')
