import { describe, expect, it } from "vitest";
import { buildPayload, computeHalfFifth, type FormValues } from "./payload";

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
    cash: "",
    assets: "",
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

  it("trims skill names before using them as keys", () => {
    const payload = buildPayload(
      baseValues({ skills: [{ name: "  회계  ", value: "40" }] })
    );
    expect(payload.skills).toEqual({ 회계: 40 });
  });

  it("passes cash and assets through as free text", () => {
    const payload = buildPayload(
      baseValues({ cash: "  현금 약 8만원  ", assets: "노트북, 카메라" })
    );
    expect(payload.cash).toBe("현금 약 8만원");
    expect(payload.assets).toBe("노트북, 카메라");
  });
});

describe("computeHalfFifth", () => {
  it("floors total/2 and total/5", () => {
    expect(computeHalfFifth(65)).toEqual({ half: 32, fifth: 13 });
  });

  it("returns null for non-finite input", () => {
    expect(computeHalfFifth(NaN)).toBeNull();
  });
});
