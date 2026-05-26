"""apps/core/pagination.py — project-wide pagination standard."""

from rest_framework.pagination import PageNumberPagination


class StandardPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100

    def get_paginated_response(self, data):  # type: ignore[override]
        response = super().get_paginated_response(data)
        response["X-Total-Count"] = self.page.paginator.count
        return response

    def get_paginated_response_schema(self, schema):  # type: ignore[override]
        return {
            "type": "object",
            "required": ["count", "results"],
            "properties": {
                "count": {"type": "integer"},
                "next": {"type": "string", "nullable": True},
                "previous": {"type": "string", "nullable": True},
                "results": schema,
            },
        }
