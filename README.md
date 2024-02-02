# THL Covid stats for Home Assistant

## What is it?

A custom component that integrates with Finnish Institute for Health and Welfare's open data API to retrieve
Covid-19 statistics.

## Installation

### With HACS

1. Add this repository to HACS custom repositories
2. Search for THL Covid statistics in HACS and install with type integration
3. Restart Home Assistant
4. Enter your account credentials and configre other settings as you wish

### Manual

1. Download source code from latest release tag
2. Copy custom_components/thl_covid folder to your Home Assistant installation's config/custom_components folder.
3. Restart Home Assistant
4. Configure the integration by adding a new integration in settings/integrations page of Home Assistant

### Integration settings

| Name     | Type   | Requirement  | Description                                                           | Default |
|----------|--------| ------------ |-----------------------------------------------------------------------|---------|
| language | enum   | **Required** | Language selection                                                    | `fi`    |


### State attributes

As the state, this integration returns last week's Covid count for the whole country. There are also extra attributes
with area specific data and change numbers etc.

| Name          | Type   | Description                     |
|---------------|--------|---------------------------------|
| values        | Area[] | List of areas and their details |

### Area specific attributes

| Name                 | Type   | Description                                             |
|----------------------|--------|---------------------------------------------------------|
| name                 | string | Human readable name                                     |
| amount_last_week     | int    | Covid count for last week                               |
| amount_two_weeks_ago | int    | Covid count two weeks ago                               |
| change_in_numbers    | int    | Change between two weeks ago and last week (count)      |
| change_percentage    | int    | Change between two weeks ago and last week (percentage) |
| last_week            | int    | Week number for last week (latest data)                 |
| area_id              | string | Internal ID for the area                                |

### Displaying data in Lovelace

You can of course use the data however you want, but there is also a custom card done specifically for this integration, 
[thl-covid-card](https://github.com/jesmak/thl-covid-card).