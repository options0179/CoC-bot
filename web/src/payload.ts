export interface FormValues {
  name: string;
  occupation: string;
  age: string;
  sex: string;
  residence: string;
  birthplace: string;
  str: string;
  dex: string;
  pow: string;
  con: string;
  app: string;
  edu: string;
  siz: string;
  int: string;
  mov: string;
  majorWound: boolean;
  mpDepleted: boolean;
  weapons: Weapon[];
  bio: Record<string, string>;
  skills: { name: string; value: string }[];
}

// 캐릭터시트 뒷면의 자유 서술 칸 12개 (장비·소지품 + 백스토리 10종 + 동료 탐사자)
export const BIO_FIELDS: { key: string; label: string }[] = [
  { key: "gear", label: "장비 및 소지품" },
  { key: "personal_description", label: "개인 묘사" },
  { key: "ideology_beliefs", label: "사상/신념" },
  { key: "significant_people", label: "중요한 사람들" },
  { key: "meaningful_locations", label: "의미 있는 장소" },
  { key: "treasured_possessions", label: "소중한 물건" },
  { key: "traits", label: "특징" },
  { key: "injuries_scars", label: "상처와 흉터" },
  { key: "phobias_manias", label: "공포증과 매니아" },
  { key: "arcane_tomes", label: "비전의 서적·주문·인공물" },
  { key: "encounters", label: "기괴한 존재와의 조우" },
  { key: "fellow_investigators", label: "동료 탐사자" },
];

export interface Weapon {
  name: string;
  skill: string;
  damage: string;
  range: string;
  attacks: string;
  ammo: string;
  malfunction: string;
}

export const WEAPON_FIELDS: { key: keyof Weapon; label: string }[] = [
  { key: "name", label: "이름" },
  { key: "skill", label: "기능" },
  { key: "damage", label: "피해" },
  { key: "range", label: "사거리" },
  { key: "attacks", label: "공격횟수" },
  { key: "ammo", label: "탄약" },
  { key: "malfunction", label: "고장" },
];

export interface RegistrationPayload {
  name: string;
  occupation: string;
  age: number | null;
  sex: string;
  residence: string;
  birthplace: string;
  str: number | null;
  dex: number | null;
  pow: number | null;
  con: number | null;
  app: number | null;
  edu: number | null;
  siz: number | null;
  int: number | null;
  mov: number | null;
  major_wound: boolean;
  mp_depleted: boolean;
  weapons: Weapon[];
  bio: Record<string, string>;
  skills: Record<string, number>;
}

function parseIntOrNull(value: string): number | null {
  const trimmed = value.trim();
  if (trimmed === "") return null;
  const parsed = Number(trimmed);
  return Number.isFinite(parsed) ? Math.trunc(parsed) : null;
}

export function buildPayload(values: FormValues): RegistrationPayload {
  const skills: Record<string, number> = {};
  for (const row of values.skills) {
    const name = row.name.trim();
    const value = row.value.trim();
    if (!name || value === "") continue;
    const parsed = Number(value);
    if (Number.isFinite(parsed)) {
      skills[name] = Math.trunc(parsed);
    }
  }

  return {
    name: values.name.trim(),
    occupation: values.occupation.trim(),
    age: parseIntOrNull(values.age),
    sex: values.sex.trim(),
    residence: values.residence.trim(),
    birthplace: values.birthplace.trim(),
    str: parseIntOrNull(values.str),
    dex: parseIntOrNull(values.dex),
    pow: parseIntOrNull(values.pow),
    con: parseIntOrNull(values.con),
    app: parseIntOrNull(values.app),
    edu: parseIntOrNull(values.edu),
    siz: parseIntOrNull(values.siz),
    int: parseIntOrNull(values.int),
    mov: parseIntOrNull(values.mov),
    major_wound: values.majorWound,
    mp_depleted: values.mpDepleted,
    weapons: values.weapons
      .map(
        (weapon) =>
          Object.fromEntries(
            WEAPON_FIELDS.map(({ key }) => [key, weapon[key].trim()])
          ) as unknown as Weapon
      )
      .filter((weapon) => weapon.name !== ""),
    bio: Object.fromEntries(
      Object.entries(values.bio)
        .map(([key, text]) => [key, text.trim()])
        .filter(([, text]) => text !== "")
    ),
    skills,
  };
}
