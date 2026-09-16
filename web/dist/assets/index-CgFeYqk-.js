(function(){const a=document.createElement("link").relList;if(a&&a.supports&&a.supports("modulepreload"))return;for(const n of document.querySelectorAll('link[rel="modulepreload"]'))t(n);new MutationObserver(n=>{for(const l of n)if(l.type==="childList")for(const p of l.addedNodes)p.tagName==="LINK"&&p.rel==="modulepreload"&&t(p)}).observe(document,{childList:!0,subtree:!0});function s(n){const l={};return n.integrity&&(l.integrity=n.integrity),n.referrerPolicy&&(l.referrerPolicy=n.referrerPolicy),n.crossOrigin==="use-credentials"?l.credentials="include":n.crossOrigin==="anonymous"?l.credentials="omit":l.credentials="same-origin",l}function t(n){if(n.ep)return;n.ep=!0;const l=s(n);fetch(n.href,l)}})();const y=[{key:"name",label:"이름"},{key:"skill",label:"기능"},{key:"damage",label:"피해"},{key:"range",label:"사거리"},{key:"attacks",label:"공격횟수"},{key:"ammo",label:"탄약"},{key:"malfunction",label:"고장"}];function x(e){return Number.isFinite(e)?{half:Math.floor(e/2),fifth:Math.floor(e/5)}:null}function u(e){const a=e.trim();if(a==="")return null;const s=Number(a);return Number.isFinite(s)?Math.trunc(s):null}function v(e){const a={};for(const s of e.skills){const t=s.name.trim(),n=s.value.trim();if(!t||n==="")continue;const l=Number(n);Number.isFinite(l)&&(a[t]=Math.trunc(l))}return{name:e.name.trim(),occupation:e.occupation.trim(),age:u(e.age),sex:e.sex.trim(),residence:e.residence.trim(),birthplace:e.birthplace.trim(),str:u(e.str),dex:u(e.dex),pow:u(e.pow),con:u(e.con),app:u(e.app),edu:u(e.edu),siz:u(e.siz),int:u(e.int),mov:u(e.mov),major_wound:e.majorWound,mp_depleted:e.mpDepleted,weapons:e.weapons.map(s=>Object.fromEntries(y.map(({key:t})=>[t,s[t].trim()]))).filter(s=>s.name!==""),cash:e.cash.trim(),assets:e.assets.trim(),skills:a}}const E=[{key:"str",label:"근력"},{key:"dex",label:"민첩"},{key:"pow",label:"정신력",required:!0},{key:"con",label:"건강"},{key:"app",label:"외모"},{key:"edu",label:"교육"},{key:"siz",label:"크기"},{key:"int",label:"지능"},{key:"mov",label:"이동력"}],f=document.querySelector("#app");function g(){const e=window.location.pathname.split("/").filter(Boolean);return e[e.length-1]??""}function w(e){f.innerHTML="";const a=document.createElement("p");a.className="status status--error",a.textContent=e,f.appendChild(a)}async function L(){const e=g();f.innerHTML='<p class="status">확인 중...</p>';let a;try{a=await fetch(`/api/register/${e}`)}catch{w("네트워크 오류가 발생했습니다. 다시 시도해주세요.");return}if(!a.ok){w("링크가 만료되었거나 유효하지 않습니다. Discord에서 명령어를 다시 실행해주세요.");return}S(e)}function S(e){f.innerHTML=`
    <div class="card">
      <h1>탐사자 등록</h1>
      <p class="form-subtitle">30분간 유효한 1회용 링크입니다. 신중하게 입력해주세요.</p>
      <form id="registration-form">
        <section>
          <h2>기본정보</h2>
          <label>이름 <input type="text" name="name" required /></label>
          <div class="field-grid-2">
            <label>직업 <input type="text" name="occupation" /></label>
            <label>나이 <input type="number" name="age" /></label>
            <label>성별 <input type="text" name="sex" /></label>
            <label>거주지 <input type="text" name="residence" /></label>
            <label>출생지 <input type="text" name="birthplace" /></label>
          </div>
        </section>
        <section>
          <h2>특성치</h2>
          <div class="attribute-grid">
            ${E.map(o=>`<label>${o.label} <input type="number" name="${o.key}"${o.required?" required":""} /></label>`).join("")}
          </div>
        </section>
        <section>
          <h2>상태</h2>
          <label class="checkbox-field">
            <input type="checkbox" name="major_wound" /> 중상 (HP가 한 번에 최대치의 절반 이상 깎임)
          </label>
          <label class="checkbox-field">
            <input type="checkbox" name="mp_depleted" /> 빈사 (MP 소진)
          </label>
        </section>
        <section>
          <h2>무기와 전투</h2>
          <div id="weapon-rows"></div>
          <button type="button" id="add-weapon-row">+ 무기 추가</button>
        </section>
        <section>
          <h2>현금과 자산</h2>
          <label>현금 <input type="text" name="cash" placeholder="예: 현금 약 8만원" /></label>
          <label>자산 <input type="text" name="assets" placeholder="예: 노트북, 카메라, 소형 승용차" /></label>
        </section>
        <section>
          <h2>기능</h2>
          <div id="skill-rows"></div>
          <button type="button" id="add-skill-row">+ 기능 추가</button>
          <button type="button" id="fill-common-skills">자주 쓰는 기능 채우기</button>
        </section>
        <p id="form-error" class="status status--error" hidden></p>
        <button type="submit">등록하기</button>
      </form>
    </div>
  `;const a=document.querySelector("#skill-rows"),s=document.querySelector("#weapon-rows"),t=document.querySelector("#form-error"),n=document.querySelector("#registration-form");function l(o="",r=""){const c=document.createElement("div");c.className="skill-row";const d=document.createElement("input");d.type="text",d.dataset.role="skill-name",d.placeholder="기능명",d.ariaLabel="기능명",d.value=o;const i=document.createElement("input");i.type="number",i.dataset.role="skill-value",i.placeholder="값",i.ariaLabel="값",i.value=r;const m=document.createElement("span");m.className="skill-half-fifth";const k=()=>{const h=x(Number(i.value));m.textContent=h?`절반 ${h.half} / 1/5 ${h.fifth}`:""};i.addEventListener("input",k),k();const b=document.createElement("button");b.type="button",b.textContent="삭제",b.addEventListener("click",()=>c.remove()),c.append(d,i,m,b),a.appendChild(c)}function p(){const o=document.createElement("div");o.className="weapon-row";for(const{key:c,label:d}of y){const i=document.createElement("input");i.type="text",i.dataset.role=c,i.placeholder=d,i.ariaLabel=`무기 ${d}`,o.appendChild(i)}const r=document.createElement("button");r.type="button",r.textContent="삭제",r.addEventListener("click",()=>o.remove()),o.appendChild(r),s.appendChild(o)}document.querySelector("#add-skill-row").addEventListener("click",()=>l()),document.querySelector("#add-weapon-row").addEventListener("click",()=>p()),document.querySelector("#fill-common-skills").addEventListener("click",async()=>{const o=new Set(Array.from(a.querySelectorAll('[data-role="skill-name"]')).map(r=>r.value.trim()).filter(Boolean));try{const c=await(await fetch("/api/skills")).json();for(const d of c)o.has(d)||l(d)}catch{t.textContent="기능 목록을 불러오지 못했습니다.",t.hidden=!1}}),n.addEventListener("submit",async o=>{o.preventDefault(),t.hidden=!0;const r=q(n,a,s),c=v(r);let d;try{d=await fetch(`/api/register/${e}`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(c)})}catch{t.textContent="네트워크 오류가 발생했습니다. 다시 시도해주세요.",t.hidden=!1;return}let i;try{i=await d.json()}catch{t.textContent="서버 응답을 처리할 수 없습니다. 다시 시도해주세요.",t.hidden=!1;return}if(!d.ok||!i.ok){t.textContent=i.error??"등록에 실패했습니다.",t.hidden=!1;return}f.innerHTML="";const m=document.createElement("p");m.className="status status--success",m.textContent=`${i.name} 캐릭터를 등록했습니다.`,f.appendChild(m)})}function q(e,a,s){const t=o=>{var r;return((r=e.elements.namedItem(o))==null?void 0:r.value)??""},n=o=>{var r;return((r=e.elements.namedItem(o))==null?void 0:r.checked)??!1},l=Array.from(a.querySelectorAll(".skill-row")).map(o=>{var r,c;return{name:((r=o.querySelector('[data-role="skill-name"]'))==null?void 0:r.value)??"",value:((c=o.querySelector('[data-role="skill-value"]'))==null?void 0:c.value)??""}}),p=Array.from(s.querySelectorAll(".weapon-row")).map(o=>Object.fromEntries(y.map(({key:r})=>{var c;return[r,((c=o.querySelector(`[data-role="${r}"]`))==null?void 0:c.value)??""]})));return{name:t("name"),occupation:t("occupation"),age:t("age"),sex:t("sex"),residence:t("residence"),birthplace:t("birthplace"),str:t("str"),dex:t("dex"),pow:t("pow"),con:t("con"),app:t("app"),edu:t("edu"),siz:t("siz"),int:t("int"),mov:t("mov"),majorWound:n("major_wound"),mpDepleted:n("mp_depleted"),weapons:p,cash:t("cash"),assets:t("assets"),skills:l}}L();
