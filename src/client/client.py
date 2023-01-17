from klaviyo_api import KlaviyoAPI  # new sdk with incomplete functionality
from klaviyo_sdk import Client  # old sdk with all functionality

from typing import Generator, Callable

from openapi_client.exceptions import OpenApiException

BASE_URL = ""

MAX_DELAY = 60
MAX_RETRIES = 5

PAGE_COUNT_PAGINATION_PAGE_SIZE = 10
OFFSET_PAGINATION_PAGE_SIZE = 100


class KlaviyoClientException(Exception):
    pass


class KlaviyoClient:
    def __init__(self, api_token):
        self.client = KlaviyoAPI(api_token, max_delay=MAX_DELAY, max_retries=MAX_RETRIES)
        self.old_client = Client(api_token, max_delay=MAX_DELAY, max_retries=MAX_RETRIES)

    def get_metrics(self) -> Generator:
        return self._paginate_cursor_endpoint(self.client.Metrics.get_metrics)

    def get_catalog_items(self) -> Generator:
        return self._paginate_cursor_endpoint(self.client.Catalogs.get_catalog_items)

    def get_catalog_categories(self) -> Generator:
        return self._paginate_cursor_endpoint(self.client.Catalogs.get_catalog_categories)

    def get_events(self, from_timestamp_value: int, to_timestamp_value: int) -> Generator:
        request_filter = f"greater-or-equal(timestamp,{from_timestamp_value})," \
                         f"less-or-equal(timestamp,{to_timestamp_value})"
        return self._paginate_cursor_endpoint(self.client.Events.get_events, filter=request_filter)

    def get_lists(self) -> Generator:
        return self._paginate_cursor_endpoint(self.client.Lists.get_lists)

    def get_list_profiles(self, list_id: str) -> Generator:
        return self._paginate_cursor_endpoint(self.client.Lists.get_list_profiles, list_id=list_id)

    def get_profiles(self) -> Generator:
        return self._paginate_cursor_endpoint(self.client.Profiles.get_profiles)

    def get_segments(self) -> Generator:
        return self._paginate_cursor_endpoint(self.client.Segments.get_segments)

    def get_segment_profiles(self, segment_id: str) -> Generator:
        return self._paginate_cursor_endpoint(self.client.Segments.get_segment_profiles, segment_id=segment_id)

    # def get_flows(self) -> Generator:
    #     # todo pagination not working
    #     return self._paginate_number_endpoint(self.client.Flows.get_flows)

    def get_templates(self) -> Generator:
        # todo pagination not working for new client https://github.com/klaviyo/klaviyo-api-python/issues/6
        return self._paginate_page_count_endpoint(self.old_client.Templates.get_templates)

    def get_campaigns(self) -> Generator:
        return self._paginate_page_count_endpoint(self.old_client.Campaigns.get_campaigns)

    def get_campaign_recipients(self, campaign_id: str) -> Generator:
        return self._paginate_offset_endpoint(self.old_client.Campaigns.get_campaign_recipients,
                                              campaign_id=campaign_id)

    @staticmethod
    def _paginate_page_count_endpoint(endpoint_func: Callable, **kwargs) -> Generator:
        has_more = True
        page = 0
        while has_more:
            campaign_page = endpoint_func(page=page, count=PAGE_COUNT_PAGINATION_PAGE_SIZE, **kwargs)
            yield campaign_page.get("data")
            if campaign_page.get("total") <= (page + 1) * PAGE_COUNT_PAGINATION_PAGE_SIZE:
                has_more = False
            page += 1

    @staticmethod
    def _paginate_offset_endpoint(endpoint_func: Callable, **kwargs) -> Generator:
        current_page = endpoint_func(count=OFFSET_PAGINATION_PAGE_SIZE, **kwargs)
        yield current_page.get("data")

        has_more = "next_offset" in current_page
        while has_more:
            next_offset = current_page.get("next_offset")
            current_page = endpoint_func(count=OFFSET_PAGINATION_PAGE_SIZE, offset=next_offset, **kwargs)
            yield current_page.get("data")
            if "next_offset" not in current_page:
                has_more = False

    @staticmethod
    def _paginate_cursor_endpoint(endpoint_func: Callable, **kwargs) -> Generator:
        try:
            current_page = endpoint_func(**kwargs)
        except OpenApiException as api_exc:
            raise KlaviyoClientException(api_exc) from api_exc
        yield current_page.get("data")

        while next_page := current_page.get("links").get("next"):
            try:
                current_page = endpoint_func(**kwargs, page_cursor=next_page)
            except OpenApiException as api_exc:
                raise KlaviyoClientException(api_exc) from api_exc
            yield current_page.get("data")
