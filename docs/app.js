/* LABEQ interactive showcase. No fabricated Faisal inference: demo is explicitly labeled. */
'use strict';
const $ = id => document.getElementById(id);
const $all = sel => [...document.querySelectorAll(sel)];
const state = {
  step:0, name:'', nickname:'', address:'friendly', title:'أستاذة',
  relation:'', goal:'', message:'', style:'', tone:'casual', rewrite:0,
  hasResult:false, mock:true, confidence:null, started:false,
  voiceOn:false, currentSpeech:'', speechId:0, audio:null, recording:false,
  recognition:null, recorder:null, audioCtx:null, analyzeBusy:false,
  modelReply:'', modelStyleUsed:'', routerSource:'', replySource:'', needsReview:false, qualityWarnings:[], variantBusy:false
};
let capabilities={tts:false,stt:false,model_mode:'demo',voice_name:''};
let toastTimer, lipTimer, blinkTimer, activeSpeech, contextMoodTimer, reactionTimer;
const speechCache=new Map(); // Replay the same voice recording instead of regenerating it.
const relations=[
  {key:'friend',name:'صديق / صديقة',icon:'♡',short:'صديق'},
  {key:'family',name:'أحد من العائلة',icon:'⌂',short:'عائلة'},
  {key:'work',name:'زميل / مدير',icon:'▣',short:'عمل'},
  {key:'customer',name:'عميل',icon:'◇',short:'عميل'}
];
const goals=[
  {key:'polite',label:'أرفض بلطف',symbol:'♡',detail:'بدون إحراج'},
  {key:'firm',label:'أحط حدود',symbol:'⊘',detail:'بوضوح واحترام'},
  {key:'diplomatic',label:'أصلح خلاف',symbol:'✳',detail:'نتفاهم بهدوء'},
  {key:'apology',label:'أعتذر',symbol:'✿',detail:'وأصلح الغلط'},
  {key:'clarify',label:'أفهم المقصود',symbol:'?',detail:'بدون سوء فهم'}
];
const styleLabels={polite:'لبق',firm:'حازم',diplomatic:'دبلوماسي',apology:'اعتذار',clarify:'طلب توضيح'};
const goalPhrases={polite:'أرفض الطلب بأسلوب محترم',firm:'أوضح حدودي بدون تجريح',diplomatic:'أحل سوء الفهم بهدوء',apology:'أعتذر وأصلح الموقف',clarify:'أتأكد إني فهمت المقصود'};
const replyBank={
  polite:{
    casual:['أقدّر طلبك، بس هالمرة ما أقدر. إن شاء الله تتيسر لك.','ودي أساعدك، بس ظروفي الحين ما تسمح لي. أتمنى تتفهم.','تسلم على ثقتك، لكن بعتذر منك هالمرة.'],
    formal:['أقدّر طلبك، لكن يتعذّر عليّ ذلك حاليًا. أشكرك على تفهّمك.','شكرًا لتواصلك. أعتذر عن عدم تمكني من تلبية هذا الطلب.','يسعدني تعاوننا، ولكن لا أستطيع الالتزام بهذا الأمر في الوقت الحالي.']},
  firm:{
    casual:['أقدّر ظروفك، بس عندي مسؤولياتي وما أقدر أتحمل شغل إضافي بشكل مستمر.','أحب أساعد وقت ما أقدر، لكن مو مناسب إني أستلم مهام مو من مسؤوليتي.','خلّينا نتفق على حدود واضحة من البداية؛ كل واحد مسؤول عن شغله.'],
    formal:['أتفهم ظروفك، لكن لدي مسؤولياتي الخاصة ولا أستطيع تولّي مهام إضافية باستمرار.','أقدّر تعاوننا، وأفضّل أن تبقى المسؤوليات موزعة بوضوح بيننا.','أعتذر عن تحمّل مهام خارج نطاق مسؤولياتي في الوقت الحالي.']},
  diplomatic:{
    casual:['أدري إن اللي صار ضايقنا، بس ودي نتفاهم بهدوء ونسمع بعض.','يمكن فهمنا كلام بعض غلط. خلّينا نتكلم ونوضح اللي صار.','ما ودي يطول الزعل بيننا. خلّينا نسمع بعض ونحل الموضوع.'],
    formal:['أعتقد أن هناك سوء فهم بيننا، وأفضّل أن نناقش الأمر بهدوء للوصول إلى حل.','يهمني أن نتجاوز الخلاف، وأقترح أن نوضح وجهتي نظرنا باحترام.','قد نختلف في وجهات النظر، لكن من الأفضل أن نتحاور للوصول إلى تفاهم.']},
  apology:{
    casual:['حقك علي، أدري إني غلطت، وما كان قصدي أزعلك.','سامحني على اللي صار. أتحمل غلطتي وبحاول ما تتكرر.','أعتذر منك، كان المفروض أتصرف بطريقة أفضل.'],
    formal:['أعتذر عن الخطأ الذي بدر مني، وأتحمل مسؤوليته وسأعمل على عدم تكراره.','أقدّم اعتذاري عما حدث، وأتفهّم أثره عليك.','أعتذر عن هذا التصرف، وأقدّر تفهّمك وأحرص على تصحيح الموقف.']},
  clarify:{
    casual:['ممكن توضح لي قصدك أكثر؟ أبغى أتأكد إني فهمتك صح.','بس عشان أفهمك صح، تقصد كذا ولا شيء ثاني؟','ودي أتأكد من نقطة: وش المطلوب مني بالضبط؟'],
    formal:['هل يمكنك توضيح المقصود بمزيد من التفصيل؟ أود التأكد من فهمي بشكل صحيح.','للتأكد من وضوح المطلوب، هل يمكن توضيح هذه النقطة؟','أشكرك على التوضيح. هل تقصد الأمر الأول أم الثاني تحديدًا؟']}
};
function displayName(){const name=state.address==='formal' ? ((state.title==='بدون لقب'?'':state.title+' ')+state.name) : (state.nickname.trim()||state.name);return (name||'يا صديقة').trim()}
function vocative(){return 'يا '+displayName()}
function friendly(){return state.address==='friendly'}
function toaste(message){const el=$('toast');el.textContent=message;el.classList.add('show');clearTimeout(toastTimer);toastTimer=setTimeout(()=>el.classList.remove('show'),3600)}
function element(tag,className,text){const e=document.createElement(tag);if(className)e.className=className;if(text!==undefined)e.textContent=text;return e}
function makeInput({label,value,placeholder,onChange,maxLength=50,ariaLabel}){
  const wrapper=element('div');const l=element('label','field-label',label);const inp=element('input','pretty-input');inp.type='text';inp.value=value;inp.placeholder=placeholder;inp.maxLength=maxLength;inp.setAttribute('aria-label',ariaLabel||label);l.appendChild(inp);inp.addEventListener('input',e=>onChange(e.target.value));wrapper.append(l);return wrapper;
}
function makeChoices(items,value,onSelect){const grid=element('div','chips-grid');for(const item of items){const b=element('button','choice-chip'+(item.key===value?' active':''));b.type='button';b.setAttribute('aria-pressed',String(item.key===value));const icon=element('span','choice-icon',item.icon||item.symbol);const name=element('span','choice-title',item.name||item.label);b.append(icon,name);if(item.detail)b.append(element('span','choice-sub',item.detail));b.addEventListener('click',()=>{onSelect(item.key);$all('#stepContent .choice-chip').forEach(x=>{x.classList.toggle('active',x===b);x.setAttribute('aria-pressed',String(x===b))});updateNext()});grid.append(b)}return grid}
function questionForStep(){switch(state.step){case 0:return 'يا هلا! وش تحبين أناديك؟';case 1:return `تشرفنا ${vocative()}، كيف تحبين أخاطبك؟`;case 2:return `تمام ${vocative()}، مين الشخص اللي بتتكلمين معه؟`;case 3:return 'وش تبغين توصّلين من كلامك؟';default:return `أنا أسمعك ${vocative()}، احكي لي وش صار.`}}
function renderIntro(announce=false){
  $('introPanel').hidden=false;$('workspace').hidden=true;
  const headings=['خلّينا نتعرّف.','على راحتك.','مين الطرف الثاني؟','وش هدفك؟'];
  const descriptions=['وش تحبين أناديك؟','اختاري أسلوبي معك.','عشان يكون الرد مناسب لعلاقتكم.','اختاري أقرب هدف للي تبغينه.'];
  $('introIndex').textContent=String(state.step+1).padStart(2,'0')+' / 04';$('introHeading').textContent=headings[state.step];$('introSubline').textContent=descriptions[state.step];
  const container=$('stepContent');container.replaceChildren();
  if(state.step===0){const fields=element('div','input-stack');fields.append(makeInput({label:'اسمك',value:state.name,placeholder:'مثال: لين',onChange:s=>{state.name=s.trimStart();updateNext()},maxLength:32}));fields.append(makeInput({label:'اسم الدلع (اختياري)',value:state.nickname,placeholder:'مثال: لينو',onChange:s=>{state.nickname=s.trimStart()},maxLength:30}));container.append(fields)}
  else if(state.step===1){container.append(makeChoices([{key:'friendly',name:'عفوي وقريب',icon:'☺',detail:'يا لينو، كيف حالك؟'},{key:'formal',name:'رسمي وراقي',icon:'♢',detail:'أهلًا أستاذة لين'}],state.address,k=>{state.address=k;renderIntro(false)}));if(state.address==='formal'){
    const l=element('div','input-sub','اللقب');l.style.marginTop='15px';container.append(l);const titles=[{key:'أستاذة',name:'أستاذة',icon:'✦'},{key:'آنسة',name:'آنسة',icon:'✦'},{key:'بدون لقب',name:'بدون لقب',icon:'—'}];const group=makeChoices(titles,state.title,k=>{state.title=k;renderIntro(false)});group.style.gridTemplateColumns='repeat(3,minmax(0,1fr))';group.querySelectorAll('.choice-chip').forEach(ch=>{ch.style.minHeight='60px';const icon=ch.querySelector('.choice-icon');if(icon)icon.remove()});container.append(group)}}
  else if(state.step===2){container.append(makeChoices(relations,state.relation,k=>{state.relation=k;setContextMood()}))}
  else if(state.step===3){container.append(makeChoices(goals,state.goal,k=>{state.goal=k;setContextMood()}))}
  $('prevBtn').hidden=state.step===0;$('nextBtn').textContent=state.step===3?'وصلنا ✦':'نكمل ←';updateNext();setContextMood();revealCharacter();
  setDialogue(questionForStep(),'أنا معك',announce)
}
function updateNext(){$('nextBtn').disabled=(state.step===0&&!state.name.trim())||(state.step===2&&!state.relation)||(state.step===3&&!state.goal)}
function setDialogue(text,tag='أنا معك',announce=false){state.currentSpeech=text;$('dialogTag').textContent=tag;$('dialogText').textContent=text;if(announce&&state.started&&state.voiceOn)playSpeech(text);}
function setAvatarMood(mood){
  if(!mood || mood==='idle') mood='greet';
  $('avatarWrap').dataset.mood=mood;
  window.labeqCharacter?.setMood(mood);
}
function revealCharacter(){const a=$('avatarWrap');const b=$('charDialog');a.classList.remove('reveal');b.classList.remove('reveal');void a.offsetWidth;a.classList.add('reveal');b.classList.add('reveal')}
function moodFromStyle(style){
  return {apology:'sorry', clarify:'think', diplomatic:'happy',firm:'think',polite:'greet'}[style]||'greet';
}
function moodFromMessage(text){
  const m=String(text||'').trim();
  if(!m)return '';
  if(/محرج|انحرج|انحرجت|فشلة|فشله|تفاجأت|تفاجات|صدمة|انصدمت|ورطة|ورطه|فشلت|استحيت/.test(m))return 'surprised';
  if(/أعتذر|اعتذر|غلطت|سامحني|زعلته|زعلتها|تأسفت|آسف|آسفة|اسفه/.test(m))return 'sorry';
  if(/تخاصمنا|سوء فهم|خلاف|زعلان|زعلانة|مشكلة|تضارب/.test(m))return 'think';
  if(/مبسوطة|مبسوط|فرحة|فرحت|نجحت|مبروك/.test(m))return 'happy';
  return '';
}
function moodFromContext(){
  if(state.recording||state.analyzeBusy)return 'think';
  if(state.hasResult && state.style)return moodFromStyle(state.style);
  if(state.step===0)return 'greet';
  if(state.step===1)return state.address==='formal'?'think':'happy';
  if(state.step===2)return 'greet';
  if(state.step===3)return {apology:'sorry',clarify:'think',firm:'think',diplomatic:'happy'}[state.goal]||'greet';
  return moodFromMessage(state.message) || 'greet';
}
function setContextMood(){setAvatarMood(moodFromContext())}
function reactBrieflyToMessage(message){
  clearTimeout(reactionTimer);
  const reaction=moodFromMessage(message);
  if(!reaction)return;
  setAvatarMood(reaction);
  reactionTimer=setTimeout(()=>setContextMood(),1350);
}
function setSpeaking(s){const avatar=$('avatarWrap');avatar.dataset.speaking=String(s);window.labeqCharacter?.setSpeaking(s);if(!s)window.labeqCharacter?.setMouth(0)}
function mouthOpenForChar(ch){
  if(!ch || /[.،؟!;: ]/.test(ch))return .12;
  if(/[مبفپ]/.test(ch))return .16;
  if(/[اأإآووييىه]/.test(ch))return .72;
  if(/[قكجحخهعغ]/.test(ch))return .52;
  return .39;
}
function startLipApprox(){
  clearInterval(lipTimer);
  const begun=performance.now();
  lipTimer=setInterval(()=>{
    if($('avatarWrap').dataset.speaking!=='true')return;
    const tm=(performance.now()-begun)/1000;
    const movement=.18+.24*Math.abs(Math.sin(tm*7.9)+.22*Math.sin(tm*12));
    window.labeqCharacter?.setMouth(Math.min(.64,movement));
  },60);
}
function startLipSync(chars,starts,audio,tok,text){
  if(!(starts?.length && chars?.length && audio)){startLipApprox();return;}
  clearInterval(lipTimer);
  lipTimer=setInterval(()=>{
    if(tok!==state.speechId){clearInterval(lipTimer);return;}
    let index=0;
    while(index<starts.length-1 && starts[index+1]<=audio.currentTime)index++;
    window.labeqCharacter?.setMouth(mouthOpenForChar(chars[index]||''));
    markCaption(text,Math.min(text.length,index+1));
  },50);
}
function stopSpeech(){
  state.speechId++;
  if(state.audio){state.audio.pause();state.audio.removeAttribute('src');state.audio.load();state.audio=null;}
  try{window.speechSynthesis?.cancel()}catch{}
  clearInterval(lipTimer);activeSpeech=null;
  setSpeaking(false);
  $('dialogText').textContent=state.currentSpeech;
}
function preferredBrowserVoice(){const vs=('speechSynthesis'in window)?window.speechSynthesis.getVoices():[];return vs.find(v=>/Zariyah/i.test(v.name))||vs.find(v=>v.lang.toLowerCase()==='ar-sa'&&/female|woman|hoda|zariyah|salma/i.test(v.name))||vs.find(v=>v.lang.toLowerCase()==='ar-sa')||vs.find(v=>v.lang.toLowerCase().startsWith('ar'))||null}
function markCaption(text,index){const a=$('dialogText');if(!Number.isFinite(index)||index<=0){a.textContent=text;return}const i=Math.min(Math.max(0,index),text.length);const played=element('span','played',text.slice(0,i));const upcoming=element('span','upcoming',text.slice(i));a.replaceChildren(played,upcoming)}
async function playSpeech(text,force=false){
  if(!force&&!state.voiceOn)return;if(!text)return;
  stopSpeech();state.currentSpeech=text;const token=state.speechId;
  setSpeaking(true);startLipApprox();browserSpeak(text,token);
}

function browserSpeak(text,tok){
  if(!('speechSynthesis'in window)){
    toaste('المتصفح لا يدعم النطق.');return;
  }
  try{
    const u=new SpeechSynthesisUtterance(text);
    const voice=preferredBrowserVoice();if(voice)u.voice=voice;
    u.lang='ar-SA';u.rate=.93;u.pitch=1;u.volume=1;
    u.onstart=()=>{if(tok!==state.speechId)return;setSpeaking(true);startLipApprox()};
    u.onboundary=e=>{if(tok===state.speechId&&Number.isInteger(e.charIndex))markCaption(text,e.charIndex)};
    u.onend=()=>{if(tok!==state.speechId)return;clearInterval(lipTimer);setSpeaking(false);$('dialogText').textContent=text;setContextMood()};
    u.onerror=()=>{if(tok!==state.speechId)return;clearInterval(lipTimer);setSpeaking(false)};
    activeSpeech=u;window.speechSynthesis.speak(u);
  }catch{setSpeaking(false);toaste('تعذّر تشغيل الصوت من المتصفح.')}
}
function renderWorkspace(announce=false){
  $('introPanel').hidden=true;$('workspace').hidden=false;
  const r=relations.find(x=>x.key===state.relation)?.short||'صديق';const g=goals.find(x=>x.key===state.goal)?.label||'أختار أسلوبي';
  $('profileText').textContent=`${displayName()}   ·   ${r}   ·   ${g}`;
  $('scenarioInput').value=state.message;$('dataBadge').textContent=state.mock?(capabilities.model_configured?'المودل مهيأ':'المودل غير متصل'):(state.routerSource==='faisal'?'فيصل + Qwen':state.routerSource==='rule_fallback'?'Qwen · فيصل غير متاح':'Qwen · أسلوب يدوي');
  $('confidenceNote').textContent=state.mock?'لم يتم توصيل المودل الحقيقي بعد':(state.routerSource==='faisal'?'الأسلوب من فيصل · النص مولّد من Saudi LoRA':(state.routerSource==='rule_fallback'?'فيصل غير متاح · الأسلوب من قواعد احتياطية · النص من Saudi LoRA':'الأسلوب محدّد يدويًا · النص من Saudi LoRA')); 
  if(state.hasResult)renderResult();else{$('filledResult').hidden=true;$('emptyResult').hidden=false}
  $('nav1').classList.add('done');$('nav1').classList.remove('active');$('nav2').classList.add('active');$('nav3').classList.toggle('active',state.hasResult);
  setContextMood();revealCharacter();setDialogue(state.hasResult?`هذا اللي أقترحه ${vocative()}، وش رأيك؟`:`أنا أسمعك ${vocative()}، احكي لي وش صار.`,state.hasResult?'الاقتراح جاهز':'خذي راحتك',announce)
}
function selectReply(style,tone,idx){const bank=replyBank[style]||replyBank.polite;const variants=bank[tone]||bank.casual;
  // Domain-aware variants remain prepared templates. They are NOT free-form generation.
  if(state.relation==='friend'&&style==='clarify'&&idx===0&&/تضارب|تخاصم|سب|زعل|عصب|خلاف/.test(state.message))return tone==='formal'?'أود فهم ما حدث بيننا بشكل أوضح. ما الذي أزعجك تحديدًا؟ حتى نتجاوز سوء الفهم.':'أبغى أفهم اللي صار بيننا، وش اللي ضايقك بالضبط؟ عشان ما نفهم بعض غلط.';
  if(state.relation==='work'&&style==='firm'&&idx===0&&/مدير|مديرتي|رئيسي|رئيستي/.test(state.message))return tone==='formal'?'يسعدني التعاون، لكن أحتاج إلى تحديد أولويات المهام الحالية قبل إضافة مسؤوليات جديدة.':'أبشر، بس خلّينا نرتّب أولويات شغلي الحالي قبل ما أستلم مهام زيادة.';
  if(state.relation==='friend'&&style==='firm'&&idx===0)return tone==='formal'?'أقدّر صداقتنا، لكن هناك حدود أحب أن نحترمها حتى تستمر علاقتنا بشكل صحي.':'أنت غالي عندي، بس فيه حدود تهمني وأبغى نحترمها بيننا.';
  if(state.relation==='work'&&style==='diplomatic'&&idx===0)return tone==='formal'?'أقترح أن نجلس لمناقشة ما حدث بهدوء، ونحدد طريقة واضحة للعمل معًا.':'خلّينا نتفاهم على اللي صار ونحدد طريقة واضحة نتعاون فيها.';
  if(state.relation==='customer'&&style==='apology'&&idx===0)return tone==='formal'?'نعتذر عن التجربة غير المرضية، ونقدّر ملاحظتك وسنعمل على معالجة المشكلة.':'نعتذر عن اللي صار، وملاحظتك تهمنا وبنحاول نحل المشكلة بأسرع وقت.';
  if(state.relation==='friend'&&style==='apology'&&idx===0)return tone==='formal'?'أعتذر منك عمّا بدر مني. يهمني أن نصلح ما حدث بيننا.':'حقك علي، أدري إني زعلتك وما كان قصدي. ما أبي هالموضوع يبعدنا.';
  return variants[idx%variants.length]
}
function renderResult(){
  const style=state.style||state.goal||'polite';
  $('emptyResult').hidden=true;$('filledResult').hidden=false;
  $('stylePill').textContent=!state.mock?(state.style&&styleLabels[state.style]?styleLabels[state.style]:(state.modelStyleUsed||'الأسلوب المقترح')):styleLabels[style];
  $('replyText').textContent=!state.mock?state.modelReply:selectReply(style,state.tone,state.rewrite);
  $('formalityBtn').textContent=state.tone==='casual'?'صياغة رسمية':'صياغة عفوية';
  $('styleChoices').hidden=true;$('changeStyleBtn').setAttribute('aria-expanded','false');$('nav3').classList.add('active');setContextMood();
  if(!state.mock){
    const who=state.routerSource==='faisal'?'الأسلوب: فيصل':state.routerSource==='rule_fallback'?'الأسلوب: قواعد احتياطية (فيصل غير متاح)':'الأسلوب: اختيار المستخدم';
    $('confidenceNote').textContent=who+' · الرد: Qwen Saudi LoRA'+(state.needsReview?' · يحتاج مراجعة قبل الإرسال':'');
  }else{
    $('confidenceNote').textContent='المودل لم يُربط بعد — لا توجد نتيجة AI فعلية';
  }
}
async function requestActualReply({styleKey=null,tone=state.tone,instruction=null,history=[]}={}){
  const result=await fetch('/api/reply',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({
    message:state.message, relation:state.relation, goal:goalPhrases[state.goal]||'أبي رد مناسب',
    style_key:styleKey, tone, instruction, history
  })});
  let body={};try{body=await result.json()}catch{}
  if(!result.ok)throw new Error(typeof body.detail==='string'?body.detail:'فشل اتصال المودل ('+result.status+')');
  if(typeof body.reply!=='string'||!body.reply.trim()||body.mock!==false)throw new Error('لم يرجع المودل ردًا مولّدًا صالحًا');
  return body;
}
function useRealReply(data,styleFallback=null){
  state.modelReply=data.reply; state.modelStyleUsed=data.style_used||'';
  state.routerSource=data.router_source||'unknown';state.replySource=data.reply_source||'unknown';
  state.needsReview=!!data.needs_review;state.qualityWarnings=data.quality_warnings||[];
  state.style=data.style||styleFallback||state.style||state.goal||'polite';
  state.mock=false;state.hasResult=true;state.confidence=null;
}
async function realVariant({styleKey=state.style,tone=state.tone,instruction=null}={}){
  if(state.variantBusy||!state.modelReply)return;
  state.variantBusy=true;stopSpeech();setAvatarMood('think');
  for(const id of ['alternateBtn','formalityBtn','changeStyleBtn'])$(id).disabled=true;
  try{
    const history=instruction?[{role:'user',content:state.message.slice(0,500)},{role:'assistant',content:state.modelReply.slice(0,500)}]:[];
    const data=await requestActualReply({styleKey,tone,instruction,history});
    useRealReply(data,styleKey);state.tone=tone;renderResult();setContextMood();
    setDialogue('جهزت لك صياغة ثانية، شوفي إذا تناسبك.','الاقتراح جاهز',false);
  }catch(err){toaste('تعذر تعديل الرد: '+err.message);setContextMood()}
  finally{state.variantBusy=false;for(const id of ['alternateBtn','formalityBtn','changeStyleBtn'])$(id).disabled=false}
}
function demoPredict(message,relation,goal){
  // Transparent UI simulation; no claim of ML inference.
  const m=message.toLowerCase();const strong=(/يضرب|ضربني|تهديد|يهددني/.test(m));
  if(strong)return 'firm';
  // Preserve the user goal in mock mode; the real model must infer rather than use this mapping.
  return goal||'clarify';
}
async function analyze(){
  const msg=$('scenarioInput').value.trim();
  if(msg.length<5){toaste('اكتبي تفاصيل الموقف أولًا.');$('scenarioInput').focus();return;}
  stopSpeech();state.message=msg;state.mock=true;state.hasResult=true;
  state.modelReply='';state.style=demoPredict(msg,state.relation,state.goal);state.rewrite=0;
  renderWorkspace(false);
  $('dataBadge').textContent='DEMO · أمثلة ثابتة';
  $('confidenceNote').textContent='عرض واجهة فقط — اقتراحات نموذجية وليست تنبؤات AI';
  setDialogue('هذا رد تجريبي يا '+displayName()+'، شوفي إذا يناسبك.','تجربة الواجهة',false);
}

function bind(){
  $('nextBtn').addEventListener('click',()=>{
    if($('nextBtn').disabled)return;stopSpeech();state.started=true;if(state.step<3){state.step++;renderIntro(true)}else{state.step=4;state.hasResult=false;renderWorkspace(true);setTimeout(()=>$('scenarioInput').focus({preventScroll:true}),350)}
  });
  $('prevBtn').addEventListener('click',()=>{stopSpeech();state.step=Math.max(0,state.step-1);renderIntro(true)});
  $('quickDemoBtn').addEventListener('click',()=>{stopSpeech();Object.assign(state,{name:'لين',nickname:'لينو',address:'friendly',relation:'friend',goal:'diplomatic',message:'صار بيني وبين صديقتي سوء فهم وزعلت مني. أبغى نتصالح بدون ما نكبر الموضوع.',tone:'casual',hasResult:false,started:true,step:4});renderWorkspace(true);$('scenarioInput').focus({preventScroll:true})});
  $('scenarioInput').addEventListener('input',e=>{state.message=e.target.value;state.modelReply='';if(state.hasResult){state.hasResult=false;$('emptyResult').hidden=false;$('filledResult').hidden=true;$('nav3').classList.remove('active');setDialogue(`أسمعك ${vocative()}، كمّلي براحتك.`,'أنا معك',false)}clearTimeout(contextMoodTimer);contextMoodTimer=setTimeout(setContextMood,460)});
  $('analyzeBtn').addEventListener('click',analyze);
  $('changeStyleBtn').addEventListener('click',()=>{
    const choices=$('styleChoices');const show=choices.hidden;choices.hidden=!show;
    $('changeStyleBtn').setAttribute('aria-expanded',String(show));
    if(show){choices.replaceChildren();for(const st of Object.keys(styleLabels)){
      const b=element('button','style-select'+(state.style===st?' chosen':''),styleLabels[st]);b.type='button';
      b.addEventListener('click',()=>{choices.hidden=true;state.style=st;state.rewrite=0;renderResult();$('dataBadge').textContent='DEMO · أمثلة ثابتة';$('confidenceNote').textContent='أمثلة محفوظة وليست نتائج AI'});
      choices.append(b);
    }}
  });
  $('alternateBtn').addEventListener('click',()=>{
    if(!state.mock&&state.modelReply)realVariant({instruction:'أعيدي صياغة آخر رد بعبارة مختلفة طبيعية ومختصرة، مع الحفاظ على نفس الموقف والمعنى. اكتبي الرد فقط.'});
    else{state.rewrite=(state.rewrite+1)%3;renderResult();$('confidenceNote').textContent='أمثلة محفوظة وليست نتائج AI';}
  });
  $('formalityBtn').addEventListener('click',()=>{
    const tone=state.tone==='casual'?'formal':'casual';
    if(!state.mock&&state.modelReply)realVariant({tone,instruction:tone==='formal'?'أعيدي صياغة آخر رد بشكل رسمي مهني مع الحفاظ على المعنى، بدون شرح.':'أعيدي صياغة آخر رد بلهجة سعودية عفوية وطبيعية دون تغيير المعنى، بدون شرح.'});
    else{state.tone=tone;state.rewrite=0;renderResult();$('confidenceNote').textContent='أمثلة محفوظة وليست نتائج AI';}
  });
  $('copyBtn').addEventListener('click',async()=>{const text=$('replyText').textContent;try{await navigator.clipboard.writeText(text);toaste('تم نسخ الرد ✦')}catch{const ta=document.createElement('textarea');ta.value=text;document.body.append(ta);ta.select();try{document.execCommand('copy');toaste('تم نسخ الرد ✦')}catch{toaste('حددي النص وانسخيه يدويًا')}ta.remove()}});
  $('listenReplyBtn').addEventListener('click',()=>{state.started=true;playSpeech($('replyText').textContent,true)});
  $('anotherBtn').addEventListener('click',()=>{stopSpeech();state.message='';state.hasResult=false;state.style='';state.modelReply='';state.routerSource='';$('scenarioInput').value='';renderWorkspace(true);$('scenarioInput').focus()});
  $('repeatBtn').addEventListener('click',()=>{state.started=true;playSpeech(state.currentSpeech,true)});
  $('muteBtn').addEventListener('click',()=>{state.voiceOn=!state.voiceOn;state.started=true;$('muteBtn').classList.toggle('muted',!state.voiceOn);$('muteBtn').setAttribute('aria-pressed',String(state.voiceOn));toaste(state.voiceOn?'شغّلت صوت الشخصية':'كتمت صوت الشخصية');if(!state.voiceOn)stopSpeech();else playSpeech(state.currentSpeech,true)});
  $('restartBtn').addEventListener('click',reset);$('brandBtn').addEventListener('click',e=>{e.preventDefault();reset()});
  $('editProfileBtn').addEventListener('click',()=>{stopSpeech();state.step=0;renderIntro(true)});
  $('micBtn').addEventListener('click',toggleMicrophone);
  const stage=$('stagePanel');stage.addEventListener('pointermove',e=>{const r=stage.getBoundingClientRect();const x=Math.max(-1,Math.min(1,((e.clientX-r.left)/r.width-.5)*2)),y=Math.max(-1,Math.min(1,((e.clientY-r.top)/r.height-.5)*2));const a=$('avatarWrap');a.style.setProperty('--lookX',(x*5).toFixed(1)+'px');a.style.setProperty('--lookY',(y*3).toFixed(1)+'px');a.style.setProperty('--tiltX',(-x*5).toFixed(2)+'deg');a.style.setProperty('--tiltY',(y*4).toFixed(2)+'deg');window.labeqCharacter?.setLook(x,y);});stage.addEventListener('pointerleave',()=>{const a=$('avatarWrap');a.style.setProperty('--lookX','0px');a.style.setProperty('--lookY','0px');a.style.setProperty('--tiltX','0deg');a.style.setProperty('--tiltY','0deg');window.labeqCharacter?.setLook(0,0)});
  planBlink();
}
function planBlink(){blinkTimer=setTimeout(()=>{window.labeqCharacter?.blink();if(Math.random()>.75)setTimeout(()=>window.labeqCharacter?.blink(),220);planBlink()},2400+Math.random()*2600)}
function reset(){stopSpeech();clearTimeout(reactionTimer);clearTimeout(contextMoodTimer);state.step=0;state.name='';state.nickname='';state.relation='';state.goal='';state.message='';state.style='';state.hasResult=false;state.tone='casual';state.rewrite=0;state.address='friendly';state.title='أستاذة';state.mock=true;state.modelReply='';state.routerSource='';state.modelStyleUsed='';state.started=false;$('nav1').classList.remove('done');$('nav1').classList.add('active');$('nav2').classList.remove('active');$('nav3').classList.remove('active');renderIntro(false);scrollTo({top:0,behavior:'smooth'})}
function toggleMicrophone(){
  if(state.recording){try{state.recognition?.stop()}catch{}try{if(state.recorder&&state.recorder.state==='recording')state.recorder.stop()}catch{}state.recording=false;showMic(false);return}
  const Rec=window.SpeechRecognition||window.webkitSpeechRecognition;
  if(Rec){try{const rec=new Rec();state.recognition=rec;rec.lang='ar-SA';rec.interimResults=true;rec.continuous=false;let original=$('scenarioInput').value.trim();rec.onresult=e=>{let transcript='';for(let i=0;i<e.results.length;i++)transcript+=e.results[i][0].transcript+' ';const combined=[original,transcript.trim()].filter(Boolean).join(' ');$('scenarioInput').value=combined;state.message=combined};rec.onerror=e=>{toaste(e.error==='not-allowed'?'اسمحي للمتصفح باستخدام الميكروفون.':'تعذر التعرف على الصوت، تقدرين تكتبين الموقف.')};rec.onend=()=>{state.recording=false;showMic(false);setContextMood();toaste('راجعي النص قبل استخراج الرد')};state.recording=true;showMic(true);state.started=true;setAvatarMood('think');setDialogue('أسمعك، خذي راحتك.','أسمعك',false);rec.start();return}catch{}}
  if(capabilities.stt&&navigator.mediaDevices?.getUserMedia){recordWithScribe();return}
  toaste('التعرف الصوتي غير متاح هنا. جربي Chrome مع إذن المايك، أو اكتبي الموقف.');
}
function showMic(on){$('micBtn').classList.toggle('recording',on);$('micLabel').textContent=on?'إيقاف التسجيل':'احكيه بصوتك';$('recIndicator').hidden=!on}
async function recordWithScribe(){let stream;try{stream=await navigator.mediaDevices.getUserMedia({audio:true});let chunks=[];const recorder=new MediaRecorder(stream);state.recorder=recorder;state.recording=true;showMic(true);recorder.ondataavailable=e=>{if(e.data.size)chunks.push(e.data)};recorder.onstop=async()=>{stream.getTracks().forEach(t=>t.stop());state.recording=false;showMic(false);try{const blob=new Blob(chunks,{type:recorder.mimeType||'audio/webm'});const form=new FormData();form.append('file',blob,'scenario.webm');toaste('أحوّل التسجيل إلى نص...');const res=await fetch('/api/transcribe',{method:'POST',body:form});const d=await res.json();if(!res.ok)throw Error(d.detail);$('scenarioInput').value=[state.message,d.text].filter(Boolean).join(' ');state.message=$('scenarioInput').value;setContextMood();toaste('تم تحويل الصوت؛ راجعي النص')}catch{toaste('فشل تفريغ الصوت، جربي الكتابة')}};recorder.start()}catch{if(stream)stream.getTracks().forEach(t=>t.stop());toaste('اسمحي بالوصول للميكروفون ثم حاولي مرة ثانية')}}
async function checkCapabilities(){
  capabilities={tts:false,stt:false,model_mode:'static-demo',voice_name:'صوت المتصفح'};
  $('voiceMetaText').textContent='عرض تجريبي · صوت المتصفح';
  $('dataBadge').textContent='DEMO · بدون مودل';
}

function initStageWebgl(){const c=$('stageWebgl'); if(!c) return; const gl=c.getContext('webgl',{premultipliedAlpha:true,antialias:true}); if(!gl) return; const vert=`attribute vec2 p;void main(){gl_Position=vec4(p,0.0,1.0);}`; const frag=`precision mediump float; uniform vec2 r; uniform float t; void main(){ vec2 uv=(gl_FragCoord.xy*2.0-r)/min(r.x,r.y); float d=length(uv); float a=0.18/(d*2.2+0.22); vec2 p1=uv-vec2(0.35*sin(t*0.6),0.18*cos(t*0.7)); vec2 p2=uv+vec2(0.28*cos(t*0.45),0.22*sin(t*0.5)); float g1=0.16/((length(p1)*3.0)+0.18); float g2=0.13/((length(p2)*3.0)+0.18); vec3 col=vec3(0.72,0.44,0.95)*a + vec3(1.0,0.67,0.84)*g1 + vec3(0.62,0.40,0.90)*g2; gl_FragColor=vec4(col, min(0.55, a+g1+g2));}`; function compile(type,src){const s=gl.createShader(type); gl.shaderSource(s,src); gl.compileShader(s); return s;} const prog=gl.createProgram(); gl.attachShader(prog,compile(gl.VERTEX_SHADER,vert)); gl.attachShader(prog,compile(gl.FRAGMENT_SHADER,frag)); gl.linkProgram(prog); gl.useProgram(prog); const buf=gl.createBuffer(); gl.bindBuffer(gl.ARRAY_BUFFER,buf); gl.bufferData(gl.ARRAY_BUFFER,new Float32Array([-1,-1,1,-1,-1,1,1,1]),gl.STATIC_DRAW); const loc=gl.getAttribLocation(prog,'p'); gl.enableVertexAttribArray(loc); gl.vertexAttribPointer(loc,2,gl.FLOAT,false,0,0); const rLoc=gl.getUniformLocation(prog,'r'); const tLoc=gl.getUniformLocation(prog,'t'); function resize(){const dpr=Math.min(window.devicePixelRatio||1,2); const w=c.clientWidth||c.parentElement.clientWidth; const h=c.clientHeight||c.parentElement.clientHeight; c.width=w*dpr; c.height=h*dpr; gl.viewport(0,0,c.width,c.height);} resize(); window.addEventListener('resize',resize); function draw(ms){gl.clearColor(0,0,0,0); gl.clear(gl.COLOR_BUFFER_BIT); gl.uniform2f(rLoc,c.width,c.height); gl.uniform1f(tLoc,ms*0.001); gl.drawArrays(gl.TRIANGLE_STRIP,0,4); requestAnimationFrame(draw);} requestAnimationFrame(draw);}
bind();renderIntro(false);checkCapabilities();initStageWebgl();
