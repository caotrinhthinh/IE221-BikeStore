"""apps/core/schema.py — Custom OpenAPI schema hooks."""


def merge_auth_tags_hook(result, generator, request, public):
    """
    Postprocessing hook for drf-spectacular to merge the lowercase 'auth' tag
    (automatically generated for dj-rest-auth registration endpoints)
    into the uppercase 'Auth' tag.
    """
    for path in result.get("paths", {}).values():
        for operation in path.values():
            if "tags" in operation:
                operation["tags"] = [
                    "Auth" if tag == "auth" else tag for tag in operation["tags"]
                ]
    return result
