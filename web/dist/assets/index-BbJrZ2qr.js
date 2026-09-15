(function(){const o=document.createElement("link").relList;if(o&&o.supports&&o.supports("modulepreload"))return;for(const r of document.querySelectorAll('link[rel="modulepreload"]'))s(r);new MutationObserver(r=>{for(const n of r)if(n.type==="childList")for(const i of n.addedNodes)i.tagName==="LINK"&&i.rel==="modulepreload"&&s(i)}).observe(document,{childList:!0,subtree:!0});function e(r){const n={};return r.integrity&&(n.integrity=r.integrity),r.referrerPolicy&&(n.referrerPolicy=r.referrerPolicy),r.crossOrigin==="use-credentials"?n.credentials="include":r.crossOrigin==="anonymous"?n.credentials="omit":n.credentials="same-origin",n}function s(r){if(r.ep)return;r.ep=!0;const n=e(r);fetch(r.href,n)}})();function c(t){const o=t.trim();if(o==="")return null;const e=Number(o);return Number.isFinite(e)?Math.trunc(e):null}function f(t){const o={};for(const e of t.skills){const s=e.name.trim(),r=e.value.trim();if(!s||r==="")continue;const n=Number(r);Number.isFinite(n)&&(o[s]=Math.trunc(n))}return{name:t.name.trim(),occupation:t.occupation.trim(),age:c(t.age),sex:t.sex.trim(),residence:t.residence.trim(),birthplace:t.birthplace.trim(),str:c(t.str),dex:c(t.dex),pow:c(t.pow),con:c(t.con),app:c(t.app),edu:c(t.edu),siz:c(t.siz),int:c(t.int),mov:c(t.mov),skills:o}}const b=[{key:"str",label:"근력"},{key:"dex",label:"민첩"},{key:"pow",label:"정신력"},{key:"con",label:"건강"},{key:"app",label:"외모"},{key:"edu",label:"교육"},{key:"siz",label:"크기"},{key:"int",label:"지능"},{key:"mov",label:"이동력"}],m=document.querySelector("#app");function y(){const t=window.location.pathname.split("/").filter(Boolean);return t[t.length-1]??""}function p(t){m.innerHTML="";const o=document.createElement("p");o.className="status status--error",o.textContent=t,m.appendChild(o)}async function h(){const t=y();m.innerHTML='<p class="status">확인 중...</p>';let o;try{o=await fetch(`/api/register/${t}`)}catch{p("네트워크 오류가 발생했습니다. 다시 시도해주세요.");return}if(!o.ok){p("링크가 만료되었거나 유효하지 않습니다. Discord에서 명령어를 다시 실행해주세요.");return}k(t)}function k(t){m.innerHTML=`
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
            ${b.map(n=>`<label>${n.label} <input type="number" name="${n.key}" /></label>`).join("")}
          </div>
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
  `;const o=document.querySelector("#skill-rows"),e=document.querySelector("#form-error"),s=document.querySelector("#registration-form");function r(n="",i=""){const u=document.createElement("div");u.className="skill-row";const l=document.createElement("input");l.type="text",l.dataset.role="skill-name",l.placeholder="기능명",l.ariaLabel="기능명",l.value=n;const a=document.createElement("input");a.type="number",a.dataset.role="skill-value",a.placeholder="값",a.ariaLabel="값",a.value=i;const d=document.createElement("button");d.type="button",d.textContent="삭제",d.addEventListener("click",()=>u.remove()),u.append(l,a,d),o.appendChild(u)}document.querySelector("#add-skill-row").addEventListener("click",()=>r()),document.querySelector("#fill-common-skills").addEventListener("click",async()=>{const n=new Set(Array.from(o.querySelectorAll('[data-role="skill-name"]')).map(i=>i.value.trim()).filter(Boolean));try{const u=await(await fetch("/api/skills")).json();for(const l of u)n.has(l)||r(l)}catch{e.textContent="기능 목록을 불러오지 못했습니다.",e.hidden=!1}}),s.addEventListener("submit",async n=>{n.preventDefault(),e.hidden=!0;const i=w(s,o),u=f(i);let l;try{l=await fetch(`/api/register/${t}`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(u)})}catch{e.textContent="네트워크 오류가 발생했습니다. 다시 시도해주세요.",e.hidden=!1;return}let a;try{a=await l.json()}catch{e.textContent="서버 응답을 처리할 수 없습니다. 다시 시도해주세요.",e.hidden=!1;return}if(!l.ok||!a.ok){e.textContent=a.error??"등록에 실패했습니다.",e.hidden=!1;return}m.innerHTML="";const d=document.createElement("p");d.className="status status--success",d.textContent=`${a.name} 캐릭터를 등록했습니다.`,m.appendChild(d)})}function w(t,o){const e=r=>{var n;return((n=t.elements.namedItem(r))==null?void 0:n.value)??""},s=Array.from(o.querySelectorAll(".skill-row")).map(r=>{var n,i;return{name:((n=r.querySelector('[data-role="skill-name"]'))==null?void 0:n.value)??"",value:((i=r.querySelector('[data-role="skill-value"]'))==null?void 0:i.value)??""}});return{name:e("name"),occupation:e("occupation"),age:e("age"),sex:e("sex"),residence:e("residence"),birthplace:e("birthplace"),str:e("str"),dex:e("dex"),pow:e("pow"),con:e("con"),app:e("app"),edu:e("edu"),siz:e("siz"),int:e("int"),mov:e("mov"),skills:s}}h();
