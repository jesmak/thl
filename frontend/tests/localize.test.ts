import { describe, expect, it } from "vitest";

import { translate } from "../src/localize/localize";

describe("texts", () => {
    it("are in the viewer’s language", () => {
        expect(translate("fi", "whole_country")).toBe("Koko maa");
        expect(translate("en", "whole_country")).toBe("Whole country");
    });

    it("take the language without its region", () => {
        expect(translate("fi-FI", "last_week")).toBe("Viime viikko");
        expect(translate("en_GB", "last_week")).toBe("Last week");
    });

    it("fall back to English for a language that has no translation", () => {
        expect(translate("sv", "whole_country")).toBe("Whole country");
        expect(translate(undefined, "whole_country")).toBe("Whole country");
    });

    it("fill in what the text asks for", () => {
        expect(translate("en", "entity_not_found", { entity: "sensor.thl_influenssa" })).toBe("There is no entity sensor.thl_influenssa.");
    });

    it("give back the key when there is no such text", () => {
        expect(translate("en", "no_such_key")).toBe("no_such_key");
    });
});
