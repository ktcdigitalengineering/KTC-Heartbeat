import requests


def normalize_project_id(project_id):
    return project_id[2:] if project_id.startswith("b.") else project_id


def get_submittal_metadata(project_id, access_token):
    project_id = normalize_project_id(project_id)

    headers = {
        "Authorization": f"Bearer {access_token}"
    }

    url = (
        f"https://developer.api.autodesk.com/construction/submittals/v2/"
        f"projects/{project_id}/metadata"
    )

    response = requests.get(url, headers=headers)

    if response.status_code != 200:
        raise Exception(
            f"Submittal Metadata API error {response.status_code}: "
            f"{response.text}"
        )

    return response.json()


def build_lookup_map(items):
    lookup = {}

    for item in items:
        item_id = item.get("id")

        item_name = (
            item.get("value")
            or item.get("displayName")
            or item.get("name")
            or item.get("title")
            or item.get("key")
        )

        if item_id and item_name:
            lookup[str(item_id)] = item_name

    return lookup


def get_metadata_maps(project_id, access_token):
    metadata = get_submittal_metadata(project_id, access_token)

    item_type_map = build_lookup_map(
        metadata.get("itemTypes", [])
    )

    status_map = build_lookup_map(
        metadata.get("statuses", [])
    )

    response_map = build_lookup_map(
        metadata.get("responses", [])
    )

    return item_type_map, status_map, response_map