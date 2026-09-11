const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const http = require('node:http');
const handler = require('../api/redirect');
const health = require('../api/health');
const targets = require('../data/targets.json');
const {safeUrl} = require('../lib/security');
const ids = Object.keys(targets);
function call(query, method='GET', fn=handler) {
  const r={headers:{},setHeader(k,v){this.headers[k]=v;},status(v){this.code=v;return this;},end(){return this;},json(v){this.body=v;return this;}};
  fn({query,method},r);return r;
}
test('allowlist exactly matches verified safe input',()=>{
 const rows=JSON.parse(fs.readFileSync(path.join(__dirname,'../../outputs/phase2_3/samples/safe_content.json'),'utf8'));
 assert.equal(rows.length,8);assert.deepEqual(targets,Object.fromEntries(rows.map(x=>[x.safe_event_id,x.safe_original_url])));
});
test('all eight exact 302 locations',()=>{for(const id of ids){const r=call({event_id:id});assert.equal(r.code,302);assert.equal(r.headers.Location,targets[id]);}});
test('unknown event 404',()=>assert.equal(call({event_id:'evt_ffffffffffffffffffff'}).code,404));
for (const [name,id] of [['missing',undefined],['invalid','not-valid'],['array',[ids[0],ids[1]]],['object',{}],['traversal','../data/targets.json'],['newline',ids[0]+'\n']])
 test(name+' event 400',()=>assert.equal(call({event_id:id}).code,400));
test('URL query cannot override allowlist',()=>{const r=call({event_id:ids[0],url:'https://evil.invalid'});assert.equal(r.headers.Location,targets[ids[0]]);});
test('URL-only open redirect rejected',()=>assert.equal(call({url:'https://evil.invalid'}).code,400));
test('POST 405 without Location',()=>{const r=call({event_id:ids[0]},'POST');assert.equal(r.code,405);assert.equal(r.headers.Location,undefined);});
test('HEAD exact redirect',()=>assert.equal(call({event_id:ids[0]},'HEAD').headers.Location,targets[ids[0]]));
test('security headers on successes and errors',()=>{for(const id of [ids[0],'bad','evt_ffffffffffffffffffff']){const r=call({event_id:id});assert.equal(r.headers['Cache-Control'],'no-store');assert.equal(r.headers['Referrer-Policy'],'no-referrer');assert.equal(r.headers['X-Content-Type-Options'],'nosniff');}});
test('unsafe configured target fails closed',()=>{const original=targets[ids[0]];try{for(const v of ['http://evil.invalid','javascript:alert(1)','https://u:p@evil.invalid','https://evil.invalid/\r\nX:a']){targets[ids[0]]=v;assert.equal(call({event_id:ids[0]}).code,500);}}finally{targets[ids[0]]=original;}});
test('https URL policy',()=>{assert.equal(safeUrl('https://example.org/a?q=1'),true);for(const s of ['//example.org','https://example.org:444','https://example.org/#x','https://example.org\\evil'])assert.equal(safeUrl(s),false);});
test('health GET',()=>assert.equal(call({},'GET',health).body.ok,true));
test('health method blocked',()=>assert.equal(call({},'POST',health).code,405));
test('public root exists',()=>assert.match(fs.readFileSync(path.join(__dirname,'../public/index.html'),'utf8'),/<html/i));
test('local HTTP handlers and rewrite routes',async()=>{
 const config=require('../vercel.json');assert.equal(config.rewrites[0].source,'/r/:event_id');assert.equal(config.rewrites[0].destination,'/api/redirect?event_id=:event_id');
 const server=http.createServer((req,res)=>{
  const u=new URL(req.url,'http://localhost');res.status=n=>{res.statusCode=n;return res;};res.json=v=>res.end(JSON.stringify(v));
  if(u.pathname==='/health')return health(req,res);
  if(u.pathname==='/')return res.end(fs.readFileSync(path.join(__dirname,'../public/index.html')));
  req.query={event_id:decodeURIComponent(u.pathname.slice(3))};return handler(req,res);
 });
 await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
 try{const base='http://127.0.0.1:'+server.address().port;
  for(const id of ids){const v=await fetch(base+'/r/'+id,{redirect:'manual'});assert.equal(v.status,302);assert.equal(v.headers.get('location'),targets[id]);}
  for(const [p,s] of [['/health',200],['/',200],['/r/not-valid',400],['/r/evt_ffffffffffffffffffff',404]])assert.equal((await fetch(base+p)).status,s);
 }finally{await new Promise(resolve=>server.close(resolve));}
});
