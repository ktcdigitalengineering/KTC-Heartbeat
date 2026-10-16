import requests
import json

def get_submittal_revisions(
    project_id,
    item_id,
    access_token
):
    """
    Retrieve revisions for one ACC submittal item.
    """

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json"
    }

    url = (
        "https://developer.api.autodesk.com/"
        "construction/submittals/v2/"
        f"projects/{project_id}/items/{item_id}/revisions"
    )

    response = requests.get(
        url,
        headers=headers,
        timeout=(10, 60)
    )

    if response.status_code != 200:
        raise Exception(
            f"Submittal revision API error "
            f"{response.status_code} for item {item_id}: "
            f"{response.text}"
        )

    data = response.json()

    print("=" * 80)
    print(f"Item ID: {item_id}")
    print(json.dumps(data, indent=4))
    print("=" * 80)

    if isinstance(data, list):
        revisions = data

    elif isinstance(data, dict):
        revisions = (
            data.get("results")
            or data.get("data")
            or data.get("revisions")
            or []
        )

    else:
        revisions = []

    if not isinstance(revisions, list):
        raise TypeError(
            f"Unexpected revision response for item {item_id}. "
            f"Received {type(revisions).__name__}"
        )

    return revisions