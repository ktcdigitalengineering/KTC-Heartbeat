import requests

def get_custom_attribute_map(project_id, access_token):
    headers = {
        "Authorization": f"Bearer {access_token}"
    }

    url = (
        f"https://developer.api.autodesk.com/construction/assets/v1/"
        f"projects/{project_id}/custom-attributes"
    )

    response = requests.get(url, headers=headers)

    if response.status_code != 200:
        raise Exception(
            f"Custom Attributes API error {response.status_code}: {response.text}"
        )

    data = response.json()

    custom_attribute_map = {}

    for item in data.get("results", []):

        attribute_key = item.get("name")          # ca1
        attribute_label = item.get("displayName") # 1. TAM DRILL START

        if attribute_key and attribute_label:
            custom_attribute_map[attribute_key] = attribute_label

    return custom_attribute_map