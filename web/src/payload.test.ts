import { describe, expect, it } from "vitest";
import { buildPayload, type FormValues } from "./payload";

function baseValues(overrides: Partial<FormValues> = {}): FormValues {
  return {
    name: "탐사자",
    occupation: "",
    age: "",
    sex: "",
    residence: "",
    birthplace: "",
    str: "",
    dex: "",
    pow: "",
    con: "",
    app: "",
    edu: "",
    siz: "",
    int: "",
    mov: "",
    majorWound: false,
    mpDepleted: false,
    weapons: [],
    bio: {},
    skills: [],
    ...overrides,
  };
}

describe("buildPayload", () => {
  it("trims the name field", () => {
    const payload = buildPayload(baseValues({ name: "  탐사자  " }));
    expect(payload.name).toBe("탐사자");
  });

  it("converts blank numeric fields to null", () => {
    const payload = buildPayload(baseValues({ age: "" }));
    expect(payload.age).toBeNull();
  });

  it("parses numeric fields as integers", () => {
    const payload = buildPayload(baseValues({ str: "50" }));
    expect(payload.str).toBe(50);
  });

  it("drops skill rows with a blank name or value", () => {
    const payload = buildPayload(
      baseValues({
        skills: [
          { name: "회계", value: "40" },
          { name: "", value: "10" },
          { name: "심리학", value: "" },
        ],
      })
    );
    expect(payload.skills).toEqual({ 회계: 40 });
  });

  it("passes the manual status checkboxes through as booleans", () => {
    const payload = buildPayload(baseValues({ majorWound: true, mpDepleted: false }));
    expect(payload.major_wound).toBe(true);
    expect(payload.mp_depleted).toBe(false);
  });

  it("keeps weapon rows that have a name and trims their values", () => {
    const payload = buildPayload(
      baseValues({
        weapons: [
          {
            name: "  권총 .38  ",
            skill: "권총",
            damage: "1d10",
            range: "15m",
            attacks: "1(3)",
            ammo: "6",
            malfunction: "100",
          },
        ],
      })
    );
    expect(payload.weapons).toEqual([
      {
        name: "권총 .38",
        skill: "권총",
        damage: "1d10",
        range: "15m",
        attacks: "1(3)",
        ammo: "6",
        malfunction: "100",
      },
    ]);
  });

  it("drops weapon rows without a name", () => {
    const payload = buildPayload(
      baseValues({
        weapons: [
          {
            name: "  ",
            skill: "",
            damage: "1d10",
            range: "",
            attacks: "",
            ammo: "",
            malfunction: "",
          },
        ],
      })
    );
    expect(payload.weapons).toEqual([]);
  });

  it("keeps only non-empty bio fields, trimmed", () => {
    const payload = buildPayload(
      baseValues({ bio: { gear: "  손전등  ", traits: "", phobias: "   " } })
    );
    expect(payload.bio).toEqual({ gear: "손전등" });
  });

  it("trims skill names before using them as keys", () => {
    const payload = buildPayload(
      baseValues({ skills: [{ name: "  회계  ", value: "40" }] })
    );
    expect(payload.skills).toEqual({ 회계: 40 });
  });
});
