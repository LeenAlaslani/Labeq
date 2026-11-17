/* LABEQ V15 Communication Coach.
   Teaching examples are contextual editorial templates, NOT Faisal predictions
   and NOT Qwen generations. For unfamiliar scenarios, show effects only. */
(()=>{
'use strict';
const byId=id=>document.getElementById(id);
const styles={
  polite:{name:'لبق',why:'يساعدك توصلين موقفك بدون ما تجرحين الطرف الثاني.',watch:'كوني واضحة في حدودك، ولا تتركيه يفهم أن القرار مؤقت إذا ما كان كذلك.',effect:'يوصل الرفض أو الطلب باحترام.'},
  firm:{name:'حازم',why:'يناسب لما تحتاجين توضحين حدودك بدون هجوم.',watch:'الحزم ما يعني القسوة؛ وضحي السبب بدون اتهامات.',effect:'يخلي حدودك واضحة للطرف الثاني.'},
  diplomatic:{name:'دبلوماسي',why:'يفيد إذا ودّك تحافظين على العلاقة وتفتحين باب التفاهم.',watch:'الهدوء مو معناه تتنازلين عن اللي تبغينه.',effect:'يفتح مساحة للتفاهم بدل التصعيد.'},
  apology:{name:'اعتذار',why:'مناسب إذا كان منك خطأ واضح وتبغين تصلحينه.',watch:'لا تتحملين مسؤولية شيء ما سويتيه.',effect:'يعترف بالخطأ عندما يكون منك فعلًا.'},
  clarify:{name:'طلب توضيح',why:'مناسب لما تحتاجين تفهمين المقصود قبل اتخاذ موقف.',watch:'اختاري سؤالًا محددًا يخدم هدفك.',effect:'يساعد على فهم المقصود قبل الرد.'}
};
const alternatives={polite:'firm',firm:'polite',diplomatic:'firm',apology:'diplomatic',clarify:'diplomatic'};
const frequent=/كل\s*(?:يوم|مر[ةه]|شوي|أسبوع|اسبوع|وقت)|دايم|دائم|باستمرار|بشكل\s*مستمر|متكرر|تتكرر|يتكرر|على\s*طول/;
const help=/(?:ساعد|مساعد|شغل|مهام|مهمة|مهامك|طلب|طلبات)/;
const money=/(?:سلف|فلوس|مبلغ|اقرض|أقرض|قرض|دين)/;
const conflict=/(?:خلاف|زعل|تزاعل|تهاوش|تصالح|سوء\s*فهم|تضارب|تخاصم)/;
const admittedMistake=/(?:أنا\s*غلطت|انا\s*غلطت|غلطتي|خطئي|أخطأت|اخطأت|أنا\s*السبب)/;
function inspect(message,goal){
 const m=(message||'').trim();
 const repeated=frequent.test(m);
 const isRefusal=['polite','firm'].includes(goal)||/(?:ما\s*أقدر|أرفض|ارفض|ما\s*أبي|ما\s*ابغى)/.test(m);
 const work=/(?:عندي\s*شغلي|عندي\s*مهامي|عندي\s*مسؤولياتي|شغلي\s*كثير)/.test(m);
 if(repeated&&isRefusal&&(help.test(m)||money.test(m)))return {type:money.test(m)?'repeat-money':'repeat-help',work};
 if(['diplomatic','apology','clarify'].includes(goal)&&conflict.test(m))return {type:'conflict',mistake:admittedMistake.test(m)};
 return {type:'unknown'};
}
function situationExamples(c){
 if(c.type==='repeat-help'){
   const reason=c.work?' وأنا عندي شغلي':'';
   return {
     polite:`أحب أساعدك، بس ما أقدر أساعدك كل مرة${reason}. أتمنى تتفهم.`,
     firm:`أقدّر طلبك، بس ما أقدر أستمر أساعد كل يوم${reason}. لازم تكون هالحدود واضحة بيننا.`,
     diplomatic:`ودي نتفاهم على هالنقطة؛ أحب أساعد وقت ما أقدر، بس مو بشكل يومي${reason}.`,
     apology:`أعتذر إني ما أقدر أساعدك كل مرة${reason}، وأتمنى تتفهم.` ,
     clarify:`عشان نكون واضحين، هل تقصد إنك تحتاج مساعدتي كل يوم؟ لأن ما أقدر ألتزم بهالشي.`
   };
 }
 if(c.type==='repeat-money')return {
   polite:'أقدّر طلبك، بس ما أقدر أسلّف بشكل متكرر. أتمنى تتفهم.',
   firm:'ما أقدر أستمر أسلّف كل مرة، وأحتاج يكون هالشي واضح.',
   diplomatic:'أبي أوضح لك إن السلف المتكرر مو شيء أقدر ألتزم فيه، وأتمنى نتفهم بعض.',
   apology:'آسف إني ما أقدر أستمر في السلف كل مرة، لكن هذي حدودي.',
   clarify:'أبي أفهم، هل تقصد إنك تحتاج سلفة بشكل متكرر؟ لأني ما أقدر ألتزم بهالشي.'
 };
 if(c.type==='conflict')return {
   polite:'ما ودي يطول الزعل بيننا، ودي نتفاهم بهدوء.',
   firm:'خلّنا نتفاهم، بس بالنسبة لي مهم إن الكلام يكون باحترام.',
   diplomatic:'ودي نسمع بعض ونفهم اللي صار، ما أبي يكبر الخلاف.',
   apology:c.mistake?'حقك علي في اللي صار، أدري إني غلطت وأبي أصلح الموضوع.':null,
   clarify:'ودي أفهم وش اللي ضايقك بالضبط عشان نوضح سوء الفهم.'
 };
 return {};
}
function makeCompareCard(style,best,examples){
 const info=styles[style],wrap=document.createElement('div');
 wrap.className='coach-comparison-card'+(best?' best':'');
 const title=document.createElement('strong');title.textContent=(best?'الأسلوب المقترح · ':'بديل محتمل · ')+info.name;
 wrap.appendChild(title);
 if(examples[style]){
   const quote=document.createElement('p');quote.textContent='«'+examples[style]+'»';wrap.appendChild(quote);
 }
 const description=document.createElement('small');description.textContent=info.effect;
 wrap.appendChild(description);return wrap;
}
function syncResult({style,goal,relation,message,isDemo}){
 const wrapper=byId('coachLearning');
 if(!wrapper||!styles[style]){if(wrapper)wrapper.hidden=true;return;}
 wrapper.hidden=false;
 const c=inspect(message,goal),data=styles[style],examples=situationExamples(c);
 let effect=data.effect,why=data.why,watch=data.watch;
 if(c.type==='repeat-help'){
   effect='الموضوع مو رفض اليوم؛ الهدف توضيح إن المساعدة ما تقدر تكون كل مرة.';
   why='لما تتكرر طلبات المساعدة وتبغين تحافظين على العلاقة وفي نفس الوقت تحمين وقتك.';
   watch='لا تقولين «مو اليوم» إذا قصدك إنك ما تقدرين تلتزمين بالمساعدة كل مرة.';
 }else if(c.type==='repeat-money'){
   effect='المطلوب توضيح حد للسلف المتكرر، مو تأجيل سلفة واحدة.';
   why='لما تتكرر طلبات السلف وتبغين توضحين حدودك باحترام.';
   watch='لا توعدين بسلفة لاحقًا إذا هذا مو قصدك.';
 }else if(c.type==='conflict'){
   effect='الهدف تخفيف الزعل وفتح باب حوار، من غير افتراض مين أخطأ.';
   why='لما يكون بينكم زعل وتبغين تفتحين باب التفاهم.';
   watch='لا تعتذرين عن شيء ما ذكرتِ إنك سويتيه.';
 }
 byId('coachGlimpse').textContent=effect;
 byId('coachWhy').textContent=why;
 byId('coachWatch').textContent=watch;
 byId('coachCompareCards').replaceChildren(makeCompareCard(style,true,examples),makeCompareCard(alternatives[style],false,examples));
 const disclaimer=wrapper.querySelector('.coach-disclaimer');
 if(disclaimer){
   disclaimer.textContent=(c.type==='unknown'
     ?'ما عندنا مثال جاهز متوافق مع تفاصيل هذا الموقف؛ يمكنك تجربة أسلوب آخر ضمن قوالب العرض.'
     :'هذي أمثلة تعليمية مرتبطة بنوع موقفك، وليست ردودًا ولّدها Qwen ولا تفسيرًا داخليًا لقرار فيصل.')+(isDemo?' هذه نسخة عرض تجريبية.':'');
 }
}
function exampleFor(message,goal,style){
 const context=inspect(message,goal);
 if(context.type==='conflict'&&goal!=='diplomatic')return null;
 return situationExamples(context)[style]||null;
}
function clearResult(){const wrapper=byId('coachLearning');if(wrapper)wrapper.hidden=true;const insight=byId('coachInsight');if(insight)insight.open=false;const compare=byId('coachCompare');if(compare)compare.open=false;}
function reset(){clearResult();}
window.labeqCoach={syncResult,clearResult,reset,exampleFor};
})();
