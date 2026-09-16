(function(){const o=document.createElement("link").relList;if(o&&o.supports&&o.supports("modulepreload"))return;for(const r of document.querySelectorAll('link[rel="modulepreload"]'))l(r);new MutationObserver(r=>{for(const n of r)if(n.type==="childList")for(const i of n.addedNodes)i.tagName==="LINK"&&i.rel==="modulepreload"&&l(i)}).observe(document,{childList:!0,subtree:!0});function t(r){const n={};return r.integrity&&(n.integrity=r.integrity),r.referrerPolicy&&(n.referrerPolicy=r.referrerPolicy),r.crossOrigin==="use-credentials"?n.credentials="include":r.crossOrigin==="anonymous"?n.credentials="omit":n.credentials="same-origin",n}function l(r){if(r.ep)return;r.ep=!0;const n=t(r);fetch(r.href,n)}})();function y(e){return Number.isFinite(e)?{half:Math.floor(e/2),fifth:Math.floor(e/5)}:null}function c(e){const o=e.trim();if(o==="")return null;const t=Number(o);return Number.isFinite(t)?Math.trunc(t):null}function k(e){const o={};for(const t of e.skills){const l=t.name.trim(),r=t.value.trim();if(!l||r==="")continue;const n=Number(r);Number.isFinite(n)&&(o[l]=Math.trunc(n))}return{name:e.name.trim(),occupation:e.occupation.trim(),age:c(e.age),sex:e.sex.trim(),residence:e.residence.trim(),birthplace:e.birthplace.trim(),str:c(e.str),dex:c(e.dex),pow:c(e.pow),con:c(e.con),app:c(e.app),edu:c(e.edu),siz:c(e.siz),int:c(e.int),mov:c(e.mov),cash:e.cash.trim(),assets:e.assets.trim(),skills:o}}const x=[{key:"str",label:"근력"},{key:"dex",label:"민첩"},{key:"pow",label:"정신력",required:!0},{key:"con",label:"건강"},{key:"app",label:"외모"},{key:"edu",label:"교육"},{key:"siz",label:"크기"},{key:"int",label:"지능"},{key:"mov",label:"이동력"}],m=document.querySelector("#app");function w(){const e=window.location.pathname.split("/").filter(Boolean);return e[e.length-1]??""}function b(e){m.innerHTML="";const o=document.createElement("p");o.className="status status--error",o.textContent=e,m.appendChild(o)}async function g(){const e=w();m.innerHTML='<p class="status">확인 중...</p>';let o;try{o=await fetch(`/api/register/${e}`)}catch{b("네트워크 오류가 발생했습니다. 다시 시도해주세요.");return}if(!o.ok){b("링크가 만료되었거나 유효하지 않습니다. Discord에서 명령어를 다시 실행해주세요.");return}v(e)}function v(e){m.innerHTML=`
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
            ${x.map(n=>`<label>${n.label} <input type="number" name="${n.key}"${n.required?" required":""} /></label>`).join("")}
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
  `;const o=document.querySelector("#skill-rows"),t=document.querySelector("#form-error"),l=document.querySelector("#registration-form");function r(n="",i=""){const u=document.createElement("div");u.className="skill-row";const a=document.createElement("input");a.type="text",a.dataset.role="skill-name",a.placeholder="기능명",a.ariaLabel="기능명",a.value=n;const s=document.createElement("input");s.type="number",s.dataset.role="skill-value",s.placeholder="값",s.ariaLabel="값",s.value=i;const d=document.createElement("span");d.className="skill-half-fifth";const h=()=>{const f=y(Number(s.value));d.textContent=f?`절반 ${f.half} / 1/5 ${f.fifth}`:""};s.addEventListener("input",h),h();const p=document.createElement("button");p.type="button",p.textContent="삭제",p.addEventListener("click",()=>u.remove()),u.append(a,s,d,p),o.appendChild(u)}document.querySelector("#add-skill-row").addEventListener("click",()=>r()),document.querySelector("#fill-common-skills").addEventListener("click",async()=>{const n=new Set(Array.from(o.querySelectorAll('[data-role="skill-name"]')).map(i=>i.value.trim()).filter(Boolean));try{const u=await(await fetch("/api/skills")).json();for(const a of u)n.has(a)||r(a)}catch{t.textContent="기능 목록을 불러오지 못했습니다.",t.hidden=!1}}),l.addEventListener("submit",async n=>{n.preventDefault(),t.hidden=!0;const i=E(l,o),u=k(i);let a;try{a=await fetch(`/api/register/${e}`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(u)})}catch{t.textContent="네트워크 오류가 발생했습니다. 다시 시도해주세요.",t.hidden=!1;return}let s;try{s=await a.json()}catch{t.textContent="서버 응답을 처리할 수 없습니다. 다시 시도해주세요.",t.hidden=!1;return}if(!a.ok||!s.ok){t.textContent=s.error??"등록에 실패했습니다.",t.hidden=!1;return}m.innerHTML="";const d=document.createElement("p");d.className="status status--success",d.textContent=`${s.name} 캐릭터를 등록했습니다.`,m.appendChild(d)})}function E(e,o){const t=r=>{var n;return((n=e.elements.namedItem(r))==null?void 0:n.value)??""},l=Array.from(o.querySelectorAll(".skill-row")).map(r=>{var n,i;return{name:((n=r.querySelector('[data-role="skill-name"]'))==null?void 0:n.value)??"",value:((i=r.querySelector('[data-role="skill-value"]'))==null?void 0:i.value)??""}});return{name:t("name"),occupation:t("occupation"),age:t("age"),sex:t("sex"),residence:t("residence"),birthplace:t("birthplace"),str:t("str"),dex:t("dex"),pow:t("pow"),con:t("con"),app:t("app"),edu:t("edu"),siz:t("siz"),int:t("int"),mov:t("mov"),cash:t("cash"),assets:t("assets"),skills:l}}g();
