import { expect, test } from "@playwright/test";

// Plan §6: one smoke test of grid → detail against the real API and database.
test.skip(!!process.env.E2E_STATIC, "live stack only");

test("grid → species detail", async ({ page }) => {
  await page.goto("/");
  await expect(page).toHaveURL(/\/c\/baseline/);
  const cell = page.getByRole("gridcell", { name: /^H3\+ \(1\)/ });
  await expect(cell).toBeVisible();
  await expect(cell).toContainText("bound + ZPE");

  await cell.click();
  await expect(page).toHaveURL(/\/c\/baseline\/s\/3\/1\/1/);
  await expect(page.getByRole("heading", { level: 1 })).toContainText("H₃⁺");
  await expect(page.getByText("Ways to fall apart")).toBeVisible();
  await expect(page.getByText("H₂ + H⁺").first()).toBeVisible(); // the weakest channel
  await expect(page.locator("canvas").first()).toBeVisible(); // the 3D viewer
});

test("temperature changes the free-energy grid", async ({ page }) => {
  await page.goto("/c/baseline?q=d_g&color=value&T=20");
  const cell = page.getByRole("gridcell", { name: /^H7\+ \(1\)/ });
  await expect(cell).toContainText("+");
  await page.goto("/c/baseline?q=d_g&color=value&T=1000");
  await expect(cell).toContainText("−"); // falls apart when hot
});
