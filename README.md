Klaviyo Extractor
=============

Klaviyo is a marketing automation platform, used primarily for email marketing and SMS marketing.

This component uses the Klaviyo APIs to extract data on all objects from Klaviyo.

**Table of contents:**

[TOC]

Prerequisites
=============
to get your API Token:

1. Log into your Klaviyo platform
2. Your profile name (bottom left)
3. Account
4. Settings
5. API Keys
6. Create Private API Key with Read-Only privileges

For more information follow [this guide on from Klaviyo](https://developers.klaviyo.com/en/docs/retrieve_api_credentials)

Supported endpoints
===================

- [Campaigns](https://developers.klaviyo.com/en/v1-2/reference/get-campaigns)
- [Catalogs](https://developers.klaviyo.com/en/reference/get_catalog_items)
- [Segments](https://developers.klaviyo.com/en/reference/get_segments)
- [Lists](https://developers.klaviyo.com/en/reference/get_lists)
- [Profiles](https://developers.klaviyo.com/en/reference/get_profiles)
- [Metrics](https://developers.klaviyo.com/en/reference/get_metrics)
- [Events](https://developers.klaviyo.com/en/reference/get_events)
- [Flows](https://developers.klaviyo.com/en/reference/get_flows)
- [Templates](https://developers.klaviyo.com/en/reference/get_templates)
- [Metric aggergates](https://developers.klaviyo.com/en/reference/query_metric_aggregates)



If you need more endpoints, please submit your request to
[ideas.keboola.com](https://ideas.keboola.com/)

Configuration
=============

Authorization configuration
---------------------------

- API Token (#api_token) - [REQ] API token generated following the steps in the Prerequisites

Configuration
-------------

- Endpoints (objects) - [REQ] Key value pair of Klaviyo objects and a boolean value to signify whether or not to extract them
    - Campaigns (campaigns)
    - Catalog Items (catalogs)
  - Events (events)
  - Metrics (metrics)
  - Lists (lists)
  - Segments (segments)
  - Profiles (profiles)
  - Flows (flows)
  - Templates (templates)
  - Query Metric Aggregates (metric_aggregates)
- Campaigns : Additional Options (campaigns_settings) - [OPT] Additional options if campaigns are being downloaded
  - Channel Options (fetch_campaign_channels) - [OPT] Campaign channels (sms, email). Defaults to all channels.
- Catalogs : Additional Options (catalogs_settings) - [OPT] Additional options if catalogs are being downloaded
  - Fetch Catalog Categories (fetch_catalog_categories) - [OPT] Boolean value to indicate if catalog categories should be fetched
- Time range options : Additional Options (time_range_settings) - [OPT] Additional options for the following endpoints: Events, Metric Aggregates.
  - Fetch From Date (date_from) - [OPT] Date from which data is downloaded. Either date in YYYY-MM-DD format or relative date string i.e. 5 days ago, 1 month ago, yesterday, etc. You can also set this as last run, which will fetch data from the last run of the component.
  - Fetch To Date (date_to) - [OPT] Date to which data is downloaded. Either date in YYYY-MM-DD format or relative date string i.e. 5 days ago, 1 month ago, now, etc.
- Store nested attributes (store_nested_attributes) - [OPT] You can use this options if you are fetching deeply nested attributes and you are encountering Output mapping errors due to 64 characters limit for columns. This option will store attributes in a single column.
- Flows : Additional Options (flows_settings) - [OPT] Additional options if flows are being downloaded
  - Fetch Flow Actions (fetch_flows) - [OPT] Boolean value to indicate if flow actions should be fetched
- Profiles : Additional Options (profiles_settings) - [OPT] Additional options if profiles are being downloaded
  - Fetch Profiles Mode (fetch_profiles_mode) - [OPT] either "fetch_all", "fetch_by_segment", "fetch_by_list". 
"fetch_all" extracts all profiles.
"fetch_by_list" extracts all profiles contained in specific lists, specified in the list of List IDs.
"fetch_by_segment" extracts all profiles contained in specific segments, specified in the list of Segment IDs.        
  - List IDs (fetch_profiles_by_list) - [OPT] array of list IDs
  - Segment IDs (fetch_profiles_by_segment) - [OPT] array of segment IDs
- Metric aggregates - Additional Options (metric_aggregates_settings) - [OPT] Additional options if aggregated metrics are being downloaded
  - Metric IDs (metric_aggregates_ids) - [OPT] array of metric IDs
  - Aggregate interval (metric_aggregates_interval) - [OPT] Granularity of aggregatin. Choose from "hour", "day", "week", "month"
  - Partitioning by (metric_aggregates_partitioning_by) - [OPT] Array of dimensions for partitioning aggregated values
  - (metric_aggregates_measurements) - [OPT] An array with the selected aggregation. It cannot be changed, as the endpoint returns all three values.

**Note:** Events endpoint contains deeply nested data, which can lead to long column names. This has to be addressed using Rename Columns processor or using the store_nested_attributes parameter.

Sample Configuration
=============

```json
{
  "parameters": {
    "#api_token": "SECRET_VALUE",
    "objects": {
      "campaigns": true,
      "catalogs": true,
      "events": true,
      "metrics": true,
      "lists": true,
      "segments": true,
      "profiles": true,
      "flows": false,
      "templates": false,
      "metric_aggregates": true
    },
    "campaigns_settings": {
      "fetch_campaign_recipients": true
    },
    "catalogs_settings": {
      "fetch_catalog_categories": true
    },
    "time_range_settings": {
      "date_from": "last run",
      "date_to": "now"
    },
    "profiles_settings": {
      "fetch_profiles_mode": "fetch_by_segment",
      "fetch_profiles_by_segment": ["segid"]
    },
    "metric_aggregates_settings": {
      "metric_aggregates_ids": ["metric_id e.g. SUCEUS"],
      "metric_aggregates_measurements": [
        "count", "unique", "sum_value"
      ],
      "metric_aggregates_interval": "day",
      "metric_aggregates_partitioning_by": ["dimensions_name e.g Campaign Name"]
    },
  },
  "action": "run"
}
```

Output
======

List of tables, foreign keys, schema.

Query Metric Aggregates limitations
-----------------------------------

### Empty period
When using the by parameter to aggregate data over a specified period, if no data is available for the selected time range, the endpoint returns a single aggregated value instead of a list of values for each aggregated period. In such cases, the returned values are supplemented with null values, which can result in empty columns in the output of the consuming component. This occurs because the endpoint does not return the expected data points for each aggregation period.

This behavior should be considered when processing the results, as the absence of data for specific periods may affect the integrity of the final output.

### Partitioning

In cases where data partitioning is based on specific dimensions, there are situations where some dimensions are empty or unavailable for partitioning in a given category. This can occur when a dataset is categorized by multiple dimensions, but for certain records or categories, one or more dimensions lack valid values.

When this happens, the system substitutes the empty dimension with a placeholder value:

-	“DIMENSION NOT AVAILABLE” – used when a specific dimension is missing.
-	“NO DIMENSIONS SELECTED” – used when no dimensions are selected at all.

**Examples**

No partitioning selected

| id | metric_id | date  | unique  | sum_value  | count   | dimensions   | 
| ------------ | ------------ | ------------ | ------------ | ------------ | ------------ | ------------ |
|2024-09-01T00:00:00+00:00_SUCEUS|SUCEUS|2024-09-01T00:00:00+00:00|10.0|5.0|0.0|['NO DIMENSIONS SELECTED']|

\ One existing partitioning selected

| id | metric_id | date  | unique  | sum_value  | count   | dimensions   | 
| ------------ | ------------ | ------------ | ------------ | ------------ | ------------ | ------------ |
|2024-09-01T00:00:00+00:00_SUCEUS|SUCEUS|2024-09-01T00:00:00+00:00|10.0|5.0|0.0|['Internal Klaviyo - Test Campaign Name']|

\ One existing partitioning selected and two missing selected

| id | metric_id | date  | unique  | sum_value  | count   | dimensions   | 
| ------------ | ------------ | ------------ | ------------ | ------------ | ------------ | ------------ |
|2024-09-01T00:00:00+00:00_SUCEUS|SUCEUS|2024-09-01T00:00:00+00:00|10.0|5.0|0.0|['Internal Klaviyo - Test Campaign Name', 'DIMENSION NOT AVAILABLE', 'DIMENSION NOT AVAILABLE']|

Development
-----------

If required, change local data folder (the `CUSTOM_FOLDER` placeholder) path to your custom path in
the `docker-compose.yml` file:

~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    volumes:
      - ./:/code
      - ./CUSTOM_FOLDER:/data
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Clone this repository, init the workspace and run the component with following command:

~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
docker-compose build
docker-compose run --rm dev
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Run the test suite and lint check using this command:

~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
docker-compose run --rm test
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Integration
===========

For information about deployment and integration with KBC, please refer to the
[deployment section of developers documentation](https://developers.keboola.com/extend/component/deployment/)