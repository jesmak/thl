# THL disease statistics for Home Assistant

Home Assistant integration for the weekly infectious disease numbers published by the Finnish Institute for Health and
Welfare (THL).

[![GitHub Release][releases-shield]][releases] [![GitHub Release Date][release-date-shield]][releases] [![HACS][hacs-shield]][hacs] [![License][license-shield]](LICENSE)

<img src="https://raw.githubusercontent.com/jesmak/thl/main/docs/images/dashboard-light.png#gh-light-mode-only" width="1000" alt="A dashboard with four maps of Finland's wellbeing services counties, coloured by incidence: COVID-19, influenza, flu-like illness visits and norovirus in February, each with Pirkanmaa's figures and its trend over 26 weeks">
<img src="https://raw.githubusercontent.com/jesmak/thl/main/docs/images/dashboard-dark.png#gh-dark-mode-only" width="1000" alt="A dashboard with four maps of Finland's wellbeing services counties, coloured by incidence: COVID-19, influenza, flu-like illness visits and norovirus in February, each with Pirkanmaa's figures and its trend over 26 weeks">

The data in the picture is made up.

## What is it?

A custom component that follows the weekly numbers of infectious diseases from the open data of the Finnish Institute
for Health and Welfare (THL). Each disease is added separately, and gets sensors for its cases and its incidence per
100 000 people, in the whole country and in every wellbeing services county.

It can also follow **flu-like illness visits** in primary care: the share of all visits made for influenza-like
illness, in the whole country and in every county. These show a flu season starting before the lab-confirmed cases do.

Sensors get the past year written into their statistics, so graphs have a history from the start, and the statistics
follow the figures THL corrects later.

The numbers can be shown with the [THL card](#thl-card) that comes with the integration, which draws them on a map of
Finland.

## Installation

### With HACS

1. Add this repository to HACS custom repositories with type **Integration**
2. Search for THL disease statistics in HACS and download it
3. Restart Home Assistant
4. Add the integration in Settings › Devices & services, and choose a disease

### Manual

1. Download the source code from the latest release
2. Copy the `custom_components/thl` folder to your Home Assistant installation's `config/custom_components` folder
3. Restart Home Assistant
4. Add the integration in Settings › Devices & services, and choose a disease

## Settings

Adding the integration takes two steps: first the language, then the first disease from the list THL reports. Every
further disease is added from the integration page with **Add disease**; the diseases already being followed are left
out of the list. The flu-like illness visits are added from the same page with **Add flu-like illness visits**.

To change the language later, choose **Reconfigure** from the integration's menu. Everything being followed is
renamed in the new language, and so are the areas in the sensor attributes. The ids in the attributes never change.

| Name     | Type | Description                                              | Default                   |
| -------- | ---- | -------------------------------------------------------- | ------------------------- |
| Language | enum | The language of the disease and area names: `fi` or `en` | Home Assistant's language |
| Disease  | enum | One of the diseases THL reports weekly                   |                           |

## Sensors

THL publishes a week's numbers during the following week, so every sensor shows the newest week that has numbers in
it, up to four weeks back. Its `last_week` attribute tells which week that is. The flu-like illness visits skip a week
that THL has listed but not yet filled in. A sensor is unavailable while THL can't be reached, or when none of the last
four weeks has numbers.

### A disease

Each disease is a device named after it, such as **THL Influenssa**, with these sensors:

| Sensor                                       | State                                  | Example                                            |
| -------------------------------------------- | -------------------------------------- | -------------------------------------------------- |
| The disease                                  | Cases in the whole country             | `sensor.thl_influenssa`                            |
| Incidence                                    | Cases per 100 000 in the whole country | `sensor.thl_influenssa_ilmaantuvuus`               |
| One per wellbeing services county            | Cases in the county                    | `sensor.thl_influenssa_etela_karjala`              |
| One per wellbeing services county, incidence | Cases per 100 000 in the county        | `sensor.thl_influenssa_etela_karjala_ilmaantuvuus` |

Incidence is what makes the counties comparable: a large county has more cases simply because more people live there.

The whole country's cases sensor carries every area in its `values` attribute, which is what the THL card reads:

| Key                       | Description                                    |
| ------------------------- | ---------------------------------------------- |
| `name`                    | The area's name in the chosen language         |
| `area_id`                 | The area's id, `finland` for the whole country |
| `amount_last_week`        | Cases last week                                |
| `amount_two_weeks_ago`    | Cases the week before                          |
| `change_in_numbers`       | The difference between the two weeks           |
| `change_percentage`       | The difference as a percentage                 |
| `incidence_last_week`     | Cases per 100 000 last week                    |
| `incidence_two_weeks_ago` | Cases per 100 000 the week before              |
| `entity_id`               | The area's cases sensor                        |
| `incidence_entity_id`     | The area's incidence sensor                    |

The figures of the week before are missing when THL hasn't published it. The `values` attribute isn't stored in the
recorder; each area's own sensors are.

### Flu-like illness visits

A device named **THL Influenssankaltaiset käynnit** (or **THL Flu-like illness visits**), with a sensor for the
whole country and one per county. The state is the percentage of all primary care visits that were made for
influenza-like illness. It is a small number outside the flu season: around 0.01 %.

The whole country's sensor carries the name of the visits in its `disease_name` attribute, as a disease's does, which
is what the THL card shows as its title, and every area in its `values` attribute:

| Key                    | Description                                       |
| ---------------------- | ------------------------------------------------- |
| `name`, `area_id`      | As for a disease                                  |
| `share_last_week`      | The share of flu-like illness visits last week, % |
| `share_two_weeks_ago`  | The same the week before                          |
| `visits_last_week`     | Visits for flu-like illness last week             |
| `all_visits_last_week` | All primary care visits last week                 |
| `entity_id`            | The area's sensor                                 |

### The history

When a sensor is added, the past year is written into its statistics, a year and a week to be exact, so the same week a
year ago is there too. Each week's figure is placed in the week after it, which is when the sensor shows it.

THL fills in a week's numbers during the weeks after it, so a figure the sensor showed may be corrected later. The
statistics follow THL. At every start, and whenever THL changes a figure, each week of the past year is given the figure
THL has for it now. A week without statistics gets one row at its start, and in a week the recorder kept, every hour it
recorded is given the figure, including the hours when the sensor still showed the week before. Hours the recorder
didn't keep, such as while THL couldn't be reached, stay empty. A sensor enabled later gets its past when it is added.

A graph therefore shows each week about a week after the week it describes. The shape of the curve is the same.

## THL card

<p>
<img src="https://raw.githubusercontent.com/jesmak/thl/main/docs/images/thl-card-country-light.png#gh-light-mode-only" width="400" alt="Influenza on a map of Finland's wellbeing services counties, each coloured by its incidence against the whole country and labelled with its cases, the whole country's figures beside the map, the capital region enlarged below them, a colour key and a six-month trend">
<img src="https://raw.githubusercontent.com/jesmak/thl/main/docs/images/thl-card-country-dark.png#gh-dark-mode-only" width="400" alt="Influenza on a map of Finland's wellbeing services counties, each coloured by its incidence against the whole country and labelled with its cases, the whole country's figures beside the map, the capital region enlarged below them, a colour key and a six-month trend">
<img src="https://raw.githubusercontent.com/jesmak/thl/main/docs/images/thl-card-county-light.png#gh-light-mode-only" width="400" alt="Buttons for influenza and norovirus over the map, coloured by the change from the week before, with Pirkanmaa chosen and outlined, its figures including the same week a year ago, and its own trend">
<img src="https://raw.githubusercontent.com/jesmak/thl/main/docs/images/thl-card-county-dark.png#gh-dark-mode-only" width="400" alt="Buttons for influenza and norovirus over the map, coloured by the change from the week before, with Pirkanmaa chosen and outlined, its figures including the same week a year ago, and its own trend">
</p>

The integration comes with a dashboard card that draws one disease, or the flu-like illness visits, on a map of the
wellbeing services counties. Each county is coloured by how it compares with the whole country, or by how its cases
changed from the week before. Clicking a county shows its own figures and trend.

One card can switch between several diseases. The capital region, whose counties are too small to point at on the map,
is drawn again larger under the figures.

The integration serves the card itself and adds it to the dashboards' resources when it starts, so the card is always
the integration's own version. With the resources set in YAML (`resource_mode: yaml`), it can't add or update
itself, and the log says which line to add, change or remove.

### Card options

The card has a visual editor. Add it from the card picker and choose the disease. The options can also be written by
hand.

| Name           | Type           | Description                                                                                                                                                                                                                                                                                                                                                                                                              | Default                                                                         |
| -------------- | -------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------- |
| `type`         | string         | **Required.** `custom:thl-card`                                                                                                                                                                                                                                                                                                                                                                                          |                                                                                 |
| `entity`       | string or list | **Required.** The whole country's sensor of a disease, or of the flu-like illness visits, or a list of them                                                                                                                                                                                                                                                                                                              |                                                                                 |
| `color_by`     | string         | `level` compares each county with the whole country, `change` with its own week before                                                                                                                                                                                                                                                                                                                                   | `level`                                                                         |
| `default_area` | string         | The `area_id` of a county chosen whenever the card loads, such as `pirkanmaan_hyvinvointialue`                                                                                                                                                                                                                                                                                                                           | the whole country                                                               |
| `show_trend`   | boolean        | A line of the chosen area's past six months under its figures                                                                                                                                                                                                                                                                                                                                                            | `true`                                                                          |
| `show_inset`   | boolean        | The capital region drawn again larger under the figures                                                                                                                                                                                                                                                                                                                                                                  | `true`                                                                          |
| `show_key`     | boolean        | A key under the map that says what the colours mean                                                                                                                                                                                                                                                                                                                                                                      | `true`                                                                          |
| `map_width`    | number         | The map's width, in pixels. Held to a height, the map shrinks below it to fit                                                                                                                                                                                                                                                                                                                                            | follows the card                                                                |
| `height_mode`  | string         | How tall the card is. `auto` fits its content, `fixed` keeps it at `height`, `max` lets it grow up to `max_height`. In `fixed` and `max` nothing scrolls. The disease stays at the top, the key and the trend at the bottom, and the map between them shrinks to fit. The card never gets lower than these need with a map 200 px high, and in a card narrower than a full section, also what the figures need, as they go under the map there. A height in grid rows, set in the layout tab of a sections view, is used instead | `fixed` when `height` is set, `max` when only `max_height` is, otherwise `auto` |
| `height`       | number         | The card's height in pixels, for `fixed`                                                                                                                                                                                                                                                                                                                                                                                 |                                                                                 |
| `max_height`   | number         | The card's greatest height in pixels, for `max`                                                                                                                                                                                                                                                                                                                                                                          |                                                                                 |

### The map

Each county is coloured, and its cases, or for the flu-like illness visits the visits, are written at its middle.
Clicking a county chooses it and outlines it, and clicking it again goes back to the whole country. The counties can
also be chosen from the keyboard, with Tab and Enter.

Helsinki and Vantaa and Kerava are a few pixels each on the map. The capital region is therefore drawn again about five
times larger under the figures, with a dashed frame on the map around what it shows. Its counties and their numbers
are chosen there. With `show_inset: false` it is left out, and their numbers are on the map with the rest, as hard to
point at as they are small.

### The colours

By default a county is coloured by its level compared with the whole country. The level is its incidence per 100,000
people for a disease, or its share of flu-like illness visits. The level is what makes counties comparable, since a
large county has more cases simply because more people live there.

| Colour      | What it means                                  |
| ----------- | ---------------------------------------------- |
| Blue        | No cases at all                                |
| Green       | Less than half the whole country's level       |
| Light green | Less than 0.8 times the whole country's level  |
| Yellow      | About the same as the whole country            |
| Orange      | More than 1.25 times the whole country's level |
| Red         | More than twice the whole country's level      |

With `color_by: change` a county is coloured by how its cases changed from the week before instead, or for the
flu-like illness visits, how their share changed:

| Colour      | What it means                                        |
| ----------- | ---------------------------------------------------- |
| Blue        | No cases at all, this week or the week before        |
| Green       | Cases fell by more than 40%                          |
| Light green | Cases fell by more than 10%                          |
| Yellow      | Little change either way, or no week to compare with |
| Orange      | Cases rose by more than 10%                          |
| Red         | Cases rose by more than 40%                          |

The key under the map gives the same bounds. A county the sensor carries no numbers for is left the colour of the
text.

### The figures and the trend

Beside or under the map are the whole country's figures, last week's cases and incidence, the week before, and the
change. A county that had no cases the week before has a dash for the change, as there is nothing to compare with. For
the flu-like illness visits they are the share of visits, how many there were, and the share the week before. A chosen
county shows its own figures instead.

The same week a year ago is shown too, when Home Assistant's statistics reach that far.

The trend covers the past six months, drawn from the statistics the integration keeps for each area's sensor. It is
the incidence when colouring by level, and the cases when colouring by change. Pointing at it, tapping it or moving
along it with the arrow keys shows a week and its figure. THL publishes a week's figures during the week after, so the
newest point is the figure the sensor shows now, and the others are each named by the week their figure is from.

### Several diseases

Given a list of sensors, the card shows buttons over the map to switch between them. The first is shown when the card
loads, and the chosen county stays chosen when switching.

### Sizes

In a sections view the card is the section's full width by default, and can be made as narrow as half the section. A
card 290 pixels wide or more, which is a whole section even in a view of four, puts the figures beside the map, over the
sea west of it, with the capital region below them. A narrower card keeps them under the map, with the capital region
under them. In a wider card the map and the figures stay together in the middle. The map grows with the card up to a
point, and the shapes and the numbers on them scale together.

<p>
<img src="https://raw.githubusercontent.com/jesmak/thl/main/docs/images/thl-card-narrow-light.png#gh-light-mode-only" width="255" alt="A narrow card with the figures, the capital region, the colour key and the trend under the map">
<img src="https://raw.githubusercontent.com/jesmak/thl/main/docs/images/thl-card-narrow-dark.png#gh-dark-mode-only" width="255" alt="A narrow card with the figures, the capital region, the colour key and the trend under the map">
</p>

Set `map_width` to fix the map's width. Held to a height, the map shrinks below it to fit.

## Examples

### The diseases on maps

The [THL card](#thl-card) draws a disease on a map of the counties. The dashboard in the picture above has one card
for each disease, all opening on the same county:

```yaml
type: custom:thl-card
entity: sensor.thl_influenssa
default_area: pirkanmaan_hyvinvointialue
```

The flu-like illness visits take the same card, with `entity: sensor.thl_influenssankaltaiset_kaynnit`.

Three diseases to switch between, coloured by change, with a county chosen when the card loads:

```yaml
type: custom:thl-card
entity:
  - sensor.thl_influenssa
  - sensor.thl_koronavirus_sars_cov_2
  - sensor.thl_norovirus
color_by: change
default_area: pirkanmaan_hyvinvointialue
```

### A county's incidence over half a year

[apexcharts-card](https://github.com/RomRider/apexcharts-card) can draw a county's incidence from its statistics:

```yaml
type: custom:apexcharts-card
graph_span: 26w
header:
  show: true
  title: Influenssa, Etelä-Karjala
  show_states: true
series:
  - entity: sensor.thl_influenssa_etela_karjala_ilmaantuvuus
    statistics:
      type: mean
      period: day
    curve: stepline
  - entity: sensor.thl_influenssa_ilmaantuvuus
    name: Koko maa
    statistics:
      type: mean
      period: day
    curve: stepline
```

## Upgrading from the separate THL card

The THL card used to be a repository of its own, THL card. It now comes with the integration, and the separate
repository has been removed. If you installed it, remove it in HACS, and check that its resource
(`/hacsfiles/thl-card/…`) is gone from Settings › Dashboards › Resources. Until it is, the log warns about it at every
start. Your dashboards need no changes, as the card's type stays `custom:thl-card`.

## Upgrading from 1.x

Nothing needs to be done. Versions before 2.0 made a separate integration entry for each disease; on the first start
they are merged into one entry with a disease inside it for each. Entity IDs and unique IDs stay as they were, so
history, statistics, dashboards, automations and the THL card keep working. The language of the merged entry is the one
most of the old entries used.

The county, incidence and flu-like illness sensors are new, and appear with six months of history. The disease sensors
that already existed keep the history they have, with THL's current figures in its past year.

## Data

The data comes from [THL's open data](https://thl.fi/en/statistics-and-data/data-and-services/open-data) under the
[Creative Commons Attribution 4.0](https://creativecommons.org/licenses/by/4.0/) licence. The disease numbers come
from the infectious diseases register, and the primary care visits from the primary health care register (Avohilmo).
Every entity credits THL in its attribution.

The THL card's map of the wellbeing services counties is adapted from
[Hyvinvointialueet.svg](https://commons.wikimedia.org/wiki/File:Hyvinvointialueet.svg) by Fenn-O-maniC on Wikimedia
Commons, licensed under [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/). The adapted map in
`frontend/src/map/counties.ts` is licensed under CC BY-SA 4.0 as well, see [LICENSE-map](LICENSE-map).

The newest weeks are read every half hour. The names of the diseases and areas are kept for half an hour and shared
by every disease.

## Translating

The texts are in `custom_components/thl/translations/`, one JSON file per language, such as `en.json` and `fi.json`.
To add a language, copy `en.json` to the new language's code and translate the values. The names of the diseases and
areas come from THL in Finnish or English.

The THL card's texts are in `frontend/src/localize/languages/`, in the same way. To add a language there, copy
`en.json` to the new language's code, translate the values, and add the file to `LANGUAGES` in
`frontend/src/localize/localize.ts`. A text left out falls back to English.

## Development

Requires the Python that the current Home Assistant release needs, 3.14 at the moment.

```
python3.14 -m venv .venv
.venv/bin/pip install -r requirements_test.txt
.venv/bin/pytest
.venv/bin/ruff check .
.venv/bin/ruff format --check .
```

The tests run on made-up data, without network access.

The THL card is in `frontend/` and requires Node 22.13 or newer:

```
cd frontend
npm install
npm run check
```

`npm run check` typechecks, lints, checks formatting, runs the tests and builds `custom_components/thl/www/thl-card.js`,
which is the file the integration serves and is committed to the repository. The card carries the integration's version
from `manifest.json`. To have git refuse a commit whose built card doesn't match `frontend/`, run
`git config core.hooksPath .githooks` once.

| Path                           | What it contains                                                              |
| ------------------------------ | ----------------------------------------------------------------------------- |
| `__init__.py`                  | Setup, and the shared dimensions                                              |
| `migration.py`                 | Merging the entries of 1.x into one                                           |
| `config_flow.py`               | The language, a subentry per disease, and one for the flu-like illness visits |
| `api.py`                       | THL's service, and one shared copy of each dimensions file                    |
| `statistics.py`                | Reading the dimensions and data files                                         |
| `coordinator.py`               | Fetching the newest weeks with figures every half hour                        |
| `sensor.py`                    | The sensors                                                                   |
| `history.py`                   | Keeping THL's figure for each past week in the statistics of the sensors      |
| `translations/<language>.json` | Home Assistant UI texts                                                       |
| `card.py`, `www/`              | Serving the THL card and adding it to the dashboards' resources               |
| `frontend/`                    | The THL card's source, tests and build                                        |

## Support

Hey dude! Help me out for a couple of :beers: or a :coffee:!

[![coffee](https://www.buymeacoffee.com/assets/img/custom_images/black_img.png)](https://www.buymeacoffee.com/jesmak)

## Thanks

To Fenn-O-maniC for the map of the wellbeing services counties that the THL card draws.

## License

MIT, see [LICENSE](LICENSE). The THL card's map is CC BY-SA 4.0, see [LICENSE-map](LICENSE-map). The data is THL's,
under CC BY 4.0.

[releases-shield]: https://img.shields.io/github/release/jesmak/thl.svg?style=for-the-badge
[release-date-shield]: https://img.shields.io/github/release-date/jesmak/thl?style=for-the-badge
[releases]: https://github.com/jesmak/thl/releases
[hacs-shield]: https://img.shields.io/badge/HACS-Custom-orange.svg?style=for-the-badge
[hacs]: https://hacs.xyz/docs/faq/custom_repositories/
[license-shield]: https://img.shields.io/github/license/jesmak/thl.svg?style=for-the-badge
