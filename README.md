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



If you need more endpoints, please submit your request to
[ideas.keboola.com](https://ideas.keboola.com/)

Configuration
=============

##Authorization configuration

- API Token (#api_token) - [REQ] API token generated following the steps in the Prerequisites

##Configuration

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
- Campaigns : Additional Options (campaigns_settings) - [OPT] Additional options if campaigns are being downloaded
  - Channel Options (fetch_campaign_channels) - [OPT] Campaign channels (sms, email). Defaults to all channels.
- Catalogs : Additional Options (catalogs_settings) - [OPT] Additional options if catalogs are being downloaded
  - Fetch Catalog Categories (fetch_catalog_categories) - [OPT] Boolean value to indicate if catalog categories should be fetched
- Events : Additional Options (events_settings) - [OPT] Additional options if events are being downloaded
  - Fetch Events From Date (date_from) - [OPT] Date from which event data is downloaded. Either date in YYYY-MM-DD format
    or relative date string i.e. 5 days ago, 1 month ago, yesterday, etc. You can also set this as last run, which will
    fetch data from the last run of the component.
  - Fetch Events To Date (date_to) - [OPT] Date to which event data is downloaded. Either date in YYYY-MM-DD format or
    relative date string i.e. 5 days ago, 1 month ago, now, etc.
  - Shorten Column Names (shorten_column_names) - [OPT] Boolean value to indicate if column names should be shortened - `event_properties_` prefix is replaced with `ep_`.
- Flows : Additional Options (flows_settings) - [OPT] Additional options if flows are being downloaded
  - Fetch Flow Actions (fetch_flows) - [OPT] Boolean value to indicate if flow actions should be fetched
- Profiles : Additional Options (profiles_settings) - [OPT] Additional options if profiles are being downloaded
  - Fetch Profiles Mode (fetch_profiles_mode) - [OPT] either "fetch_all", "fetch_by_segment", "fetch_by_list". 
"fetch_all" extracts all profiles.
"fetch_by_list" extracts all profiles contained in specific lists, specified in the list of List IDs.
"fetch_by_segment" extracts all profiles contained in specific segments, specified in the list of Segment IDs.        
  - List IDs (fetch_profiles_by_list) - [OPT] array of list IDs
  - Segment IDs (fetch_profiles_by_segment) - [OPT] array of segment IDs

**Note:** Events endpoint contains deeply nested data, which can lead to long column names. This has to be addressed using Rename Columns processor.

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
      "templates": false
    },
    "campaigns_settings": {
      "fetch_campaign_recipients": true
    },
    "catalogs_settings": {
      "fetch_catalog_categories": true
    },
    "events_settings": {
      "date_from": "last run",
      "date_to": "now"
    },
    "profiles_settings": {
      "fetch_profiles_mode": "fetch_by_segment",
      "fetch_profiles_by_segment": ["segid"]
    }
  },
  "action": "run"
}
```

Output
======

List of tables, foreign keys, schema.

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