"""Write private loopback model settings."""
from pathlib import Path
from secrets import token_urlsafe
ROOT=Path(__file__).resolve().parent
p=ROOT/'.env'
if p.exists():
    lines=p.read_text().splitlines()
else:
    template=ROOT/'.env.example'
    lines=template.read_text().splitlines() if template.exists() else []
# For safety, build new independent local secret every first setup.
keyfile=ROOT/'.local_api_key'
key=keyfile.read_text().strip() if keyfile.exists() else token_urlsafe(32)
keyfile.write_text(key+'\n'); keyfile.chmod(0o600)
reserved=('LABEQ_MODEL_API_URL=', 'LABEQ_MODEL_API_KEY=', 'LABEQ_MODEL_MODE=')
lines=[l for l in lines if not l.startswith(reserved)]
lines.extend(['LABEQ_MODEL_API_URL=http://127.0.0.1:7862','LABEQ_MODEL_API_KEY='+key,'LABEQ_MODEL_MODE=real'])
p.write_text('\n'.join(lines).rstrip()+'\n')
p.chmod(0o600)
print('✅ تم تجهيز إعدادات خادم الاستدلال المحلي.')
