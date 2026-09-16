(function(){const o=document.createElement("link").relList;if(o&&o.supports&&o.supports("modulepreload"))return;for(const r of document.querySelectorAll('link[rel="modulepreload"]'))a(r);new MutationObserver(r=>{for(const n of r)if(n.type==="childList")for(const l of n.addedNodes)l.tagName==="LINK"&&l.rel==="modulepreload"&&a(l)}).observe(document,{childList:!0,subtree:!0});function t(r){const n={};return r.integrity&&(n.integrity=r.integrity),r.referrerPolicy&&(n.referrerPolicy=r.referrerPolicy),r.crossOrigin==="use-credentials"?n.credentials="include":r.crossOrigin==="anonymous"?n.credentials="omit":n.credentials="same-origin",n}function a(r){if(r.ep)return;r.ep=!0;const n=t(r);fetch(r.href,n)}})();function d(e){const o=e.trim();if(o==="")return null;const t=Number(o);return Number.isFinite(t)?Math.trunc(t):null}function f(e){const o={};for(const t of e.skills){const a=t.name.trim(),r=t.value.trim();if(!a||r==="")continue;const n=Number(r);Number.isFinite(n)&&(o[a]=Math.trunc(n))}return{name:e.name.trim(),occupation:e.occupation.trim(),age:d(e.age),sex:e.sex.trim(),residence:e.residence.trim(),birthplace:e.birthplace.trim(),str:d(e.str),dex:d(e.dex),pow:d(e.pow),con:d(e.con),app:d(e.app),edu:d(e.edu),siz:d(e.siz),int:d(e.int),mov:d(e.mov),major_wound:e.majorWound,mp_depleted:e.mpDepleted,skills:o}}const b=[{key:"str",label:"근력"},{key:"dex",label:"민첩"},{key:"pow",label:"정신력",required:!0},{key:"con",label:"건강"},{key:"app",label:"외모"},{key:"edu",label:"교육"},{key:"siz",label:"크기"},{key:"int",label:"지능"},{key:"mov",label:"이동력"}],m=document.querySelector("#app");function y(){const e=window.location.pathname.split("/").filter(Boolean);return e[e.length-1]??""}function p(e){m.innerHTML="";const o=document.createElement("p");o.className="status status--error",o.textContent=e,m.appendChild(o)}async function h(){const e=y();m.innerHTML='<p class="status">확인 중...</p>';let o;try{o=await fetch(`/api/register/${e}`)}catch{p("네트워크 오류가 발생했습니다. 다시 시도해주세요.");return}if(!o.ok){p("링크가 만료되었거나 유효하지 않습니다. Discord에서 명령어를 다시 실행해주세요.");return}k(e)}function k(e){m.innerHTML=`
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
          <h2>상태</h2>
          <label class="checkbox-field">
            <input type="checkbox" name="major_wound" /> 중상 (HP가 한 번에 최대치의 절반 이상 깎임)
          </label>
          <label class="checkbox-field">
            <input type="checkbox" name="mp_depleted" /> 빈사 (MP 소진)
          </label>
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
  `;const o=document.querySelector("#skill-rows"),t=document.querySelector("#form-error"),a=document.querySelector("#registration-form");function r(n="",l=""){const s=document.createElement("div");s.className="skill-row";const i=document.createElement("input");i.type="text",i.dataset.role="skill-name",i.placeholder="기능명",i.ariaLabel="기능명",i.value=n;const c=document.createElement("input");c.type="number",c.dataset.role="skill-value",c.placeholder="값",c.ariaLabel="값",c.value=l;const u=document.createElement("button");u.type="button",u.textContent="삭제",u.addEventListener("click",()=>s.remove()),s.append(i,c,u),o.appendChild(s)}document.querySelector("#add-skill-row").addEventListener("click",()=>r()),document.querySelector("#fill-common-skills").addEventListener("click",async()=>{const n=new Set(Array.from(o.querySelectorAll('[data-role="skill-name"]')).map(l=>l.value.trim()).filter(Boolean));try{const s=await(await fetch("/api/skills")).json();for(const i of s)n.has(i)||r(i)}catch{t.textContent="기능 목록을 불러오지 못했습니다.",t.hidden=!1}}),a.addEventListener("submit",async n=>{n.preventDefault(),t.hidden=!0;const l=x(a,o),s=f(l);let i;try{i=await fetch(`/api/register/${e}`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(s)})}catch{t.textContent="네트워크 오류가 발생했습니다. 다시 시도해주세요.",t.hidden=!1;return}let c;try{c=await i.json()}catch{t.textContent="서버 응답을 처리할 수 없습니다. 다시 시도해주세요.",t.hidden=!1;return}if(!i.ok||!c.ok){t.textContent=c.error??"등록에 실패했습니다.",t.hidden=!1;return}m.innerHTML="";const u=document.createElement("p");u.className="status status--success",u.textContent=`${c.name} 캐릭터를 등록했습니다.`,m.appendChild(u)})}function x(e,o){const t=n=>{var l;return((l=e.elements.namedItem(n))==null?void 0:l.value)??""},a=n=>{var l;return((l=e.elements.namedItem(n))==null?void 0:l.checked)??!1},r=Array.from(o.querySelectorAll(".skill-row")).map(n=>{var l,s;return{name:((l=n.querySelector('[data-role="skill-name"]'))==null?void 0:l.value)??"",value:((s=n.querySelector('[data-role="skill-value"]'))==null?void 0:s.value)??""}});return{name:t("name"),occupation:t("occupation"),age:t("age"),sex:t("sex"),residence:t("residence"),birthplace:t("birthplace"),str:t("str"),dex:t("dex"),pow:t("pow"),con:t("con"),app:t("app"),edu:t("edu"),siz:t("siz"),int:t("int"),mov:t("mov"),majorWound:a("major_wound"),mpDepleted:a("mp_depleted"),skills:r}}h();
