/**
 * Where each county's number is written: the point inside the county furthest from its edge, computed once from
 * the shapes in counties.ts by sampling them on a grid, not placed by hand. The positions are in the map's own
 * coordinates, its viewBox, so they hold on the map and in the capital region's inset alike.
 */

export interface CountyLabel {
    id: string;
    x: number;
    y: number;
}

export const COUNTY_LABELS: CountyLabel[] = [
    { id: "etela-savon_hyvinvointialue", x: 1123.6, y: 2371.2 },
    { id: "pohjois-karjalan_hyvinvointialue", x: 1496.9, y: 2024.7 },
    { id: "kainuun_hyvinvointialue", x: 1280.8, y: 1590.7 },
    { id: "pohjois-pohjanmaan_hyvinvointialue", x: 884.6, y: 1641.4 },
    { id: "pohjois-savon_hyvinvointialue", x: 1127.1, y: 1921.7 },
    { id: "keski-suomen_hyvinvointialue", x: 875.8, y: 2161.1 },
    { id: "etela-karjalan_hyvinvointialue", x: 1210.0, y: 2544.6 },
    { id: "kymenlaakson_hyvinvointialue", x: 1060.0, y: 2633.9 },
    { id: "lansi-uudenmaan_hyvinvointialue", x: 682.3, y: 2756.8 },
    { id: "paijat-hameen_hyvinvointialue", x: 911.9, y: 2487.3 },
    { id: "kanta-hameen_hyvinvointialue", x: 723.3, y: 2586.8 },
    { id: "pirkanmaan_hyvinvointialue", x: 637.8, y: 2378.0 },
    { id: "lapin_hyvinvointialue", x: 1020.8, y: 804.9 },
    { id: "etela-pohjanmaan_hyvinvointialue", x: 614.5, y: 2033.7 },
    { id: "keski-pohjanmaan_hyvinvointialue", x: 725.0, y: 1857.4 },
    { id: "pohjanmaan_hyvinvointialue", x: 566.2, y: 1837.5 },
    { id: "satakunnan_hyvinvointialue", x: 424.6, y: 2337.1 },
    { id: "varsinais-suomen_hyvinvointialue", x: 479.4, y: 2642.4 },
    { id: "ahvenanmaa", x: 72.9, y: 2750.4 },
    { id: "helsingin_kaupunki", x: 785.6, y: 2779.7 },
    { id: "vantaan_ja_keravan_hyvinvointialue", x: 778.7, y: 2754.6 },
    { id: "ita-uudenmaan_hyvinvointialue", x: 965.2, y: 2686.9 },
    { id: "keski-uudenmaan_hyvinvointialue", x: 786.7, y: 2694.3 },
];

/**
 * Where the capital region's numbers go on the map when there is no inset. Helsinki's and Vantaa's centres are a few
 * pixels apart, so Helsinki's number is moved into the sea below it.
 */
export const WITHOUT_INSET: Record<string, { x: number; y: number }> = {
    helsingin_kaupunki: { x: 785.6, y: 2830 },
};

/** The counties too small to point at on the map, drawn again larger in the inset. */
export const CAPITAL_REGION = ["helsingin_kaupunki", "vantaan_ja_keravan_hyvinvointialue", "keski-uudenmaan_hyvinvointialue"];

/** The part of the map the inset shows, as a viewBox: the capital region with a little room around it. */
export const INSET_VIEW_BOX = "718.8 2593.1 169.3 237.7";

/** The counties that reach into the inset, so it draws only those. */
export const INSET_COUNTIES = [
    "lansi-uudenmaan_hyvinvointialue",
    "paijat-hameen_hyvinvointialue",
    "kanta-hameen_hyvinvointialue",
    "helsingin_kaupunki",
    "vantaan_ja_keravan_hyvinvointialue",
    "ita-uudenmaan_hyvinvointialue",
    "keski-uudenmaan_hyvinvointialue",
];
