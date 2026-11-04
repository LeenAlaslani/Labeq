/* LABEQ V10 — the approved character illustration is the only facial artwork.
   We never re-draw eyebrows, eyes, cheeks, nose, or a synthetic O-shaped mouth.
   The full original smile is always present at rest. */
(()=>{
  'use strict';
  const canvas=document.getElementById('character2d');
  if(!canvas)return;
  const ctx=canvas.getContext('2d',{alpha:true});
  if(!ctx)return;
  const names={
    face:'assets/maha_body_original_face.png',
    blink:'assets/maha_body_blink.png',
    arm:'assets/maha_character_arm.png',
    clean:'assets/maha_mouth_clean_overlay.png',
    mouth:'assets/maha_mouth_open.png'
  };
  const imgs={};
  let loaded=0;
  for(const [key,url] of Object.entries(names)){
    const im=new Image();imgs[key]=im;
    im.onload=()=>loaded++;
    im.onerror=()=>console.warn('Could not load character asset:',key);
    im.src=url;
  }
  const reduceMotion=window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  const clamp=(v,a,b)=>Math.max(a,Math.min(b,v));
  const s={mood:'greet',talking:false,mouth:0,mouthTarget:0,lookX:0,lookY:0,blinkAt:-9999,blinkDuration:165,reactAt:0};
  let raf;
  function blinkWeight(now){
    const p=(now-s.blinkAt)/s.blinkDuration;
    if(p<0||p>1)return 0;
    return Math.pow(Math.sin(Math.PI*p),1.22);
  }
  function mouthOverlay(){
    const open=clamp(s.mouth,0,1);
    if(!s.talking && open<.025)return;
    // Restore smooth skin under lips *only during speech*; no synthetic mouth at rest.
    const strength=clamp(open*.95+.12,0,1);
    ctx.save();
    ctx.globalAlpha=strength;
    ctx.drawImage(imgs.clean,0,0,704,650);
    // The lips themselves are cropped from the user-approved original artwork.
    const scaleY=.68+.31*open;
    const scaleX=.94+.055*open;
    ctx.translate(397,353);
    ctx.scale(scaleX,scaleY);
    ctx.drawImage(imgs.mouth,-60,-40,122,83);
    ctx.restore();
  }
  function frame(ms){
    raf=requestAnimationFrame(frame);
    if(loaded!==Object.keys(names).length)return;
    const t=ms/1000;
    s.mouth += (s.mouthTarget-s.mouth)*.20;
    if(!s.talking && s.mouth<.015)s.mouth=0;
    const floatY=reduceMotion?0:Math.sin(t*1.15)*1.3;
    const reactEase=Math.max(0,1-(performance.now()-s.reactAt)/750);
    const surprised=s.mood==='surprised';
    const think=s.mood==='think';
    const sorry=s.mood==='sorry';
    const headTilt=(think?.009:0)+(sorry?-.008:0)+(surprised?-.006*reactEase:0);
    ctx.clearRect(0,0,704,650);
    ctx.save();
    ctx.translate(352+s.lookX*2.1,326+s.lookY*1.4+floatY);
    ctx.rotate(headTilt);
    ctx.translate(-352,-326);
    ctx.drawImage(imgs.face,0,0,704,650);
    const blink=Math.min(1,blinkWeight(performance.now())*1.7);
    if(blink>.01){ctx.save();ctx.globalAlpha=blink;ctx.drawImage(imgs.blink,0,0,704,650);ctx.restore()}
    mouthOverlay();
    // Arm is still the original illustrated hand, not a reconstructed vector limb.
    ctx.save();
    ctx.translate(488,510);
    let angle=0;
    if(!reduceMotion){
      if(s.talking)angle=Math.sin(t*2.9)*.032;
      else if(s.mood==='greet')angle=Math.sin(t*1.95)*.026;
      else if(s.mood==='happy')angle=Math.sin(t*1.6)*.022;
      else if(surprised)angle=-.028*reactEase;
      else angle=Math.sin(t*1.1)*.008;
    }
    ctx.rotate(angle);ctx.translate(-488,-510);
    ctx.drawImage(imgs.arm,0,0,704,650);
    ctx.restore();
    ctx.restore();
  }
  raf=requestAnimationFrame(frame);
  window.labeqCharacter={
    setMood(value){
      if(!value||s.mood===value)return;
      s.mood=value;
      s.reactAt=performance.now();
    },
    setSpeaking(value){s.talking=!!value;if(!s.talking)s.mouthTarget=0;},
    setMouth(value){s.mouthTarget=clamp(Number(value)||0,0,1);},
    setLook(x,y){s.lookX=clamp(Number(x)||0,-1,1);s.lookY=clamp(Number(y)||0,-1,1);},
    blink(){s.blinkAt=performance.now();},
    transition(){
      const w=document.getElementById('avatarWrap');
      w.classList.add('leaving');
      setTimeout(()=>{w.classList.remove('leaving');w.classList.remove('reveal');void w.offsetWidth;w.classList.add('reveal')},630);
    }
  };
})();
