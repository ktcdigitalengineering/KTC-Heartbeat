import requests


def get_all_assets(project_id, access_token):
    headers = {
        "Authorization": f"Bearer {access_token}"
    }

    url = (
        f"https://developer.api.autodesk.com/construction/assets/v2/"
        f"projects/{project_id}/assets"
        f"?includeCustomAttributes=true&limit=100"
    )

    all_assets = []
    page = 1

    while url:
        print(f"Calling assets page {page}...")

        response = requests.get(url, headers=headers)

        if response.status_code != 200:
            raise Exception(f"Assets API error {response.status_code}: {response.text}")

        data = response.json()
        assets = data.get("results", [])

        all_assets.extend(assets)

        print(f"Assets in page: {len(assets)}")
        print(f"Total assets so far: {len(all_assets)}")

        pagination = data.get("pagination", {})
        url = pagination.get("nextUrl")

        page += 1

    return all_assets