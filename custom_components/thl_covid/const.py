DOMAIN = "thl_covid"
API_DIMENSIONS_URL = "https://sampo.thl.fi/pivot/prod/{lang}/epirapo/covid19case/fact_epirapo_covid19case.dimensions.json"
API_DATA_URL = "https://sampo.thl.fi/pivot/prod/{lang}/epirapo/covid19case/fact_epirapo_covid19case.json?row=hcdmunicipality2020-{area_sid}&column=dateweek20200101-{week_sid}"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/106.0.5249.62 Safari/537.36"

LANGUAGES = ["en", "fi"]

STR_ALL_AREAS = {"fi": "Kaikki Alueet", "en": "All areas"}
STR_ALL_TIMES = {"fi": "Kaikki ajat", "en": "All times"}
STR_TIME = {"fi": "Vuosi {year} Viikko {week}", "en": "Year {year} Week {week}"}

CONF_LANGUAGE = "language"

AREA_IDS = {
    445131: "ahvenanmaa",
    445197: "varsinais-suomen_shp",
    445170: "satakunnan_shp",
    445206: "kanta-hameen_shp",
    445282: "pirkanmaan_shp",
    445014: "paijat-hameen_shp",
    445178: "kymenlaakson_shp",
    445043: "etela-karjalan_shp",
    445155: "etela-savon_shp",
    445175: "ita-savon_shp",
    445293: "pohjois-karjalan_shp",
    445223: "pohjois-savon_shp",
    445285: "keski-suomen_shp",
    445225: "etela-pohjanmaan_shp",
    445079: "vaasan_shp",
    445230: "keski-pohjanmaan_shp",
    444996: "pohjois-pohjanmaan_shp",
    445101: "kainuun_shp",
    445190: "lansi-pohjan_shp",
    445224: "lapin_shp",
    445193: "helsingin_ja_uudenmaan_shp",
    445222: "finland"
}
