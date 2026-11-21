const fs = require('fs');
const vm = require('vm');
const assert = require('assert');

async function run(events) {
  const calls = [];
  const encoded = new TextEncoder().encode(events);
  let position = 0;
  const context = {
    window: {}, TextDecoder, AbortController, setTimeout, clearTimeout,
    fetch: async (url, options = {}) => {
      calls.push({url, options});
      if (options.method === 'POST') {
        return {ok: true, json: async () => ({event_id: 'queued-event'})};
      }
      return {ok: true, body: {getReader: () => ({
        read: async () => {
          if (position >= encoded.length) return {done: true};
          const value = encoded.slice(position, position + 3);
          position += 3;
          return {done: false, value};
        },
        cancel: async () => {}
      })}};
    }
  };
  vm.runInNewContext(fs.readFileSync(__dirname + '/../space_client.js', 'utf8'), context);
  const reply = await context.window.labeqSpaceReply({
    message: 'عندي شغلي', relation: 'work', goal: 'أوضح حدودي',
    style_key: 'firm', tone: 'formal', instruction: 'اختصري',
    history: [{role: 'assistant', content: 'الرد السابق'}]
  });
  const sent = JSON.parse(calls[0].options.body).data[0];
  assert.strictEqual(sent.goal, 'أوضح حدودي');
  assert.strictEqual(sent.style, 'حازم');
  assert.strictEqual(sent.history.length, 3);
  assert.strictEqual(reply.style, 'firm');
  assert.strictEqual(reply.mock, false);
  return reply;
}

(async () => {
  const result = {reply: 'ما أقدر أساعد كل يوم', style_key: 'firm', reply_source: 'qwen_lora_generated'};
  const reply = await run('event: heartbeat\r\ndata: null\r\n\r\nevent: complete\r\ndata: ' + JSON.stringify([result]) + '\r\n\r\n');
  assert.strictEqual(reply.reply, result.reply);
  for(const source of ['qwen_base_generated','ollama_generated']){
    const actual={...result,reply_source:source};
    assert.strictEqual((await run('event: complete\ndata: '+JSON.stringify([actual])+'\n\n')).reply_source,source);
  }
  for(const invalid of [{...result,mock:true},{...result,reply_source:'template'},{...result,reply:''},{...result,reply:null}]){
    await assert.rejects(run('event: complete\ndata: '+JSON.stringify([invalid])+'\n\n'),/استجابة غير صالحة/);
  }
  await assert.rejects(run('event: error\ndata: "quota"\n\n'), /انتهت حصة GPU/);
  await assert.rejects(run('event: error\ndata: {"error":"You have exceeded your ZeroGPU runs limit"}\n\n'), /تسجيل الدخول/);
  await assert.rejects(run('event: error\ndata: {"error":"GenerationBudgetError"}\n\n'), /تعذّر توليد رد مكتمل/);
  await assert.rejects(run('event: heartbeat\ndata: null\n\n'), /قبل اكتمال الرد/);
  console.log('Space client queue tests: PASS');
})().catch(error => { console.error(error); process.exitCode = 1; });
