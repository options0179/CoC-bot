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
  skills: { name: string; value: string }[];
}

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
    skills,
  };
}
