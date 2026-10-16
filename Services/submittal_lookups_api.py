import requests


def normalize_project_id(project_id):
    return project_id[2:] if project_id.startswith("b.") else project_id


def get_lookup_map(project_id, access_token, endpoint, name_fields):
    project_id = normalize_project_id(project_id)

    headers = {
        "Authorization": f"Bearer {access_token}"
    }

    url = (
        f"https://developer.api.autodesk.com/construction/submittals/v2/"
        f"projects/{project_id}/{endpoint}"
    )

    lookup_map = {}

    while url:
        print(f"Calling lookup URL: {url}")

        response = requests.get(url, headers=headers)

        if response.status_code != 200:
            raise Exception(
                f"Submittal lookup API error {response.status_code}: "
                f"{response.text}"
            )

        data = response.json()

        items = data if isinstance(data, list) else data.get("results", [])

        for item in items:
            item_id = item.get("id")

            item_name = None
            for field in name_fields:
                if item.get(field):
                    item_name = item.get(field)
                    break

            if item_id and item_name:
                lookup_map[str(item_id)] = item_name

        pagination = data.get("pagination", {}) if isinstance(data, dict) else {}
        url = pagination.get("nextUrl")

    return lookup_map


def get_package_map(project_id, access_token):
    return get_lookup_map(
        project_id,
        access_token,
        "packages",
        ["displayName", "name", "title", "value"]
    )


def get_spec_section_map(project_id, access_token):
    return get_lookup_map(
        project_id,
        access_token,
        "specSections",
        ["displayName", "name", "title", "number", "value"]
    )