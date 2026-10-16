import requests


def get_location_map(project_id, access_token):
    headers = {
        "Authorization": f"Bearer {access_token}"
    }

    url = (
        f"https://developer.api.autodesk.com/construction/locations/v2/"
        f"projects/{project_id}/trees/default/nodes"
    )

    location_map = {}

    while url:
        response = requests.get(url, headers=headers)

        if response.status_code != 200:
            raise Exception(
                f"Locations API error {response.status_code}: {response.text}"
            )

        data = response.json()

        for item in data.get("results", []):
            location_id = item.get("id")
            location_name = item.get("name") or item.get("displayName")

            if location_id and location_name:
                location_map[location_id] = location_name

        pagination = data.get("pagination", {})
        url = pagination.get("nextUrl")

    return location_map