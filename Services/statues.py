import requests


def get_status_map(project_id, access_token):
    headers = {
        "Authorization": f"Bearer {access_token}"
    }

    url = (
        f"https://developer.api.autodesk.com/construction/assets/v1/"
        f"projects/{project_id}/asset-statuses"
    )

    response = requests.get(url, headers=headers)

    if response.status_code != 200:
        raise Exception(
            f"Status API error {response.status_code}: {response.text}"
        )

    data = response.json()

    status_map = {}

    for item in data.get("results", []):
        status_id = item.get("id")
        status_name = (
            item.get("displayName")
            or item.get("name")
            or item.get("label")
        )

        if status_id and status_name:
            status_map[status_id] = status_name

    print("Status map:")
    print(status_map)

    return status_map