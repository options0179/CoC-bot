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
  cash: string;
  assets: string;
  skills: { name: string; value: string }[];
}

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
  cash: string;
  assets: string;
  skills: Record<string, number>;
}

export function computeHalfFifth(total: number): { half: number; fifth: number } | null {
  if (!Number.isFinite(total)) return null;
  return { half: Math.floor(total / 2), fifth: Math.floor(total / 5) };
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
    cash: values.cash.trim(),
    assets: values.assets.trim(),
    skills,
  };
}
