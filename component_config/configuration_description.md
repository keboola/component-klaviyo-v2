# Prerequisites
to get your API Token:

1. Log into your Klaviyo platform
2. Your profile name (bottom left)
3. Account
4. Settings
5. API Keys
6. Create Private API Key with Read-Only privileges

For more information follow [this guide on from Klaviyo](https://developers.klaviyo.com/en/docs/retrieve_api_credentials)

# Supported endpoints

- [Campaigns](https://developers.klaviyo.com/en/v1-2/reference/get-campaigns)
- [Catalogs](https://developers.klaviyo.com/en/reference/get_catalog_items)
- [Segments](https://developers.klaviyo.com/en/reference/get_segments)
- [Lists](https://developers.klaviyo.com/en/reference/get_lists)
- [Profiles](https://developers.klaviyo.com/en/reference/get_profiles)
- [Metrics](https://developers.klaviyo.com/en/reference/get_metrics)
- [Events](https://developers.klaviyo.com/en/reference/get_events)
- [Metric aggergates](https://developers.klaviyo.com/en/reference/query_metric_aggregates)

# Limitations

When fetching profiles the maximum amount of profiles is 25,000 due to fetching times. If you wish to fetch more, 
it is recommended to create multiple segments or lists and download them in multiple runs of the component.