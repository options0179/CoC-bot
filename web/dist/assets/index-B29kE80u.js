(function(){let e=document.createElement(`link`).relList;if(e&&e.supports&&e.supports(`modulepreload`))return;for(let e of document.querySelectorAll(`link[rel="modulepreload"]`))n(e);new MutationObserver(e=>{for(let t of e)if(t.type===`childList`)for(let e of t.addedNodes)e.tagName===`LINK`&&e.rel===`modulepreload`&&n(e)}).observe(document,{childList:!0,subtree:!0});function t(e){let t={};return e.integrity&&(t.integrity=e.integrity),e.referrerPolicy&&(t.referrerPolicy=e.referrerPolicy),t.credentials=e.crossOrigin===`use-credentials`?`include`:e.crossOrigin===`anonymous`?`omit`:`same-origin`,t}function n(e){if(e.ep)return;e.ep=!0;let n=t(e);fetch(e.href,n)}})();function e(e){let t=e.trim();if(t===``)return null;let n=Number(t);return Number.isFinite(n)?Math.trunc(n):null}function t(t){let n={};for(let e of t.skills){let t=e.name.trim(),r=e.value.trim();if(!t||r===``)continue;let i=Number(r);Number.isFinite(i)&&(n[t]=Math.trunc(i))}return{name:t.name.trim(),occupation:t.occupation.trim(),age:e(t.age),sex:t.sex.trim(),residence:t.residence.trim(),birthplace:t.birthplace.trim(),str:e(t.str),dex:e(t.dex),pow:e(t.pow),con:e(t.con),app:e(t.app),edu:e(t.edu),siz:e(t.siz),int:e(t.int),mov:e(t.mov),skills:n}}var n=[{key:`str`,label:`근력`},{key:`dex`,label:`민첩`},{key:`pow`,label:`정신력`},{key:`con`,label:`건강`},{key:`app`,label:`외모`},{key:`edu`,label:`교육`},{key:`siz`,label:`크기`},{key:`int`,label:`지능`},{key:`mov`,label:`이동력`}],r=document.querySelector(`#app`);function i(){let e=window.location.pathname.split(`/`).filter(Boolean);return e[e.length-1]??``}function a(e){r.innerHTML=``;let t=document.createElement(`p`);t.className=`status status--error`,t.textContent=e,r.appendChild(t)}async function o(){let e=i();r.innerHTML=`<p class="status">확인 중...</p>`;let t;try{t=await fetch(`/api/register/${e}`)}catch{a(`네트워크 오류가 발생했습니다. 다시 시도해주세요.`);return}t.ok?s(e):a(`링크가 만료되었거나 유효하지 않습니다. Discord에서 명령어를 다시 실행해주세요.`)}function s(e){r.innerHTML=`
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
            ${n.map(e=>`<label>${e.label} <input type="number" name="${e.key}" /></label>`).join(``)}
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
  `;let i=document.querySelector(`#skill-rows`),a=document.querySelector(`#form-error`),o=document.querySelector(`#registration-form`);function s(e=``,t=``){let n=document.createElement(`div`);n.className=`skill-row`;let r=document.createElement(`input`);r.type=`text`,r.dataset.role=`skill-name`,r.placeholder=`기능명`,r.ariaLabel=`기능명`,r.value=e;let a=document.createElement(`input`);a.type=`number`,a.dataset.role=`skill-value`,a.placeholder=`값`,a.ariaLabel=`값`,a.value=t;let o=document.createElement(`button`);o.type=`button`,o.textContent=`삭제`,o.addEventListener(`click`,()=>n.remove()),n.append(r,a,o),i.appendChild(n)}document.querySelector(`#add-skill-row`).addEventListener(`click`,()=>s()),document.querySelector(`#fill-common-skills`).addEventListener(`click`,async()=>{let e=new Set(Array.from(i.querySelectorAll(`[data-role="skill-name"]`)).map(e=>e.value.trim()).filter(Boolean));try{let t=await(await fetch(`/api/skills`)).json();for(let n of t)e.has(n)||s(n)}catch{a.textContent=`기능 목록을 불러오지 못했습니다.`,a.hidden=!1}}),o.addEventListener(`submit`,async n=>{n.preventDefault(),a.hidden=!0;let s=t(c(o,i)),l;try{l=await fetch(`/api/register/${e}`,{method:`POST`,headers:{"Content-Type":`application/json`},body:JSON.stringify(s)})}catch{a.textContent=`네트워크 오류가 발생했습니다. 다시 시도해주세요.`,a.hidden=!1;return}let u;try{u=await l.json()}catch{a.textContent=`서버 응답을 처리할 수 없습니다. 다시 시도해주세요.`,a.hidden=!1;return}if(!l.ok||!u.ok){a.textContent=u.error??`등록에 실패했습니다.`,a.hidden=!1;return}r.innerHTML=``;let d=document.createElement(`p`);d.className=`status status--success`,d.textContent=`${u.name} 캐릭터를 등록했습니다.`,r.appendChild(d)})}function c(e,t){let n=t=>e.elements.namedItem(t)?.value??``,r=Array.from(t.querySelectorAll(`.skill-row`)).map(e=>({name:e.querySelector(`[data-role="skill-name"]`)?.value??``,value:e.querySelector(`[data-role="skill-value"]`)?.value??``}));return{name:n(`name`),occupation:n(`occupation`),age:n(`age`),sex:n(`sex`),residence:n(`residence`),birthplace:n(`birthplace`),str:n(`str`),dex:n(`dex`),pow:n(`pow`),con:n(`con`),app:n(`app`),edu:n(`edu`),siz:n(`siz`),int:n(`int`),mov:n(`mov`),skills:r}}o();