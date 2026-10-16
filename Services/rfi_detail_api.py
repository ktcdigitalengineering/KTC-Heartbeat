import requests


def get_rfi_detail(
    project_id,
    rfi_id,
    access_token
):
    """
    Retrieve one complete RFI record, including custom attribute values.
    """

    project_api_id = (
        project_id[2:]
        if project_id.startswith("b.")
        else project_id
    )

    url = (
        "https://developer.api.autodesk.com/"
        "construction/rfis/v3/"
        f"projects/{project_api_id}/rfis/{rfi_id}"
    )

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json"
    }

    response = requests.get(
        url,
        headers=headers,
        timeout=(15, 60)
    )

    if response.status_code != 200:
        raise Exception(
            f"Get RFI detail error "
            f"{response.status_code}: "
            f"{response.text}"
        )

    return response.json()