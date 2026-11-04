"""Interactive Mac configuration; secrets are kept in local .env only."""
from pathlib import Path
from getpass import getpass
from urllib.parse import urlparse

path = Path(__file__).resolve().parent / '.env'
print('ربط لبِق مع API المودل المنشور من Colab (لا تضعي مفتاح منصت هنا).')
url = input('رابط المودل HTTPS من Colab: ').strip().rstrip('/')
if url.endswith('/v1/reply'):
    url = url[:-len('/v1/reply')]
parsed = urlparse(url)
if not parsed.hostname or (parsed.scheme != 'https' and not (parsed.scheme == 'http' and parsed.hostname in ('localhost', '127.0.0.1'))):
    raise SystemExit('الرابط يجب أن يكون HTTPS، أو localhost للتجربة فقط.')
key = getpass('LABEQ API Key الخاص بالمودل (مخفي): ').strip()
if len(key) < 16:
    raise SystemExit('مفتاح قصير جدًا؛ استخدمي المفتاح الموجود في خلية Colab.')
old = path.read_text() if path.exists() else ''
lines = [line for line in old.splitlines() if not line.startswith(('LABEQ_MODEL_API_URL=', 'LABEQ_MODEL_API_KEY=', 'LABEQ_MODEL_MODE='))]
lines += ['LABEQ_MODEL_API_URL=' + url, 'LABEQ_MODEL_API_KEY=' + key, 'LABEQ_MODEL_MODE=real']
path.write_text('\n'.join(lines).rstrip() + '\n')
path.chmod(0o600)
print('تم حفظ رابط المودل والمفتاح محليًا. أعيدي تشغيل run_mac.sh. لا تشاركي ملف .env')
