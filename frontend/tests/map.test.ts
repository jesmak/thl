import { describe, expect, it } from "vitest";

import { COUNTIES, OUTLINES } from "../src/map/counties";
import { COUNTY_LABELS } from "../src/map/labels";

/** The areas the thl integration publishes; the map has to match them exactly. */
const AREA_IDS = [
    "ita-uudenmaan_hyvinvointialue",
    "keski-uudenmaan_hyvinvointialue",
    "lansi-uudenmaan_hyvinvointialue",
    "vantaan_ja_keravan_hyvinvointialue",
    "varsinais-suomen_hyvinvointialue",
    "satakunnan_hyvinvointialue",
    "kanta-hameen_hyvinvointialue",
    "pirkanmaan_hyvinvointialue",
    "paijat-hameen_hyvinvointialue",
    "kymenlaakson_hyvinvointialue",
    "etela-karjalan_hyvinvointialue",
    "etela-savon_hyvinvointialue",
    "pohjois-savon_hyvinvointialue",
    "pohjois-karjalan_hyvinvointialue",
    "keski-suomen_hyvinvointialue",
    "etela-pohjanmaan_hyvinvointialue",
    "pohjanmaan_hyvinvointialue",
    "keski-pohjanmaan_hyvinvointialue",
    "pohjois-pohjanmaan_hyvinvointialue",
    "kainuun_hyvinvointialue",
    "lapin_hyvinvointialue",
    "helsingin_kaupunki",
    "ahvenanmaa",
];

describe("the map", () => {
    it("has a shape for every area the integration reports", () => {
        expect(COUNTIES.map((county) => county.id).sort()).toEqual([...AREA_IDS].sort());
    });

    it("labels every shape, and only shapes it has", () => {
        expect(COUNTY_LABELS.map((label) => label.id).sort()).toEqual([...AREA_IDS].sort());
    });

    it("draws each shape once", () => {
        expect(new Set(COUNTIES.map((county) => county.id)).size).toBe(COUNTIES.length);
    });

    it("gives every shape path data", () => {
        for (const county of COUNTIES) {
            expect(county.d.length, county.id).toBeGreaterThan(100);
            expect(county.d.startsWith("m") || county.d.startsWith("M"), county.id).toBe(true);
        }
    });

    it("draws one outline under the counties and one over them", () => {
        expect(OUTLINES.map((outline) => outline.layer)).toEqual(["under", "over"]);
    });
});
