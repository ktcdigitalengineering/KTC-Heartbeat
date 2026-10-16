import requests


import requests


def get_category_map(project_id, access_token):

    headers = {
        "Authorization": f"Bearer {access_token}"
    }

    url = (
        f"https://developer.api.autodesk.com/construction/assets/v1/"
        f"projects/{project_id}/categories"
    )

    response = requests.get(url, headers=headers)

    if response.status_code != 200:
        raise Exception(
            f"Category API error {response.status_code}: {response.text}"
        )

    data = response.json()

    raw_category_map = {}

    for item in data.get("results", []):
        category_id = item.get("id")

        if not category_id:
            continue

        raw_category_map[category_id] = {
            "name": item.get("displayName") or item.get("name", ""),
            "parentId": item.get("parentId")
        }

    category_map = {}

    for category_id, category in raw_category_map.items():
        parent_id = category.get("parentId")

        if parent_id and parent_id in raw_category_map:
            category_map[category_id] = {
                "level1": raw_category_map[parent_id].get("name", ""),
                "level2": category.get("name", "")
            }
        else:
            category_map[category_id] = {
                "level1": category.get("name", ""),
                "level2": ""
            }

    return category_map


def get_category_path(category_id, category_map):
    """
    Returns the full category hierarchy.
    Example:
    Mechanical > Pump > Booster Pump
    """

    names = []

    current_id = category_id

    while current_id:

        category = category_map.get(current_id)

        if not category:
            break

        names.insert(0, category["name"])

        current_id = category.get("parentId")

    return " > ".join(names)