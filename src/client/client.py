import json
import swagger_client
from klaviyo_api import KlaviyoAPI  # new sdk with incomplete functionality
from klaviyo_sdk import Client  # old sdk with all functionality
from typing import Iterator, Callable, Dict, List
from openapi_client.exceptions import OpenApiException

BASE_URL = ""

MAX_DELAY = 60
MAX_RETRIES = 5

PAGE_COUNT_PAGINATION_PAGE_SIZE = 10
OFFSET_PAGINATION_PAGE_SIZE = 100


class KlaviyoClientException(Exception):
    pass


class KlaviyoClient:
    def __init__(self, api_token: str):
        self.client = KlaviyoAPI(api_token, max_delay=MAX_DELAY, max_retries=MAX_RETRIES)
        self.old_client = Client(api_token, max_delay=MAX_DELAY, max_retries=MAX_RETRIES)

    def get_metrics(self) -> Iterator[List[Dict]]:
        return self._paginate_cursor_endpoint(self.client.Metrics.get_metrics)

    def get_catalog_items(self) -> Iterator[List[Dict]]:
        return self._paginate_cursor_endpoint(self.client.Catalogs.get_catalog_items)

    def get_catalog_categories(self) -> Iterator[List[Dict]]:
        return self._paginate_cursor_endpoint(self.client.Catalogs.get_catalog_categories)

    def get_events(self, from_timestamp_value: int, to_timestamp_value: int) -> Iterator[List[Dict]]:
        request_filter = f"greater-or-equal(timestamp,{from_timestamp_value})," \
                         f"less-or-equal(timestamp,{to_timestamp_value})"
        return self._paginate_cursor_endpoint(self.client.Events.get_events, filter=request_filter)

    def get_lists(self) -> Iterator[List[Dict]]:
        return self._paginate_cursor_endpoint(self.client.Lists.get_lists)

    def get_list(self, list_id: str) -> Dict:
        try:
            return self.client.Lists.get_list(list_id)
        except OpenApiException as api_exc:
            error_message = self._process_error(api_exc)
            raise KlaviyoClientException(error_message) from api_exc

    def get_list_ids(self) -> List[Dict]:
        all_list_ids = []
        for page in self._paginate_cursor_endpoint(self.client.Lists.get_lists):
            all_list_ids.extend({"id": row.get("id"), "name": row.get("attributes").get("name")} for row in page)
        return all_list_ids

    def get_segment_ids(self) -> List[Dict]:
        all_segment_ids = []
        for page in self._paginate_cursor_endpoint(self.client.Segments.get_segments):
            all_segment_ids.extend({"id": row.get("id"), "name": row.get("attributes").get("name")} for row in page)
        return all_segment_ids

    def get_list_profiles(self, list_id: str) -> Iterator[List[Dict]]:
        return self._paginate_cursor_endpoint(self.client.Lists.get_list_profiles, list_id=list_id)

    def get_profiles(self) -> Iterator[List[Dict]]:
        return self._paginate_cursor_endpoint(self.client.Profiles.get_profiles)

    def get_segments(self) -> Iterator[List[Dict]]:
        return self._paginate_cursor_endpoint(self.client.Segments.get_segments)

    def get_segment(self, segment_id):
        try:
            return self.client.Segments.get_segment(segment_id)
        except OpenApiException as api_exc:
            error_message = self._process_error(api_exc)
            raise KlaviyoClientException(error_message) from api_exc

    def get_segment_profiles(self, segment_id: str) -> Iterator[List[Dict]]:
        return self._paginate_cursor_endpoint(self.client.Segments.get_segment_profiles, segment_id=segment_id)

    def get_flows(self) -> Iterator[List[Dict]]:
        return self._paginate_cursor_endpoint(self.client.Flows.get_flows)

    def get_templates(self) -> Iterator[List[Dict]]:
        return self._paginate_cursor_endpoint(self.client.Templates.get_templates)

    def get_campaigns(self) -> Iterator[List[Dict]]:
        return self._paginate_page_count_endpoint(self.old_client.Campaigns.get_campaigns)

    def get_campaign_recipients(self, campaign_id: str) -> Iterator[List[Dict]]:
        return self._paginate_offset_endpoint(self.old_client.Campaigns.get_campaign_recipients,
                                              campaign_id=campaign_id)

    def _paginate_page_count_endpoint(self, endpoint_func: Callable, **kwargs) -> Iterator[List[Dict]]:
        has_more = True
        page = 0
        while has_more:
            try:
                campaign_page = endpoint_func(page=page, count=PAGE_COUNT_PAGINATION_PAGE_SIZE, **kwargs)
            except swagger_client.rest.ApiException as api_exc:
                error_message = self._process_error(api_exc)
                raise KlaviyoClientException(error_message) from api_exc
            yield campaign_page.get("data")
            if campaign_page.get("total") <= (page + 1) * PAGE_COUNT_PAGINATION_PAGE_SIZE:
                has_more = False
            page += 1

    def _paginate_offset_endpoint(self, endpoint_func: Callable, **kwargs) -> Iterator[List[Dict]]:
        try:
            current_page = endpoint_func(count=OFFSET_PAGINATION_PAGE_SIZE, **kwargs)
        except swagger_client.rest.ApiException as api_exc:
            error_message = self._process_error(api_exc)
            raise KlaviyoClientException(error_message) from api_exc
        yield current_page.get("data")

        has_more = "next_offset" in current_page
        while has_more:
            next_offset = current_page.get("next_offset")
            try:
                current_page = endpoint_func(count=OFFSET_PAGINATION_PAGE_SIZE, offset=next_offset, **kwargs)
            except swagger_client.rest.ApiException as api_exc:
                error_message = self._process_error(api_exc)
                raise KlaviyoClientException(error_message) from api_exc
            yield current_page.get("data")
            if "next_offset" not in current_page:
                has_more = False

    def _paginate_cursor_endpoint(self, endpoint_func: Callable, **kwargs) -> Iterator[List[Dict]]:
        try:
            current_page = endpoint_func(**kwargs)
        except OpenApiException as api_exc:
            error_message = self._process_error(api_exc)
            raise KlaviyoClientException(error_message) from api_exc
        yield current_page.get("data")

        while next_page := current_page.get("links").get("next"):
            try:
                current_page = endpoint_func(**kwargs, page_cursor=next_page)
            except OpenApiException as api_exc:
                error_message = self._process_error(api_exc)
                raise KlaviyoClientException(error_message) from api_exc
            yield current_page.get("data")

    def _process_error(self, api_exc: Exception) -> str:
        try:
            error_data = json.loads(api_exc.body)
        except json.JSONDecodeError as exc:
            raise KlaviyoClientException(f"Error Occurred. Failed to decode error : {api_exc.body}") from exc
        if len(error_data.get('errors', [])) > 0:
            error = error_data.get('errors')[0]
            error_message = self._generate_error_message_v2_client(error)
        elif "message" in error_data and "status" in error_data:
            error_message = self._generate_error_message_v1_client(error_data)
        else:
            error_message = error_data
        return error_message

    @staticmethod
    def _generate_error_message_v2_client(error_data: Dict) -> str:
        error_detail = f"{error_data.get('title')} {error_data.get('detail')}"
        if error_data.get('status') == 401:
            error_name = f"Not Authorized Error ({error_data.get('status')})"
        elif error_data.get('status') == 403:
            error_name = f"Forbidden Error ({error_data.get('status')})"
        elif error_data.get('status') == 404:
            error_name = f"Not Found Error ({error_data.get('status')})"
        else:
            error_name = f"{error_data.get('code')} ({error_data.get('status')})"
        return f"{error_name} : {error_detail}"

    @staticmethod
    def _generate_error_message_v1_client(error_data: Dict) -> str:
        error_detail = error_data.get('message')
        if error_data.get('status') == 401:
            error_name = f"Not Authorized Error ({error_data.get('status')})"
        elif error_data.get('status') == 403:
            error_name = f"Forbidden Error ({error_data.get('status')})"
        elif error_data.get('status') == 404:
            error_name = f"Not Found Error ({error_data.get('status')})"
        else:
            error_name = f"({error_data.get('status')})"
        return f"{error_name} : {error_detail}"

    def get_missing_scopes(self) -> List[str]:
        missing_scopes = []

        # test campaigns endpoint
        try:
            self.old_client.Campaigns.get_campaigns()
        except swagger_client.rest.ApiException:
            missing_scopes += ["campaigns"]

        # test catalogs endpoint
        try:
            self.client.Catalogs.get_catalog_items()
        except OpenApiException:
            missing_scopes += ["catalogs"]

        # test events endpoint
        try:
            self.client.Events.get_events()
        except OpenApiException:
            missing_scopes += ["catalogs"]

        # test lists endpoint
        try:
            self.client.Lists.get_lists()
        except OpenApiException:
            missing_scopes += ["lists"]

        # test metrics endpoint
        try:
            self.client.Metrics.get_metrics()
        except OpenApiException:
            missing_scopes += ["metrics"]

        # test profiles endpoint
        try:
            self.client.Profiles.get_profiles()
        except OpenApiException:
            missing_scopes += ["profiles"]

        # test segments endpoint
        try:
            self.client.Segments.get_segments()
        except OpenApiException:
            missing_scopes += ["segment"]

        return missing_scopes
