/* Queue real model requests through the Space's Gradio API. */
'use strict';

window.labeqSpaceReply=async function(payload){
  const relation={friend:'صديق',family:'عائلة',work:'عمل',customer:'عميل'};
  const styles={polite:'لطيف',firm:'حازم',diplomatic:'دبلوماسي',apology:'اعتذار',clarify:'طلب توضيح'};
  const history=[...payload.history];
  if(payload.tone==='formal')history.push({role:'user',content:'تعليمات تعديل الرد: اجعلي الصياغة رسمية ومهنية دون تغيير الهدف أو نوع الأسلوب.'});
  if(payload.instruction)history.push({role:'user',content:'تعليمات تعديل الرد: '+payload.instruction.slice(0,450)});
  const request={
    message:payload.message,relation:relation[payload.relation],goal:payload.goal,
    style:styles[payload.style_key]||'تلقائي',history:history.slice(-6),
    generation_mode:'مولّد فقط'
  };
  const controller=new AbortController();
  const timer=setTimeout(()=>controller.abort(),150000);
  try{
    const endpoint='/model/gradio_api/call/reply';
    const submitted=await fetch(endpoint,{
      method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({data:[request]}),signal:controller.signal
    });
    if(!submitted.ok)throw Error('تعذّر الانضمام لطابور المودل. جرّبي مرة ثانية.');
    const job=await submitted.json();
    if(typeof job.event_id!=='string'||!/^[a-zA-Z0-9_-]+$/.test(job.event_id))throw Error('لم يبدأ طلب المودل.');
    const stream=await fetch(endpoint+'/'+job.event_id,{signal:controller.signal});
    if(!stream.ok||!stream.body)throw Error('تعذّر متابعة طلب المودل.');
    const reader=stream.body.getReader();
    const decoder=new TextDecoder();
    let pending='';
    try{
      while(true){
        const chunk=await reader.read();
        pending=(pending+decoder.decode(chunk.value,{stream:!chunk.done})).replace(/\r\n/g,'\n');
        let boundary;
        while((boundary=pending.indexOf('\n\n'))>=0){
          const frame=pending.slice(0,boundary);
          pending=pending.slice(boundary+2);
          const event=frame.split('\n').find(line=>line.startsWith('event:'))?.slice(6).trim();
          const data=frame.split('\n').filter(line=>line.startsWith('data:')).map(line=>line.slice(5).trimStart()).join('\n');
          if(event==='error'){
            let reason='';
            try{reason=JSON.parse(data)?.error||''}catch{}
            if(/quota|runs limit|credits|authenticate/i.test(reason)){
              throw Error('انتهت حصة GPU المجانية. افتحي التطبيق من صفحة Hugging Face بعد تسجيل الدخول، أو جرّبي لاحقًا.');
            }
            throw Error('تعذّر التوليد أو انتهت حصة GPU. جرّبي لاحقًا.');
          }
          if(event==='complete'){
            const result=JSON.parse(data)?.[0];
            if(!result||typeof result.reply!=='string'||!result.reply.trim()||!['qwen_lora_generated','qwen_base_generated','ollama_generated'].includes(result.reply_source)||result.mock===true)throw Error('رجع المودل استجابة غير صالحة.');
            return {...result,style:result.style_key,mock:false};
          }
        }
        if(chunk.done)break;
      }
    }finally{
      await reader.cancel().catch(()=>{});
    }
    throw Error('انتهى اتصال المودل قبل اكتمال الرد.');
  }catch(error){
    if(error.name==='AbortError')throw Error('تأخر طابور المودل. جرّبي مرة ثانية.');
    throw error;
  }finally{
    clearTimeout(timer);
  }
};
