import { expect, test, type Page } from "@playwright/test";

// The GitHub Pages build (doc/Plan.md, Phase 9), served under its subpath with the exported
// data: run with E2E_STATIC=1 and E2E_BASE_URL=http://web-static:4173/h_clusters/ (compose.yaml).
test.skip(!process.env.E2E_STATIC, "static build only");

/** Data files that came back missing, except resources the live API also lacks for some
 * structures (normal modes of atoms, bond orders of structures outside the bonds study). */
function watchMissing(page: Page): string[] {
  const missing: string[] = [];
  page.on("response", (r) => {
    const url = r.url();
    if (r.status() >= 400 && url.includes("/data/") && !/\/structures\/\d+\/(modes|bonds)\.json$/.test(url))
      missing.push(`${r.status()} ${url}`);
  });
  return missing;
}

test("grid → species detail from exported files, under the base path", async ({ page }) => {
  const missing = watchMissing(page);
  await page.goto("./");
  await expect(page).toHaveURL(/\/h_clusters\/#\/c\/baseline/);
  const cell = page.getByRole("gridcell", { name: /^H5\+ \(1\)/ });
  await expect(cell).toContainText("bound + ZPE");
  await cell.click();
  await expect(page).toHaveURL(/#\/c\/baseline\/s\/5\/1\/1/);
  await expect(page.getByRole("heading", { level: 1 })).toContainText("H₅⁺");
  await expect(page.locator("canvas").first()).toBeVisible();
  await expect(page.getByRole("heading", { name: "Bond orders" })).toBeVisible();
  await expect(page.getByText(/Static snapshot: values precomputed at 21 temperatures × 10 pressures/)).toBeVisible();
  expect(missing).toEqual([]);
});

test("deep links load, and temperature snaps to the exported grid", async ({ page }) => {
  const missing = watchMissing(page);
  await page.goto("./#/c/baseline?q=d_g&color=value&T=20");
  const cell = page.getByRole("gridcell", { name: /^H7\+ \(1\)/ });
  await expect(cell).toContainText("+");
  await expect(page.locator("output[for=temperature]")).toContainText("18.2 K"); // nearest to 20 K
  await page.goto("./#/c/baseline?q=d_g&color=value&T=1000");
  await expect(cell).toContainText("−"); // falls apart when hot
  await page.goto("./#/c/baseline/studies");
  await expect(page.getByRole("heading", { name: /Bond orders/ })).toBeVisible();
  await page.goto("./#/c/baseline/benchmark");
  await expect(page.getByText("ωB97X-D4/def2-TZVPPD").first()).toBeVisible();
  expect(missing).toEqual([]);
});
