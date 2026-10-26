(function(){let e=document.createElement(`link`).relList;if(e&&e.supports&&e.supports(`modulepreload`))return;for(let e of document.querySelectorAll(`link[rel="modulepreload"]`))n(e);new MutationObserver(e=>{for(let t of e)if(t.type===`childList`)for(let e of t.addedNodes)e.tagName===`LINK`&&e.rel===`modulepreload`&&n(e)}).observe(document,{childList:!0,subtree:!0});function t(e){let t={};return e.integrity&&(t.integrity=e.integrity),e.referrerPolicy&&(t.referrerPolicy=e.referrerPolicy),t.credentials=e.crossOrigin===`use-credentials`?`include`:e.crossOrigin===`anonymous`?`omit`:`same-origin`,t}function n(e){if(e.ep)return;e.ep=!0;let n=t(e);fetch(e.href,n)}})();var e=[{key:`name`,label:`이름`},{key:`skill`,label:`기능`},{key:`damage`,label:`피해`},{key:`range`,label:`사거리`},{key:`attacks`,label:`공격횟수`},{key:`ammo`,label:`탄약`},{key:`malfunction`,label:`고장`}];function t(e){return Number.isFinite(e)?{half:Math.floor(e/2),fifth:Math.floor(e/5)}:null}function n(e){let t=e.trim();if(t===``)return null;let n=Number(t);return Number.isFinite(n)?Math.trunc(n):null}function r(t){let r={};for(let e of t.skills){let t=e.name.trim(),n=e.value.trim();if(!t||n===``)continue;let i=Number(n);Number.isFinite(i)&&(r[t]=Math.trunc(i))}return{name:t.name.trim(),occupation:t.occupation.trim(),age:n(t.age),sex:t.sex.trim(),residence:t.residence.trim(),birthplace:t.birthplace.trim(),str:n(t.str),dex:n(t.dex),pow:n(t.pow),con:n(t.con),app:n(t.app),edu:n(t.edu),siz:n(t.siz),int:n(t.int),mov:n(t.mov),major_wound:t.majorWound,mp_depleted:t.mpDepleted,weapons:t.weapons.map(t=>Object.fromEntries(e.map(({key:e})=>[e,t[e].trim()]))).filter(e=>e.name!==``),cash:t.cash.trim(),assets:t.assets.trim(),skills:r}}var i=[{key:`str`,label:`근력`},{key:`dex`,label:`민첩`},{key:`pow`,label:`정신력`,required:!0},{key:`con`,label:`건강`},{key:`app`,label:`외모`},{key:`edu`,label:`교육`},{key:`siz`,label:`크기`},{key:`int`,label:`지능`},{key:`mov`,label:`이동력`}],a=document.querySelector(`#app`);function o(){let e=window.location.pathname.split(`/`).filter(Boolean);return e[e.length-1]??``}function s(e){a.innerHTML=``;let t=document.createElement(`p`);t.className=`status status--error`,t.textContent=e,a.appendChild(t)}async function c(){let e=o();a.innerHTML=`<p class="status">확인 중...</p>`;let t;try{t=await fetch(`/api/register/${e}`)}catch{s(`네트워크 오류가 발생했습니다. 다시 시도해주세요.`);return}t.ok?l(e):s(`링크가 만료되었거나 유효하지 않습니다. Discord에서 명령어를 다시 실행해주세요.`)}function l(n){a.innerHTML=`
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
            ${i.map(e=>`<label>${e.label} <input type="number" name="${e.key}"${e.required?` required`:``} /></label>`).join(``)}
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
  `;let o=document.querySelector(`#skill-rows`),s=document.querySelector(`#weapon-rows`),c=document.querySelector(`#form-error`),l=document.querySelector(`#registration-form`);function d(e=``,n=``){let r=document.createElement(`div`);r.className=`skill-row`;let i=document.createElement(`input`);i.type=`text`,i.dataset.role=`skill-name`,i.placeholder=`기능명`,i.ariaLabel=`기능명`,i.value=e;let a=document.createElement(`input`);a.type=`number`,a.dataset.role=`skill-value`,a.placeholder=`값`,a.ariaLabel=`값`,a.value=n;let s=document.createElement(`span`);s.className=`skill-half-fifth`;let c=()=>{let e=t(Number(a.value));s.textContent=e?`절반 ${e.half} / 1/5 ${e.fifth}`:``};a.addEventListener(`input`,c),c();let l=document.createElement(`button`);l.type=`button`,l.textContent=`삭제`,l.addEventListener(`click`,()=>r.remove()),r.append(i,a,s,l),o.appendChild(r)}function f(){let t=document.createElement(`div`);t.className=`weapon-row`;for(let{key:n,label:r}of e){let e=document.createElement(`input`);e.type=`text`,e.dataset.role=n,e.placeholder=r,e.ariaLabel=`무기 ${r}`,t.appendChild(e)}let n=document.createElement(`button`);n.type=`button`,n.textContent=`삭제`,n.addEventListener(`click`,()=>t.remove()),t.appendChild(n),s.appendChild(t)}document.querySelector(`#add-skill-row`).addEventListener(`click`,()=>d()),document.querySelector(`#add-weapon-row`).addEventListener(`click`,()=>f()),document.querySelector(`#fill-common-skills`).addEventListener(`click`,async()=>{let e=new Set(Array.from(o.querySelectorAll(`[data-role="skill-name"]`)).map(e=>e.value.trim()).filter(Boolean));try{let t=await(await fetch(`/api/skills`)).json();for(let n of t)e.has(n)||d(n)}catch{c.textContent=`기능 목록을 불러오지 못했습니다.`,c.hidden=!1}}),l.addEventListener(`submit`,async e=>{e.preventDefault(),c.hidden=!0;let t=r(u(l,o,s)),i;try{i=await fetch(`/api/register/${n}`,{method:`POST`,headers:{"Content-Type":`application/json`},body:JSON.stringify(t)})}catch{c.textContent=`네트워크 오류가 발생했습니다. 다시 시도해주세요.`,c.hidden=!1;return}let d;try{d=await i.json()}catch{c.textContent=`서버 응답을 처리할 수 없습니다. 다시 시도해주세요.`,c.hidden=!1;return}if(!i.ok||!d.ok){c.textContent=d.error??`등록에 실패했습니다.`,c.hidden=!1;return}a.innerHTML=``;let f=document.createElement(`p`);f.className=`status status--success`,f.textContent=`${d.name} 캐릭터를 등록했습니다.`,a.appendChild(f)})}function u(t,n,r){let i=e=>t.elements.namedItem(e)?.value??``,a=e=>t.elements.namedItem(e)?.checked??!1,o=Array.from(n.querySelectorAll(`.skill-row`)).map(e=>({name:e.querySelector(`[data-role="skill-name"]`)?.value??``,value:e.querySelector(`[data-role="skill-value"]`)?.value??``})),s=Array.from(r.querySelectorAll(`.weapon-row`)).map(t=>Object.fromEntries(e.map(({key:e})=>[e,t.querySelector(`[data-role="${e}"]`)?.value??``])));return{name:i(`name`),occupation:i(`occupation`),age:i(`age`),sex:i(`sex`),residence:i(`residence`),birthplace:i(`birthplace`),str:i(`str`),dex:i(`dex`),pow:i(`pow`),con:i(`con`),app:i(`app`),edu:i(`edu`),siz:i(`siz`),int:i(`int`),mov:i(`mov`),majorWound:a(`major_wound`),mpDepleted:a(`mp_depleted`),weapons:s,cash:i(`cash`),assets:i(`assets`),skills:o}}c();