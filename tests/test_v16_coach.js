const fs=require('fs'),vm=require('vm'),assert=require('assert');
const nodes={};
function E(tag='div') {return {tag,hidden:false,open:false,children:[],textContent:'',className:'',type:'',
  addEventListener(type,fn){this.click=fn},querySelector(){return this.notice},
  replaceChildren(...x){this.children=x},append(...x){this.children.push(...x)},appendChild(x){this.children.push(x)}}}
for(const i of ['coachLearning','coachGlimpse','coachWhy','coachWatch','coachCompareCards','coachInsight','coachCompare','replyOptions','changeStyleBtn'])nodes[i]=E();
nodes.coachLearning.notice=E('p');nodes.changeStyleBtn.click=()=>{nodes.changed=true};
const ctx={window:{},document:{getElementById:id=>nodes[id],createElement:E}};
vm.runInNewContext(fs.readFileSync(__dirname+'/../coach.js','utf8'),ctx);
const sync=ctx.window.labeqCoach.syncResult;
sync({coaching:{strategy:'ابدئي بالاعتراف بمخاوفه ثم اطلبي حقك',core:'خلاف في جدول المهام',risk:'لا تفترضي موافقة مسبقة'},isDemo:false});
assert.strictEqual(nodes.coachLearning.hidden,false);
assert(nodes.coachGlimpse.textContent.includes('حقك'));
assert(nodes.coachWhy.textContent.includes('خلاف'));
assert(nodes.coachWatch.textContent.includes('موافقة'));
assert.strictEqual(nodes.coachCompareCards.children.length,2);
assert(!nodes.coachCompareCards.children.some(c=>c.textContent.includes('أحب أساعدك')));
nodes.coachCompareCards.children[1].click();
assert(nodes.changed);assert(nodes.replyOptions.open);
sync({coaching:{},isDemo:false});assert.strictEqual(nodes.coachLearning.hidden,true);
console.log('V16 dynamic coaching tests: PASS');
