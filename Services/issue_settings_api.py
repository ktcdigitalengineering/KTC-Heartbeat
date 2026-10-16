import requests

from Services.issues_api import (
    normalize_project_id,
    send_get_request
)


def get_paginated_issue_setting(
    project_id,
    access_token,
    endpoint,
    extra_params=None
):
    project_id = normalize_project_id(
        project_id
    )

    url = (
        "https://developer.api.autodesk.com/"
        "construction/issues/v1/"
        f"projects/{project_id}/{endpoint}"
    )

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json"
    }

    all_results = []
    offset = 0

    while True:
        params = {
            "limit": 100,
            "offset": offset
        }

        if extra_params:
            params.update(extra_params)

        response = send_get_request(
            url=url,
            headers=headers,
            params=params
        )

        data = response.json()
        results = data.get("results", [])

        if not isinstance(results, list):
            raise Exception(
                f"Unexpected response from {endpoint}."
            )

        all_results.extend(results)

        pagination = data.get("pagination", {})

        total_results = pagination.get(
            "totalResults",
            len(all_results)
        )

        page_limit = pagination.get(
            "limit",
            len(results)
        )

        if not results:
            break

        if len(all_results) >= int(total_results):
            break

        offset += int(page_limit)

    return all_results


def get_issue_types(
    project_id,
    access_token
):
    return get_paginated_issue_setting(
        project_id=project_id,
        access_token=access_token,
        endpoint="issue-types",
        extra_params={
            "include": "subtypes"
        }
    )


def get_root_cause_categories(
    project_id,
    access_token
):
    return get_paginated_issue_setting(
        project_id=project_id,
        access_token=access_token,
        endpoint="root-cause-categories",
        extra_params={
            "include": "rootcauses"
        }
    )


def get_issue_attribute_definitions(
    project_id,
    access_token
):
    return get_paginated_issue_setting(
        project_id=project_id,
        access_token=access_token,
        endpoint="issue-attribute-definitions"
    )


def build_issue_subtype_map(issue_types):
    subtype_map = {}

    for issue_type in issue_types:
        type_name = (
            issue_type.get("title")
            or issue_type.get("name")
            or issue_type.get("displayName")
            or ""
        )

        subtypes = (
            issue_type.get("subtypes")
            or []
        )

        for subtype in subtypes:
            subtype_id = subtype.get("id")

            subtype_name = (
                subtype.get("title")
                or subtype.get("name")
                or subtype.get("displayName")
                or subtype_id
            )

            if subtype_id:
                subtype_map[str(subtype_id)] = {
                    "type": type_name,
                    "subtype": subtype_name
                }

    return subtype_map


def build_root_cause_map(categories):
    root_cause_map = {}

    for category in categories:
        category_name = (
            category.get("title")
            or category.get("name")
            or category.get("displayName")
            or ""
        )

        root_causes = (
            category.get("rootCauses")
            or category.get("rootcauses")
            or []
        )

        for root_cause in root_causes:
            root_cause_id = root_cause.get("id")

            root_cause_name = (
                root_cause.get("title")
                or root_cause.get("name")
                or root_cause.get("displayName")
                or root_cause_id
            )

            if root_cause_id:
                root_cause_map[
                    str(root_cause_id)
                ] = {
                    "category": category_name,
                    "rootCause": root_cause_name
                }

    return root_cause_map


def build_attribute_definition_map(definitions):

    definition_map = {}

    for definition in definitions:

        definition_id = str(definition["id"])

        option_map = {}

        # <<< THIS IS THE IMPORTANT CHANGE >>>
        options = (
            definition.get("metadata", {})
                      .get("list", {})
                      .get("options", [])
        )

        for option in options:

            option_map[
                str(option["id"])
            ] = option["value"]

        definition_map[definition_id] = {
            "title": definition["title"],
            "type": definition["dataType"],
            "options": option_map
        }

    return definition_map