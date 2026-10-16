import requests


def normalize_project_id(project_id):
    if project_id.startswith("b."):
        return project_id[2:]
    return project_id


def get_all_submittals(project_id, access_token):

    # Convert project ID if it starts with "b."
    submittal_project_id = normalize_project_id(project_id)

    headers = {
        "Authorization": f"Bearer {access_token}"
    }

    url = (
        f"https://developer.api.autodesk.com/construction/submittals/v2/"
        f"projects/{submittal_project_id}/items"
    )

    all_submittals = []

    while url:

        response = requests.get(url, headers=headers)

        if response.status_code != 200:
            raise Exception(
                f"Submittals API error {response.status_code}: {response.text}"
            )

        data = response.json()

        all_submittals.extend(data.get("results", []))

        pagination = data.get("pagination", {})
        url = pagination.get("nextUrl")

    return all_submittals