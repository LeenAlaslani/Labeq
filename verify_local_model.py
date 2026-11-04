import json, urllib.request
url='http://127.0.0.1:7862'
try:
  with urllib.request.urlopen(url+'/health',timeout=10) as r: status=json.load(r)
  print('Health:',status)
  if not status.get('model_loaded') or not status.get('adapter_loaded'):
    raise RuntimeError('المودل أو LoRA غير محمل')
  print('✅ المودل المحلي يتجاوب، والأوزان تم تحميلها. اختبار التوليد التالي يتطلب ضغط زر لبِق.')
except Exception as e:
  print('❌ فشل الوصول للخادم المحلي:',str(e))
  print('تأكدي أن bash start_local_model.sh شغال في نافذة ثانية')
  raise SystemExit(1)
