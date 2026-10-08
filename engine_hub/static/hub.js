'use strict';
let me, csrf, conversation=null, stateHash=null, refreshTimer, activeTab='chat', currentRelease=null;
const $=id=>document.getElementById(id);
const roles={admin:'管理员',viewer:'只读',chat:'问答'};
const errors={capability_denied:'该账号没有此操作权限',clarification_required:'请明确引擎或已登记实例；当前信息不足以选择空间。',no_eligible_node:'当前空间没有可用节点，请稍后再试。',conversation_busy:'当前回答仍在运行，请等待或取消。',session_expired:'登录已过期，请重新登录。',stale_base:'批准版本已变化，请重新评测候选。',state_conflict:'远端内容已被修改，请重新读取。',release_revoked:'该版本已撤回，拒绝继续消费。'};
async function api(path,method='GET',body){
  const response=await fetch('/api'+path,{method,headers:{'Content-Type':'application/json',...(method!=='GET'?{'X-CSRF-Token':csrf||''}:{})},body:body===undefined?undefined:JSON.stringify(body)});
  const data=await response.json();
  if(!response.ok) throw new Error(errors[data.error]||data.error||'请求失败');
  return data;
}
function notice(error){$('notice').textContent=error?.message||error||'';}
function node(tag,text,className){const element=document.createElement(tag);element.textContent=text;if(className)element.className=className;return element;}
function options(id,values,includeAuto=false){const select=$(id);select.replaceChildren();if(includeAuto)select.append(new Option('自动识别 · 有歧义时澄清',''));for(const value of values)select.append(new Option(value.toUpperCase(),value));}
async function boot(identity){
  me=identity.user;csrf=identity.csrf;$('login').hidden=true;$('app').hidden=false;
  $('identity').textContent=me.id+' · '+roles[me.role];
  $('composer').hidden=me.role==='viewer';$('new-chat').hidden=me.role==='viewer';$('viewer-note').hidden=me.role!=='viewer';$('admin-nav').hidden=me.role!=='admin';
  $('candidate-panel').hidden=!me.extra.includes('candidate');$('review-panel').hidden=!me.extra.includes('publish');
  options('engine',me.engines,true);options('asset-engine',me.engines);
  await refresh();clearInterval(refreshTimer);refreshTimer=setInterval(()=>refresh().catch(notice),4000);
}
async function refresh(){
  const summary=await api('/summary');
  $('model-mode').textContent=Object.values(summary.model_modes||{}).includes('codex-luna-bridge')?'PG 回答使用 Codex Luna；其它空间使用协议 fixture':'回答使用确定性协议 fixture';
  $('nodes').replaceChildren();
  for(const n of summary.nodes){const card=node('article','', 'card');card.append(node('div',n.engine.toUpperCase(),'eyebrow'),node('h2',n.id),node('div',n.online?'● 在线':'○ 离线',n.online?'online':'offline'),node('p','Hermes '+(n.version||'未知')+' · '+(n.enabled?'接收新任务':'已排空')));$('nodes').append(card);}
  $('conversations').replaceChildren();
  for(const c of summary.conversations.slice().reverse()){const button=node('button',c.title);button.dataset.conversation=c.id;button.onclick=()=>openConversation(c.id);$('conversations').append(button);}
  if(conversation){const c=await api('/conversations/'+conversation.id);conversation=c;renderConversation(c);}
}
function renderConversation(c){
  $('conversation-title').textContent=c.title;$('share').hidden=c.owner!==me.id||me.role==='viewer';
  $('binding').textContent=c.engine.toUpperCase()+' / '+c.space+' · 会话已绑定';
  $('messages').replaceChildren();
  for(const turn of c.turns){const run=c.runs?.find(r=>r.id===turn.run);const card=node('article','', 'turn');card.append(node('div',turn.text,'user-text'));
    if(run){card.append(node('div',`${run.engine} / ${run.node} · ${run.status} · ${run.model||'webui-node-fixture'} · ${run.id}`,'meta'),node('div',`知识 / Skill: ${run.knowledge_release} · SHA ${run.report_sha256||'等待报告'}`,'meta'));
      const settled=['completed','cancelled','failed','expired','interrupted'].includes(run.status);
      card.append(node('pre',run.report||(run.status==='cancelled'?'回答已取消。':settled?'本次运行已结束，未产生报告。':'Hermes 正在使用已批准的固定资产版本…'),'report'));
      if(!['completed','cancelled','failed','expired','interrupted'].includes(run.status)&&me.role!=='viewer'&&(run.owner===me.id||me.role==='admin')){const cancel=node('button','取消回答');cancel.dataset.cancel=run.id;cancel.onclick=()=>api('/runs/'+run.id+'/cancel','POST',{}).then(refresh).catch(notice);card.append(cancel);}}
    $('messages').append(card);}
}
async function openConversation(id){conversation=await api('/conversations/'+id);$('engine').value=conversation.engine;$('instance').value='';showTab('chat');renderConversation(conversation);}
function showTab(tab){activeTab=tab;for(const name of ['chat','overview','assets','admin'])$('tab-'+name).hidden=name!==tab;for(const button of document.querySelectorAll('nav button'))button.classList.toggle('selected',button.dataset.tab===tab);if(tab==='assets')loadAssets().catch(notice);if(tab==='admin')loadAdmin().catch(notice);}
async function loadAssets(){const e=$('asset-engine').value;currentRelease=await api('/assets/'+e+'/current');const release=await api('/assets/'+e+'/releases/'+currentRelease.id);const area=$('asset-content');area.replaceChildren(node('p','批准版本 '+release.id+' · '+release.bundle_sha256,'meta'),node('h2','远端知识'),node('pre',release.content.knowledge.content,'report'),node('h2','Skill 包'));const p=JSON.parse(release.content.skill.content);area.append(node('pre',p['SKILL.md']+'\n\n'+p['references/method.md'],'report'),node('p','内容来自远端 WeKnora；执行节点仅保存不可变缓存。'));}
async function loadAdmin(){const cfg=await api('/config');const area=$('config');area.replaceChildren();for(const n of cfg.nodes){const card=node('article','', 'card');card.append(node('h2',n.engine+' / '+n.id),node('p',n.gateway_url+' · 并发上限 '+n.max_running));const button=node('button',n.enabled?'排空节点':'恢复接收');button.onclick=()=>api('/config','PATCH',{node:n.id,enabled:!n.enabled}).then(loadAdmin).catch(notice);card.append(button);area.append(card);}options('state-node',cfg.nodes.map(n=>n.id));$('diagnostics').textContent=JSON.stringify(await api('/diagnostics'),null,2);}
$('login-form').onsubmit=async event=>{event.preventDefault();try{const identity=await api('/login','POST',{username:$('username').value,password:$('password').value});$('password').value='';await boot(identity);}catch(e){$('login-error').textContent=e.message;}};
$('composer').onsubmit=async event=>{event.preventDefault();$('send').disabled=true;notice('');try{const result=await api('/ask','POST',{text:$('question').value,engine:$('engine').value||undefined,instance:$('instance').value||undefined,conversation:conversation?.id,input_revision:crypto.randomUUID()});conversation=result.conversation;$('question').value='';await refresh();}catch(e){notice(e);}finally{$('send').disabled=false;}};
$('new-chat').onclick=()=>{conversation=null;$('messages').replaceChildren();$('conversation-title').textContent='开始一次问答';$('binding').textContent='服务端授权、路由并固定资产版本';$('engine').value='';$('instance').value='';$('share').hidden=true;showTab('chat');};
$('logout').onclick=()=>api('/logout','POST',{}).then(()=>location.reload()).catch(notice);
$('share').onclick=async()=>{const names=prompt('只读共享给哪些已登记账号？用逗号分隔；空白撤销共享。');if(names===null)return;try{await api('/conversations/'+conversation.id+'/share','POST',{users:names.split(',').map(x=>x.trim()).filter(Boolean)});notice('授权共享已更新。');}catch(e){notice(e);}};
for(const button of document.querySelectorAll('nav button'))button.onclick=()=>showTab(button.dataset.tab);
$('asset-engine').onchange=()=>loadAssets().catch(notice);
$('candidate-submit').onclick=async()=>{try{const engine=$('asset-engine').value;const result=await api('/assets/'+engine+'/candidates','POST',{source:{run:$('source-run').value},knowledge:$('candidate-knowledge').value,package:{'SKILL.md':$('candidate-method').value,'references/method.md':'Synthetic method; verify evidence before action.','scripts/probe.py':'print("approved synthetic method executed")'},share_consent:$('consent').checked,base:currentRelease.id,origin:'MANUAL_SYNTHETIC'});notice('远端候选已提交：'+result.id);}catch(e){notice(e);}};
$('evaluate').onclick=()=>api('/assets/'+$('asset-engine').value+'/candidates/'+$('review-id').value+'/evaluate','POST',{passed:true,evidence:['MANUAL_FUNCTIONAL_REVIEW_NOT_SEMANTIC_ACCEPTANCE']}).then(()=>notice('已记录功能评测，领域质量仍未验收。')).catch(notice);
$('approve').onclick=()=>api('/assets/'+$('asset-engine').value+'/candidates/'+$('review-id').value+'/approve','POST',{base:currentRelease.id}).then(async()=>{notice('批准发布已写入远端并读回。');await loadAssets();}).catch(notice);
$('state-read').onclick=async()=>{try{const result=await api('/nodes/'+$('state-node').value+'/state/'+$('state-kind').value);stateHash=result.sha256;$('state-content').value=result.content;}catch(e){notice(e);}};
$('state-write').onclick=async()=>{try{const result=await api('/nodes/'+$('state-node').value+'/state/'+$('state-kind').value,'PUT',{base_sha256:stateHash,content:$('state-content').value});stateHash=result.sha256;notice('远端写回并读回成功：'+result.sha256);}catch(e){notice(e);}};
api('/me').then(boot).catch(()=>{});
