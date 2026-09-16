(function(){const a=document.createElement("link").relList;if(a&&a.supports&&a.supports("modulepreload"))return;for(const r of document.querySelectorAll('link[rel="modulepreload"]'))t(r);new MutationObserver(r=>{for(const i of r)if(i.type==="childList")for(const p of i.addedNodes)p.tagName==="LINK"&&p.rel==="modulepreload"&&t(p)}).observe(document,{childList:!0,subtree:!0});function l(r){const i={};return r.integrity&&(i.integrity=r.integrity),r.referrerPolicy&&(i.referrerPolicy=r.referrerPolicy),r.crossOrigin==="use-credentials"?i.credentials="include":r.crossOrigin==="anonymous"?i.credentials="omit":i.credentials="same-origin",i}function t(r){if(r.ep)return;r.ep=!0;const i=l(r);fetch(r.href,i)}})();const h=[{key:"gear",label:"장비 및 소지품"},{key:"personal_description",label:"개인 묘사"},{key:"ideology_beliefs",label:"사상/신념"},{key:"significant_people",label:"중요한 사람들"},{key:"meaningful_locations",label:"의미 있는 장소"},{key:"treasured_possessions",label:"소중한 물건"},{key:"traits",label:"특징"},{key:"injuries_scars",label:"상처와 흉터"},{key:"phobias_manias",label:"공포증과 매니아"},{key:"arcane_tomes",label:"비전의 서적·주문·인공물"},{key:"encounters",label:"기괴한 존재와의 조우"},{key:"fellow_investigators",label:"동료 탐사자"}],y=[{key:"name",label:"이름"},{key:"skill",label:"기능"},{key:"damage",label:"피해"},{key:"range",label:"사거리"},{key:"attacks",label:"공격횟수"},{key:"ammo",label:"탄약"},{key:"malfunction",label:"고장"}];function m(e){const a=e.trim();if(a==="")return null;const l=Number(a);return Number.isFinite(l)?Math.trunc(l):null}function k(e){const a={};for(const l of e.skills){const t=l.name.trim(),r=l.value.trim();if(!t||r==="")continue;const i=Number(r);Number.isFinite(i)&&(a[t]=Math.trunc(i))}return{name:e.name.trim(),occupation:e.occupation.trim(),age:m(e.age),sex:e.sex.trim(),residence:e.residence.trim(),birthplace:e.birthplace.trim(),str:m(e.str),dex:m(e.dex),pow:m(e.pow),con:m(e.con),app:m(e.app),edu:m(e.edu),siz:m(e.siz),int:m(e.int),mov:m(e.mov),major_wound:e.majorWound,mp_depleted:e.mpDepleted,weapons:e.weapons.map(l=>Object.fromEntries(y.map(({key:t})=>[t,l[t].trim()]))).filter(l=>l.name!==""),bio:Object.fromEntries(Object.entries(e.bio).map(([l,t])=>[l,t.trim()]).filter(([,l])=>l!=="")),skills:a}}const w=[{key:"str",label:"근력"},{key:"dex",label:"민첩"},{key:"pow",label:"정신력",required:!0},{key:"con",label:"건강"},{key:"app",label:"외모"},{key:"edu",label:"교육"},{key:"siz",label:"크기"},{key:"int",label:"지능"},{key:"mov",label:"이동력"}],b=document.querySelector("#app");function x(){const e=window.location.pathname.split("/").filter(Boolean);return e[e.length-1]??""}function f(e){b.innerHTML="";const a=document.createElement("p");a.className="status status--error",a.textContent=e,b.appendChild(a)}async function g(){const e=x();b.innerHTML='<p class="status">확인 중...</p>';let a;try{a=await fetch(`/api/register/${e}`)}catch{f("네트워크 오류가 발생했습니다. 다시 시도해주세요.");return}if(!a.ok){f("링크가 만료되었거나 유효하지 않습니다. Discord에서 명령어를 다시 실행해주세요.");return}v(e)}function v(e){b.innerHTML=`
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
            ${w.map(n=>`<label>${n.label} <input type="number" name="${n.key}"${n.required?" required":""} /></label>`).join("")}
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
          <h2>기능</h2>
          <div id="skill-rows"></div>
          <button type="button" id="add-skill-row">+ 기능 추가</button>
          <button type="button" id="fill-common-skills">자주 쓰는 기능 채우기</button>
        </section>
        <details>
          <summary>장비·소지품·백스토리 (선택)</summary>
          ${h.map(n=>`<label>${n.label} <textarea name="bio.${n.key}" rows="2"></textarea></label>`).join("")}
        </details>
        <p id="form-error" class="status status--error" hidden></p>
        <button type="submit">등록하기</button>
      </form>
    </div>
  `;const a=document.querySelector("#skill-rows"),l=document.querySelector("#weapon-rows"),t=document.querySelector("#form-error"),r=document.querySelector("#registration-form");function i(n="",o=""){const c=document.createElement("div");c.className="skill-row";const d=document.createElement("input");d.type="text",d.dataset.role="skill-name",d.placeholder="기능명",d.ariaLabel="기능명",d.value=n;const s=document.createElement("input");s.type="number",s.dataset.role="skill-value",s.placeholder="값",s.ariaLabel="값",s.value=o;const u=document.createElement("button");u.type="button",u.textContent="삭제",u.addEventListener("click",()=>c.remove()),c.append(d,s,u),a.appendChild(c)}function p(){const n=document.createElement("div");n.className="weapon-row";for(const{key:c,label:d}of y){const s=document.createElement("input");s.type="text",s.dataset.role=c,s.placeholder=d,s.ariaLabel=`무기 ${d}`,n.appendChild(s)}const o=document.createElement("button");o.type="button",o.textContent="삭제",o.addEventListener("click",()=>n.remove()),n.appendChild(o),l.appendChild(n)}document.querySelector("#add-skill-row").addEventListener("click",()=>i()),document.querySelector("#add-weapon-row").addEventListener("click",()=>p()),document.querySelector("#fill-common-skills").addEventListener("click",async()=>{const n=new Set(Array.from(a.querySelectorAll('[data-role="skill-name"]')).map(o=>o.value.trim()).filter(Boolean));try{const c=await(await fetch("/api/skills")).json();for(const d of c)n.has(d)||i(d)}catch{t.textContent="기능 목록을 불러오지 못했습니다.",t.hidden=!1}}),r.addEventListener("submit",async n=>{n.preventDefault(),t.hidden=!0;const o=E(r,a,l),c=k(o);let d;try{d=await fetch(`/api/register/${e}`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(c)})}catch{t.textContent="네트워크 오류가 발생했습니다. 다시 시도해주세요.",t.hidden=!1;return}let s;try{s=await d.json()}catch{t.textContent="서버 응답을 처리할 수 없습니다. 다시 시도해주세요.",t.hidden=!1;return}if(!d.ok||!s.ok){t.textContent=s.error??"등록에 실패했습니다.",t.hidden=!1;return}b.innerHTML="";const u=document.createElement("p");u.className="status status--success",u.textContent=`${s.name} 캐릭터를 등록했습니다.`,b.appendChild(u)})}function E(e,a,l){const t=n=>{var o;return((o=e.elements.namedItem(n))==null?void 0:o.value)??""},r=n=>{var o;return((o=e.elements.namedItem(n))==null?void 0:o.checked)??!1},i=Array.from(a.querySelectorAll(".skill-row")).map(n=>{var o,c;return{name:((o=n.querySelector('[data-role="skill-name"]'))==null?void 0:o.value)??"",value:((c=n.querySelector('[data-role="skill-value"]'))==null?void 0:c.value)??""}}),p=Array.from(l.querySelectorAll(".weapon-row")).map(n=>Object.fromEntries(y.map(({key:o})=>{var c;return[o,((c=n.querySelector(`[data-role="${o}"]`))==null?void 0:c.value)??""]})));return{name:t("name"),occupation:t("occupation"),age:t("age"),sex:t("sex"),residence:t("residence"),birthplace:t("birthplace"),str:t("str"),dex:t("dex"),pow:t("pow"),con:t("con"),app:t("app"),edu:t("edu"),siz:t("siz"),int:t("int"),mov:t("mov"),majorWound:r("major_wound"),mpDepleted:r("mp_depleted"),weapons:p,bio:Object.fromEntries(h.map(({key:n})=>{var o;return[n,((o=e.elements.namedItem(`bio.${n}`))==null?void 0:o.value)??""]})),skills:i}}g();
