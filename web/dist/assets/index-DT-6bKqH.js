(function(){const o=document.createElement("link").relList;if(o&&o.supports&&o.supports("modulepreload"))return;for(const r of document.querySelectorAll('link[rel="modulepreload"]'))l(r);new MutationObserver(r=>{for(const n of r)if(n.type==="childList")for(const s of n.addedNodes)s.tagName==="LINK"&&s.rel==="modulepreload"&&l(s)}).observe(document,{childList:!0,subtree:!0});function e(r){const n={};return r.integrity&&(n.integrity=r.integrity),r.referrerPolicy&&(n.referrerPolicy=r.referrerPolicy),r.crossOrigin==="use-credentials"?n.credentials="include":r.crossOrigin==="anonymous"?n.credentials="omit":n.credentials="same-origin",n}function l(r){if(r.ep)return;r.ep=!0;const n=e(r);fetch(r.href,n)}})();function c(t){const o=t.trim();if(o==="")return null;const e=Number(o);return Number.isFinite(e)?Math.trunc(e):null}function f(t){const o={};for(const e of t.skills){const l=e.name.trim(),r=e.value.trim();if(!l||r==="")continue;const n=Number(r);Number.isFinite(n)&&(o[l]=Math.trunc(n))}return{name:t.name.trim(),occupation:t.occupation.trim(),age:c(t.age),sex:t.sex.trim(),residence:t.residence.trim(),birthplace:t.birthplace.trim(),str:c(t.str),dex:c(t.dex),pow:c(t.pow),con:c(t.con),app:c(t.app),edu:c(t.edu),siz:c(t.siz),int:c(t.int),mov:c(t.mov),cash:t.cash.trim(),assets:t.assets.trim(),skills:o}}const b=[{key:"str",label:"근력"},{key:"dex",label:"민첩"},{key:"pow",label:"정신력",required:!0},{key:"con",label:"건강"},{key:"app",label:"외모"},{key:"edu",label:"교육"},{key:"siz",label:"크기"},{key:"int",label:"지능"},{key:"mov",label:"이동력"}],p=document.querySelector("#app");function y(){const t=window.location.pathname.split("/").filter(Boolean);return t[t.length-1]??""}function m(t){p.innerHTML="";const o=document.createElement("p");o.className="status status--error",o.textContent=t,p.appendChild(o)}async function h(){const t=y();p.innerHTML='<p class="status">확인 중...</p>';let o;try{o=await fetch(`/api/register/${t}`)}catch{m("네트워크 오류가 발생했습니다. 다시 시도해주세요.");return}if(!o.ok){m("링크가 만료되었거나 유효하지 않습니다. Discord에서 명령어를 다시 실행해주세요.");return}k(t)}function k(t){p.innerHTML=`
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
            ${b.map(n=>`<label>${n.label} <input type="number" name="${n.key}"${n.required?" required":""} /></label>`).join("")}
          </div>
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
  `;const o=document.querySelector("#skill-rows"),e=document.querySelector("#form-error"),l=document.querySelector("#registration-form");function r(n="",s=""){const u=document.createElement("div");u.className="skill-row";const a=document.createElement("input");a.type="text",a.dataset.role="skill-name",a.placeholder="기능명",a.ariaLabel="기능명",a.value=n;const i=document.createElement("input");i.type="number",i.dataset.role="skill-value",i.placeholder="값",i.ariaLabel="값",i.value=s;const d=document.createElement("button");d.type="button",d.textContent="삭제",d.addEventListener("click",()=>u.remove()),u.append(a,i,d),o.appendChild(u)}document.querySelector("#add-skill-row").addEventListener("click",()=>r()),document.querySelector("#fill-common-skills").addEventListener("click",async()=>{const n=new Set(Array.from(o.querySelectorAll('[data-role="skill-name"]')).map(s=>s.value.trim()).filter(Boolean));try{const u=await(await fetch("/api/skills")).json();for(const a of u)n.has(a)||r(a)}catch{e.textContent="기능 목록을 불러오지 못했습니다.",e.hidden=!1}}),l.addEventListener("submit",async n=>{n.preventDefault(),e.hidden=!0;const s=x(l,o),u=f(s);let a;try{a=await fetch(`/api/register/${t}`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(u)})}catch{e.textContent="네트워크 오류가 발생했습니다. 다시 시도해주세요.",e.hidden=!1;return}let i;try{i=await a.json()}catch{e.textContent="서버 응답을 처리할 수 없습니다. 다시 시도해주세요.",e.hidden=!1;return}if(!a.ok||!i.ok){e.textContent=i.error??"등록에 실패했습니다.",e.hidden=!1;return}p.innerHTML="";const d=document.createElement("p");d.className="status status--success",d.textContent=`${i.name} 캐릭터를 등록했습니다.`,p.appendChild(d)})}function x(t,o){const e=r=>{var n;return((n=t.elements.namedItem(r))==null?void 0:n.value)??""},l=Array.from(o.querySelectorAll(".skill-row")).map(r=>{var n,s;return{name:((n=r.querySelector('[data-role="skill-name"]'))==null?void 0:n.value)??"",value:((s=r.querySelector('[data-role="skill-value"]'))==null?void 0:s.value)??""}});return{name:e("name"),occupation:e("occupation"),age:e("age"),sex:e("sex"),residence:e("residence"),birthplace:e("birthplace"),str:e("str"),dex:e("dex"),pow:e("pow"),con:e("con"),app:e("app"),edu:e("edu"),siz:e("siz"),int:e("int"),mov:e("mov"),cash:e("cash"),assets:e("assets"),skills:l}}h();
