import { describe, expect, it } from "vitest";
import { act, render, screen } from "@testing-library/react";
import { en, type Key } from "./en";
import { ja } from "./ja";
import { LangProvider, translate, useLang } from "./index";

const placeholders = (text: string) => [...text.matchAll(/\{(\w+)\}/g)].map((m) => m[1]).sort();

describe("dictionaries", () => {
  it("fill placeholders and leave unknown ones visible", () => {
    expect(translate("en", "campaign.states", { n: 56 })).toBe("56 states");
    expect(translate("ja", "campaign.states", { n: 56 })).toBe("56 状態");
    expect(translate("en", "campaign.states")).toBe("{n} states");
  });
  it("Japanese has every key, non-empty, with the same placeholders as English", () => {
    for (const key of Object.keys(en) as Key[]) {
      expect(ja[key], key).toBeTruthy();
      expect(placeholders(ja[key]), key).toEqual(placeholders(en[key]));
    }
  });
  it("translates the words that matter, following the wiki's terms", () => {
    expect(ja["verdict.bound_with_zpe"]).toBe("零点エネルギー込みで束縛");
    expect(ja["charge.-1"]).toBe("アニオン");
    expect(ja["mult.2"]).toBe("二重項");
  });
});

function Switch() {
  const { lang, setLang, t } = useLang();
  return <button onClick={() => setLang(lang === "en" ? "ja" : "en")}>{t("nav.trends")}</button>;
}

describe("language switch", () => {
  it("changes the text, <html lang> and the remembered choice", () => {
    render(<LangProvider lang="en"><Switch /></LangProvider>);
    const button = screen.getByRole("button");
    expect(button).toHaveTextContent("Trends");
    expect(document.documentElement.lang).toBe("en");
    act(() => button.click());
    expect(button).toHaveTextContent("傾向");
    expect(document.documentElement.lang).toBe("ja");
    expect(localStorage.getItem("lang")).toBe("ja");
  });
});
