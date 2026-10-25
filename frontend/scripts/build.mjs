/**
 * Bundles src/ into the single file the integration serves, custom_components/thl/www/thl-card.js
 *
 * The card carries the integration's version, as the two are released together. lit is bundled, as Home Assistant
 * doesn't hand cards a copy of it. The output is not minified, so anyone can read what runs in their browser. Most of
 * its size is the map of Finland, which doesn't compress away in either case.
 */
import { build } from "esbuild";
import { readFile } from "node:fs/promises";

const manifest = JSON.parse(await readFile(new URL("../../custom_components/thl/manifest.json", import.meta.url), "utf8"));

await build({
    entryPoints: ["src/thl-card.ts"],
    outfile: "../custom_components/thl/www/thl-card.js",
    bundle: true,
    format: "esm",
    target: "es2020",
    minify: false,
    legalComments: "none",
    banner: {
        js:
            `/*! thl-card ${manifest.version} | MIT License | Includes a map adapted from Hyvinvointialueet.svg by Fenn-O-maniC, ` +
            "CC BY-SA 4.0, see https://github.com/jesmak/thl/blob/main/LICENSE-map */",
    },
    define: {
        __CARD_VERSION__: JSON.stringify(manifest.version),
    },
    logLevel: "info",
});
