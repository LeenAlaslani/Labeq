"""Read-only check of deployed Colab model health; no paid generation call."""
import asyncio
from pathlib import Path
from dotenv import load_dotenv
from model_bridge import remote_health

load_dotenv(Path(__file__).resolve().parent / '.env')

async def main():
    status = await remote_health()
    if not status['configured']:
        print('لم تضبطي اتصال المودل بعد. نفذي: python configure_model.py')
    elif not status['reachable']:
        print('الخادم لا يرد؛ افحصي رابط Cloudflare وجلسة Colab.')
    elif status['model_loaded']:
        print('✅ اتصال Qwen + Saudi LoRA يعمل من ناحية الخادم.')
        print('فيصل:', 'محمّل' if status['faisal_loaded'] else 'غير متاح — سيتم توضيح القواعد الاحتياطية في الموقع')
        print('هذا اختبار اتصال، وليس توليد رد حقيقي بعد.')
    else:
        print('الخادم يرد لكن المودل لم يتم تحميله. شغلي خلية engine.load في Colab.')

if __name__ == '__main__':
    asyncio.run(main())
