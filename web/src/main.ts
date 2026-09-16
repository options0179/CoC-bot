import "./style.css";
import {
  BIO_FIELDS,
  buildPayload,
  WEAPON_FIELDS,
  type FormValues,
  type Weapon,
} from "./payload";

const ATTRIBUTE_FIELDS: { key: string; label: string; required?: boolean }[] = [
  { key: "str", label: "근력" },
  { key: "dex", label: "민첩" },
  { key: "pow", label: "정신력", required: true },
  { key: "con", label: "건강" },
  { key: "app", label: "외모" },
  { key: "edu", label: "교육" },
  { key: "siz", label: "크기" },
  { key: "int", label: "지능" },
  { key: "mov", label: "이동력" },
];

const app = document.querySelector<HTMLDivElement>("#app")!;

function getToken(): string {
  const parts = window.location.pathname.split("/").filter(Boolean);
  return parts[parts.length - 1] ?? "";
}

function showError(message: string): void {
  app.innerHTML = "";
  const p = document.createElement("p");
  p.className = "status status--error";
  p.textContent = message;
  app.appendChild(p);
}

async function main(): Promise<void> {
  const token = getToken();
  app.innerHTML = `<p class="status">확인 중...</p>`;

  let statusResponse: Response;
  try {
    statusResponse = await fetch(`/api/register/${token}`);
  } catch {
    showError("네트워크 오류가 발생했습니다. 다시 시도해주세요.");
    return;
  }

  if (!statusResponse.ok) {
    showError("링크가 만료되었거나 유효하지 않습니다. Discord에서 명령어를 다시 실행해주세요.");
    return;
  }

  renderForm(token);
}

function renderForm(token: string): void {
  app.innerHTML = `
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
            ${ATTRIBUTE_FIELDS.map(
              (field) =>
                `<label>${field.label} <input type="number" name="${field.key}"${field.required ? " required" : ""} /></label>`
            ).join("")}
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
          ${BIO_FIELDS.map(
            (field) =>
              `<label>${field.label} <textarea name="bio.${field.key}" rows="2"></textarea></label>`
          ).join("")}
        </details>
        <p id="form-error" class="status status--error" hidden></p>
        <button type="submit">등록하기</button>
      </form>
    </div>
  `;

  const skillRows = document.querySelector<HTMLDivElement>("#skill-rows")!;
  const weaponRows = document.querySelector<HTMLDivElement>("#weapon-rows")!;
  const formError = document.querySelector<HTMLParagraphElement>("#form-error")!;
  const form = document.querySelector<HTMLFormElement>("#registration-form")!;

  function addSkillRow(name = "", value = ""): void {
    const row = document.createElement("div");
    row.className = "skill-row";

    const nameInput = document.createElement("input");
    nameInput.type = "text";
    nameInput.dataset.role = "skill-name";
    nameInput.placeholder = "기능명";
    nameInput.ariaLabel = "기능명";
    nameInput.value = name;

    const valueInput = document.createElement("input");
    valueInput.type = "number";
    valueInput.dataset.role = "skill-value";
    valueInput.placeholder = "값";
    valueInput.ariaLabel = "값";
    valueInput.value = value;

    const removeButton = document.createElement("button");
    removeButton.type = "button";
    removeButton.textContent = "삭제";
    removeButton.addEventListener("click", () => row.remove());

    row.append(nameInput, valueInput, removeButton);
    skillRows.appendChild(row);
  }

  function addWeaponRow(): void {
    const row = document.createElement("div");
    row.className = "weapon-row";

    for (const { key, label } of WEAPON_FIELDS) {
      const input = document.createElement("input");
      input.type = "text";
      input.dataset.role = key;
      input.placeholder = label;
      input.ariaLabel = `무기 ${label}`;
      row.appendChild(input);
    }

    const removeButton = document.createElement("button");
    removeButton.type = "button";
    removeButton.textContent = "삭제";
    removeButton.addEventListener("click", () => row.remove());
    row.appendChild(removeButton);

    weaponRows.appendChild(row);
  }

  document.querySelector("#add-skill-row")!.addEventListener("click", () => addSkillRow());
  document.querySelector("#add-weapon-row")!.addEventListener("click", () => addWeaponRow());

  document.querySelector("#fill-common-skills")!.addEventListener("click", async () => {
    const existingNames = new Set(
      Array.from(skillRows.querySelectorAll<HTMLInputElement>('[data-role="skill-name"]'))
        .map((input) => input.value.trim())
        .filter(Boolean)
    );
    try {
      const response = await fetch("/api/skills");
      const names: string[] = await response.json();
      for (const name of names) {
        if (!existingNames.has(name)) addSkillRow(name);
      }
    } catch {
      formError.textContent = "기능 목록을 불러오지 못했습니다.";
      formError.hidden = false;
    }
  });

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    formError.hidden = true;

    const values = collectFormValues(form, skillRows, weaponRows);
    const payload = buildPayload(values);

    let response: Response;
    try {
      response = await fetch(`/api/register/${token}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
    } catch {
      formError.textContent = "네트워크 오류가 발생했습니다. 다시 시도해주세요.";
      formError.hidden = false;
      return;
    }

    let result: { ok: boolean; name?: string; error?: string };
    try {
      result = await response.json();
    } catch {
      formError.textContent = "서버 응답을 처리할 수 없습니다. 다시 시도해주세요.";
      formError.hidden = false;
      return;
    }

    if (!response.ok || !result.ok) {
      formError.textContent = result.error ?? "등록에 실패했습니다.";
      formError.hidden = false;
      return;
    }

    app.innerHTML = "";
    const success = document.createElement("p");
    success.className = "status status--success";
    success.textContent = `${result.name} 캐릭터를 등록했습니다.`;
    app.appendChild(success);
  });
}

function collectFormValues(
  form: HTMLFormElement,
  skillRows: HTMLDivElement,
  weaponRows: HTMLDivElement
): FormValues {
  const field = (name: string) =>
    (form.elements.namedItem(name) as HTMLInputElement | null)?.value ?? "";
  const checked = (name: string) =>
    (form.elements.namedItem(name) as HTMLInputElement | null)?.checked ?? false;

  const skills = Array.from(skillRows.querySelectorAll<HTMLDivElement>(".skill-row")).map(
    (row) => ({
      name: row.querySelector<HTMLInputElement>('[data-role="skill-name"]')?.value ?? "",
      value: row.querySelector<HTMLInputElement>('[data-role="skill-value"]')?.value ?? "",
    })
  );

  const weapons = Array.from(
    weaponRows.querySelectorAll<HTMLDivElement>(".weapon-row")
  ).map(
    (row) =>
      Object.fromEntries(
        WEAPON_FIELDS.map(({ key }) => [
          key,
          row.querySelector<HTMLInputElement>(`[data-role="${key}"]`)?.value ?? "",
        ])
      ) as unknown as Weapon
  );

  return {
    name: field("name"),
    occupation: field("occupation"),
    age: field("age"),
    sex: field("sex"),
    residence: field("residence"),
    birthplace: field("birthplace"),
    str: field("str"),
    dex: field("dex"),
    pow: field("pow"),
    con: field("con"),
    app: field("app"),
    edu: field("edu"),
    siz: field("siz"),
    int: field("int"),
    mov: field("mov"),
    majorWound: checked("major_wound"),
    mpDepleted: checked("mp_depleted"),
    weapons,
    bio: Object.fromEntries(
      BIO_FIELDS.map(({ key }) => [
        key,
        (form.elements.namedItem(`bio.${key}`) as HTMLTextAreaElement | null)?.value ?? "",
      ])
    ),
    skills,
  };
}

main();
