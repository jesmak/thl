import en from "./languages/en.json";
import fi from "./languages/fi.json";

const LANGUAGES: Record<string, Record<string, string>> = { en, fi };

/**
 * A text in the viewer's language, falling back to English. `pt-BR` reads a `pt-br` table first, then `pt`.
 * `{name}` in a text is replaced from `replacements`.
 */
export function translate(language: string | undefined, key: string, replacements: Record<string, string> = {}): string {
    const tag = (language ?? "en").trim().toLowerCase().replace(/_/g, "-");
    const table = LANGUAGES[tag] ?? LANGUAGES[tag.split("-")[0]] ?? LANGUAGES.en;
    let text = table[key] ?? LANGUAGES.en[key] ?? key;

    for (const [name, value] of Object.entries(replacements)) {
        text = text.replace(`{${name}}`, value);
    }
    return text;
}

/** The language to use before Home Assistant has handed the card its own. */
export function browserLanguage(): string {
    return document.documentElement.lang || navigator.language || "en";
}
