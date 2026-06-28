DOMAIN = "thl"
API_DIMENSIONS_URL = "https://sampo.thl.fi/pivot/prod/{lang}/ttr/casesweek/fact_ttr_casesweek.dimensions.json"
API_DATA_URL = "https://sampo.thl.fi/pivot/prod/{lang}/ttr/casesweek/fact_ttr_casesweek.json?row=hva-{area_sid}&column=yearweek-{week_sid}&filter=nidrreportgroup-{disease_id}"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/106.0.5249.62 Safari/537.36"

LANGUAGES = ["en", "fi"]

STR_ALL_AREAS = {"fi": "Kaikki hyvinvointialueet", "en": "All areas"}
STR_ALL_TIMES = {"fi": "Kaikki viikot", "en": "All times"}
STR_TIME = {"fi": "Vuosi {year} Viikko {week}", "en": "Year {year} Week {week}"}

CONF_LANGUAGE = "language"
CONF_DISEASE_ID = "disease_id"
CONF_DISEASE_NAME = "disease_name"

ATTR_DISEASE_ID = "disease_id"
ATTR_DISEASE_NAME = "disease_name"

AREA_IDS = {
    841988: "finland",
    837181: "ita-uudenmaan_hyvinvointialue",
    837147: "keski-uudenmaan_hyvinvointialue",
    839479: "lansi-uudenmaan_hyvinvointialue",
    838611: "vantaan_ja_keravan_hyvinvointialue",
    838879: "varsinais-suomen_hyvinvointialue",
    838312: "satakunnan_hyvinvointialue",
    840691: "kanta-hameen_hyvinvointialue",
    838364: "pirkanmaan_hyvinvointialue",
    836484: "paijat-hameen_hyvinvointialue",
    838636: "kymenlaakson_hyvinvointialue",
    837587: "etela-karjalan_hyvinvointialue",
    838539: "etela-savon_hyvinvointialue",
    841279: "pohjois-savon_hyvinvointialue",
    836414: "pohjois-karjalan_hyvinvointialue",
    836460: "keski-suomen_hyvinvointialue",
    841691: "etela-pohjanmaan_hyvinvointialue",
    836916: "pohjanmaan_hyvinvointialue",
    838714: "keski-pohjanmaan_hyvinvointialue",
    836191: "pohjois-pohjanmaan_hyvinvointialue",
    840852: "kainuun_hyvinvointialue",
    838893: "lapin_hyvinvointialue",
    839511: "helsingin_kaupunki",
    840333: "ahvenanmaa"
}
