import { expect, test, vi } from "vitest";

// The same file loaded twice in one page, as two dashboard resources of the card with different versions in their URLs.
test("the card loaded twice registers once, throws nothing and is listed and logged once", async () => {
    const info = vi.spyOn(console, "info").mockImplementation(() => undefined);

    await import("../src/thl-card");
    const card = customElements.get("thl-card");
    const editor = customElements.get("thl-card-editor");
    vi.resetModules();
    await expect(import("../src/thl-card")).resolves.toBeDefined();

    expect(customElements.get("thl-card")).toBe(card);
    expect(customElements.get("thl-card-editor")).toBe(editor);
    const registry = window as unknown as { customCards?: { type: string }[] };
    expect(registry.customCards?.filter((entry) => entry.type === "thl-card")).toHaveLength(1);
    expect(info).toHaveBeenCalledTimes(1);
});
