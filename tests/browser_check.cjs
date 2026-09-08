// Optional: Node.js + Playwright. Test in an isolated profile, not a user's attempt.
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const fs = require('node:fs');
const path = require('node:path');
const { pathToFileURL } = require('node:url');
const crypto = require('node:crypto');
const assert = require('node:assert/strict');
const file = path.resolve(process.argv[2]);
const out = path.resolve(process.argv[3] || 'test-output');
fs.mkdirSync(out, {recursive:true});
(async()=>{
 const browser=await chromium.launch({headless:true,...(process.env.BROWSER_EXECUTABLE?{executablePath:process.env.BROWSER_EXECUTABLE}:{})});
 const passed=[], errors=[], requests=[];
 const ok=(name,test)=>{assert.ok(test,name);passed.push(name);};
 let context,page;
 async function fresh(width=1440,blocked=false){
  if(context)await context.close();
  context=await browser.newContext({offline:true,viewport:{width,height:900}});
  page=await context.newPage();page.on('pageerror',e=>errors.push(e.message));
  page.on('request',r=>{if(/^https?:/.test(r.url()))requests.push(r.url());});
  if(blocked)await page.addInitScript(()=>{Object.defineProperty(Storage.prototype,'setItem',{value(){throw new Error('blocked for test')}});});
  await page.goto(pathToFileURL(file).href);
 }
 async function fill(mode){await page.evaluate(mode=>{const data=JSON.parse(document.querySelector('#exam-data').textContent);for(const q of data.questions){if(mode==='partial'&&q.number>2)continue;let answer=q.answer;if(mode==='wrong'||(mode==='partial'&&q.number===2))answer='ABCD'[('ABCD'.indexOf(answer)+1)%4];const el=document.querySelector(`input[name=q${q.number}][value=${answer}]`);el.checked=true;el.dispatchEvent(new Event('change',{bubbles:true}));}},mode);}
 async function submit(){await page.locator('#submit').click();await page.locator('#confirm-action').click();}
 try{
  await fresh();ok('离线首页可见',await page.locator('#start').isVisible());await page.screenshot({path:path.join(out,'home.png')});
  await page.locator('#start').click();const n=await page.locator('.question').count();ok('题量完整',n===100);ok('提交前隐藏解析',await page.locator('.analysis').count()===0);ok('提交前隐藏考点',await page.locator('.tags').count()===0);
  await page.locator('input[name=q1][value=A]').check();await page.reload();ok('刷新保留选择',await page.locator('input[name=q1][value=A]').isChecked());
  await page.locator('#submit').click();ok('提前交卷提示未答', (await page.locator('#dialog-description').innerText()).includes('99'));await page.locator('#cancel-action').click();
  await fill('correct');await submit();ok('全对100分',(await page.locator('.score-ring strong').innerText())==='100');ok('全部解析在题下',await page.locator('.question .analysis').count()===n);ok('所有选项锁定',await page.locator('input[type=radio]:disabled').count()===n*4);await page.reload();ok('刷新保留成绩',await page.locator('#results').isVisible());
  await page.locator('#restart').click();await page.locator('#cancel-action').click();ok('取消重考保留成绩',await page.locator('#results').isVisible());await page.locator('#restart').click();await page.locator('#confirm-action').click();ok('重考清空选择',await page.locator('input:checked').count()===0);
  await fill('wrong');await submit();ok('全错0分',(await page.locator('.score-ring strong').innerText())==='0');
  await fresh();await page.locator('#start').click();await fill('partial');await submit();ok('部分作答1分',(await page.locator('.score-ring strong').innerText())==='1');ok('未答题明确显示',(await page.locator('#q3 .analysis').innerText()).includes('你未作答'));
  await fresh();await page.locator('#start').click();await page.goto('about:blank');await page.addInitScript(()=>{const key=Object.keys(localStorage).find(k=>k.startsWith('sz-practice:'));if(!key)return;const s=JSON.parse(localStorage.getItem(key));s.startedAt-=91*60000;s.deadline-=91*60000;localStorage.setItem(key,JSON.stringify(s));});await page.goto(pathToFileURL(file).href);ok('关闭期间超时后重开自动交卷',(await page.locator('#timer').innerText())==='00:00');await page.waitForTimeout(600);ok('超时仅一份成绩',await page.locator('.score-ring').count()===1);
  await fresh(375,true);await page.locator('#start').click();ok('存储受限警告',await page.locator('#notice').isVisible());await submit();ok('存储受限仍能评分',await page.locator('#results').isVisible());
  for(const width of [320,375,768,1440]){
   await fresh(width);await page.locator('#start').click();ok(`${width}页面无横向溢出`,await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));
   await page.locator('#q21').scrollIntoViewIfNeeded();await page.locator('#q21 [data-zoom]').click();ok(`${width}图形放大`,await page.locator('#zoom-dialog').isVisible());await page.locator('#close-zoom').click();
   await page.locator('#material-M2 button').click();ok(`${width}资料图放大`,await page.locator('#zoom-dialog').isVisible());await page.locator('#close-zoom').click();
   if(width<960){await page.locator('#toggle-card').click();ok(`${width}手机答题卡展开`,await page.locator('#answer-card').evaluate(e=>e.open));await page.locator('[data-nav="50"]').click();ok(`${width}跳题后收起`,!(await page.locator('#answer-card').evaluate(e=>e.open)));}
   await page.locator('#q21').scrollIntoViewIfNeeded();await page.screenshot({path:path.join(out,`figure-${width}.png`)});
   await page.locator('#material-M3').scrollIntoViewIfNeeded();await page.screenshot({path:path.join(out,`table-${width}.png`)});
   await fill('partial');await submit();await page.locator('#q1').scrollIntoViewIfNeeded();await page.screenshot({path:path.join(out,`review-${width}.png`)});
  }
  ok('无脚本异常',errors.length===0);ok('无需网络资源',requests.length===0);
  fs.writeFileSync(path.join(out,'browser-results.json'),JSON.stringify({file,sha256:crypto.createHash('sha256').update(fs.readFileSync(file)).digest('hex'),passed:passed.length,checks:passed,errors,requests},null,2));
  process.stdout.write(`Passed ${passed.length} browser checks\n`);
 }finally{await browser.close();}
})().catch(e=>{process.stderr.write(e.stack+'\n');process.exitCode=1;});
