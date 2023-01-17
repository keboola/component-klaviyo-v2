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
2. Your profile name (top right)
3. Account
4. Settings
5. API Keys
6. Create API Key

Supported endpoints
===================

- Campaigns
- Catalogs
- Segments
- Lists
- Profiles
- Metrics
- Events

If you need more endpoints, please submit your request to
[ideas.keboola.com](https://ideas.keboola.com/)

Configuration
=============

##Authorization configuration

- API Token (#api_token) - [REQ] description

##Configuration

- Endpoints (objects) - [REQ] description
  - Campaigns (campaigns) - [OPT] description
  - Catalog Items (catalogs) - [OPT] description
  - Events (events) - [OPT] description
  - Metrics (metrics) - [OPT] description
  - Lists (lists) - [OPT] description
  - Segments (segments) - [OPT] description
  - Profiles (profiles) - [OPT] description
  - Flows (flows) - [OPT] description
  - Templates (templates) - [OPT] description
- Campaigns : Additional Options (campaigns_settings) - [OPT] description
  - Fetch Campaign Recipients (fetch_campaign_recipients) - [OPT] description
- Catalogs : Additional Options (catalogs_settings) - [OPT] description
  - Fetch Catalog Categories (fetch_catalog_categories) - [OPT] description
- Events : Additional Options (events_settings) - [OPT] description
  - Fetch Events From Date (date_from) - [OPT] Date from which event data is downloaded. Either date in YYYY-MM-DD format
    or relative date string i.e. 5 days ago, 1 month ago, yesterday, etc. You can also set this as last run, which will
    fetch data from the last run of the component.
  - Fetch Events To Date (date_to) - [OPT] Date to which event data is downloaded. Either date in YYYY-MM-DD format or
    relative date string i.e. 5 days ago, 1 month ago, now, etc.
- Flows : Additional Options (flows_settings) - [OPT] description
  - Fetch Flow Actions (fetch_flows) - [OPT] description
- Profiles : Additional Options (profiles_settings) - [OPT] description
  - Fetch Profiles Mode (fetch_profiles_mode) - [OPT] description
  - List IDs (fetch_profiles_by_list) - [OPT] Comma separated list of list IDs
  - Segment IDs (fetch_profiles_by_segment) - [OPT] Comma separated list of segment IDs

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
    "flows_settings": {
      "fetch_flows": true
    },
    "profiles_settings": {
      "fetch_profiles_mode": "fetch_by_segment",
      "fetch_by_segment": "asdsadsdsa"
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