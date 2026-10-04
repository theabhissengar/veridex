import { expect, test } from "@playwright/test";

test("case list calls the API health endpoint from the browser", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByText("API health: ok")).toBeVisible();
  await page.getByPlaceholder("Case title").fill("Playwright case");
  await page.getByRole("button", { name: "Create case" }).click();
  await expect(page.getByRole("link", { name: "Playwright case" })).toBeVisible();
});
