"""tests/core/test_swagger.py — OpenAPI schema and Swagger tags tests."""

import pytest
from drf_spectacular.generators import SchemaGenerator


@pytest.mark.django_db
class TestSwaggerSchema:
    def test_schema_generates_successfully(self):
        generator = SchemaGenerator()
        schema = generator.get_schema(request=None, public=True)
        assert isinstance(schema, dict)
        assert "paths" in schema
        assert "components" in schema

    def test_no_lowercase_auth_tag_exists_in_schema(self):
        generator = SchemaGenerator()
        schema = generator.get_schema(request=None, public=True)

        # Find all tags in paths
        all_tags = set()
        paths = schema.get("paths", {})
        for _path, methods in paths.items():
            for _method, info in methods.items():
                if "tags" in info:
                    for tag in info["tags"]:
                        all_tags.add(tag)

        # 'auth' (lowercase) must not be in tags
        assert "auth" not in all_tags
        # 'Auth' (uppercase) must be in tags (e.g. for /auth/login/ or /auth/registration/)
        assert "Auth" in all_tags

        # Verify that registration path is now tagged as 'Auth'
        registration_info = paths.get("/auth/registration/", {}).get("post", {})
        assert "tags" in registration_info
        assert "Auth" in registration_info["tags"]
