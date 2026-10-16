import requests


def normalize_project_id(project_id):
    return project_id[2:] if project_id.startswith("b.") else project_id


def get_rfi_custom_attribute_map(project_id, access_token):
    """
    Retrieve RFI custom attribute definitions and build lookup maps.

    Returns:
        attribute_map:
            {
                attribute_id: {
                    "name": attribute_name,
                    "type": attribute_type,
                    "multipleChoice": True/False,
                    "optionMap": {
                        option_id: option_name
                    }
                }
            }
    """

    project_id = normalize_project_id(project_id)

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json"
    }

    url = (
        "https://developer.api.autodesk.com/"
        "construction/rfis/v3/"
        f"projects/{project_id}/attributes"
    )

    attribute_map = {}

    while url:
        response = requests.get(
            url,
            headers=headers,
            timeout=(15, 60)
        )

        if response.status_code != 200:
            raise Exception(
                f"RFI custom attributes API error "
                f"{response.status_code}: {response.text}"
            )

        data = response.json()

        if isinstance(data, list):
            attributes = data
        else:
            attributes = (
                data.get("results")
                or data.get("data")
                or data.get("attributes")
                or []
            )

        for attribute in attributes:
            attribute_id = attribute.get("id")

            if not attribute_id:
                continue

            attribute_name = (
                attribute.get("name")
                or attribute.get("displayName")
                or f"custom_{attribute_id}"
            )

            option_map = {}

            possible_values = (
                attribute.get("possibleValues")
                or attribute.get("options")
                or []
            )

            for option in possible_values:
                option_id = option.get("id")

                option_name = (
                    option.get("name")
                    or option.get("displayName")
                    or option.get("value")
                )

                if option_id and option_name is not None:
                    option_map[str(option_id)] = option_name

            attribute_map[str(attribute_id)] = {
                "name": attribute_name,
                "type": attribute.get("type", ""),
                "multipleChoice": attribute.get(
                    "multipleChoice",
                    False
                ),
                "optionMap": option_map
            }

        pagination = (
            data.get("pagination", {})
            if isinstance(data, dict)
            else {}
        )

        url = pagination.get("nextUrl")

    print(
        f"RFI custom attributes mapped: "
        f"{len(attribute_map)}"
    )

    return attribute_map