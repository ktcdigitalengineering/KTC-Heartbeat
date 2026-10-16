import pandas as pd
import json
from Services.reviews_api import flatten_review

# ==========================================================
# ASSET CSV EXPORT
# ==========================================================

def flatten_asset(asset, custom_attribute_map, status_map, category_map):
    row = {}

    for key, value in asset.items():
        if key == "customAttributes" and isinstance(value, dict):
            for custom_key, custom_value in value.items():
                column_name = custom_attribute_map.get(
                    custom_key,
                    f"custom_{custom_key}"
                )
                row[column_name] = custom_value

        elif key == "statusId":
            row["statusId"] = value
            row["status"] = status_map.get(value, value)

        elif key == "categoryId":
            row["categoryId"] = value

            category_info = category_map.get(value)

            if isinstance(category_info, dict):
                row["categoryLevel1"] = category_info.get("level1", "")
                row["categoryLevel2"] = category_info.get("level2", "")
            else:
                row["categoryLevel1"] = category_info or value
                row["categoryLevel2"] = ""

        elif isinstance(value, (dict, list)):
            row[key] = str(value)

        else:
            row[key] = value

    return row


def export_assets_to_csv(
    assets,
    custom_attribute_map,
    status_map,
    category_map,
    output_path
):
    flattened_assets = [
        flatten_asset(
            asset,
            custom_attribute_map,
            status_map,
            category_map
        )
        for asset in assets
    ]

    df = pd.DataFrame(flattened_assets)
    df.to_csv(output_path, index=False, encoding="utf-8-sig")

    print(f"Asset CSV exported to {output_path}")


def export_generic_to_csv(records, output_path):
    df = pd.json_normalize(records)
    df.to_csv(output_path, index=False, encoding="utf-8-sig")

    print(f"Generic CSV exported to {output_path}")


# ==========================================================
# SUBMITTAL CSV EXPORT
# ==========================================================

USER_ID_FIELDS = [
    "subcontractor",
    "manager",
    "submittedBy",
    "sentToReviewBy",
    "respondedBy",
    "createdBy",
    "updatedBy"
    
]

def flatten_submittal(
    submittal,
    item_type_map,
    package_map,
    spec_section_map,
    status_map,
    response_map,
    user_map
):
    row = {}

    for key, value in submittal.items():

        if key == "typeId":
            row["typeId"] = value
            row["itemType"] = item_type_map.get(str(value), value)

        elif key == "itemTypeId":
            row["itemTypeId"] = value
            row["itemType"] = item_type_map.get(str(value), value)

        elif key == "statusId":
            row["statusId"] = value
            row["status"] = status_map.get(str(value), value)

        elif key == "responseId":
            row["responseId"] = value
            row["response"] = response_map.get(str(value), value)

        elif key == "packageId":
            row["packageId"] = value
            row["package"] = package_map.get(str(value), value)

        elif key == "specSectionId":
            row["specSectionId"] = value
            row["specSection"] = spec_section_map.get(str(value), value)
        
        elif key in USER_ID_FIELDS:
            user_id = str(value).strip() if value else ""
            row[key] = value
            row[f"{key}Name"] = user_map.get(user_id, value)

        elif key == "ballInCourtUsers":
            row["ballInCourtUsers"] = str(value)

            if isinstance(value, list):
                user_ids = value
            elif isinstance(value, str):
                user_ids = (
                    value.replace("[", "")
                    .replace("]", "")
                    .replace("'", "")
                    .replace('"', "")
                    .split(",")
                )
            else:
                user_ids = []

            mapped_names = [
                user_map.get(str(user_id).strip(), str(user_id).strip())
                for user_id in user_ids
                if str(user_id).strip()
            ]

            row["ballInCourtUserNames"] = ", ".join(mapped_names)

        elif isinstance(value, (dict, list)):
            row[key] = str(value)

        else:
            row[key] = value

    return row


def export_submittals_to_csv(
    submittals,
    item_type_map,
    package_map,
    spec_section_map,
    status_map,
    response_map,
    user_map,
    output_file
):
    flattened_submittals = [
        flatten_submittal(
            submittal,
            item_type_map,
            package_map,
            spec_section_map,
            status_map,
            response_map,
            user_map
        )
        for submittal in submittals
    ]

    df = pd.DataFrame(flattened_submittals)
    df.to_csv(output_file, index=False, encoding="utf-8-sig")


    print(f"Submittal CSV exported to {output_file}")
   
def get_user_name(user_id, user_map):
    """
    Convert an APS user ID into a readable user name.
    """

    if not user_id:
        return ""

    user = user_map.get(user_id)

    if user is None:
        return user_id

    if isinstance(user, dict):
        return (
            user.get("name")
            or user.get("displayName")
            or user.get("email")
            or user_id
        )

    return user


def serialize_revision_value(value):
    """
    Convert lists and dictionaries into text suitable for CSV.
    """

    if value is None:
        return ""

    if isinstance(value, (dict, list)):
        return json.dumps(
            value,
            ensure_ascii=False,
            default=str
        )

    return value


def flatten_submittal_revision(
    submittal,
    revision,
    item_type_map,
    package_map,
    spec_section_map,
    status_map,
    response_map,
    user_map
):
    """
    Flatten one submittal revision into one CSV row.
    """

    row = {}

    # ======================================================
    # Parent submittal information
    # ======================================================

    row["submittalId"] = submittal.get("id", "")

    row["identifier"] = (
        submittal.get("identifier")
        or submittal.get("customIdentifier")
        or submittal.get("number")
        or ""
    )

    row["title"] = (
        submittal.get("title")
        or submittal.get("name")
        or ""
    )

    # ======================================================
    # Revision information
    # ======================================================

    row["revisionId"] = revision.get("id", "")

    row["revisionNumber"] = (
        revision.get("revision")
        or revision.get("revisionNumber")
        or revision.get("version")
        or revision.get("sequence")
        or ""
    )

    # ======================================================
    # Status
    # ======================================================

    status_id = (
        revision.get("statusId")
        or revision.get("stateId")
        or ""
    )

    row["statusId"] = status_id

    row["status"] = status_map.get(
        status_id,
        status_id
    )

    # ======================================================
    # Response
    # ======================================================

    response_id = revision.get("responseId", "")

    row["responseId"] = response_id

    row["response"] = response_map.get(
        response_id,
        response_id
    )

    row["responseComment"] = (
        revision.get("responseComment")
        or revision.get("comment")
        or ""
    )

    # ======================================================
    # Item type
    # ======================================================

    item_type_id = (
        revision.get("itemTypeId")
        or submittal.get("itemTypeId")
        or ""
    )

    row["itemTypeId"] = item_type_id

    row["itemType"] = item_type_map.get(
        item_type_id,
        item_type_id
    )

    # ======================================================
    # Package
    # ======================================================

    package_id = (
        revision.get("packageId")
        or submittal.get("packageId")
        or ""
    )

    row["packageId"] = package_id

    row["package"] = package_map.get(
        package_id,
        package_id
    )

    # ======================================================
    # Specification section
    # ======================================================

    spec_section_id = (
        revision.get("specSectionId")
        or submittal.get("specSectionId")
        or ""
    )

    row["specSectionId"] = spec_section_id

    row["specSection"] = spec_section_map.get(
        spec_section_id,
        spec_section_id
    )

    # ======================================================
    # User mappings
    # ======================================================

    created_by = revision.get("createdBy", "")
    updated_by = revision.get("updatedBy", "")

    submitted_by = (
        revision.get("submittedBy")
        or revision.get("submittedById")
        or ""
    )

    manager_id = (
        revision.get("managerId")
        or submittal.get("managerId")
        or ""
    )

    ball_in_court_id = (
        revision.get("ballInCourtId")
        or submittal.get("ballInCourtId")
        or ""
    )

    row["createdById"] = created_by
    row["createdBy"] = get_user_name(
        created_by,
        user_map
    )

    row["updatedById"] = updated_by
    row["updatedBy"] = get_user_name(
        updated_by,
        user_map
    )

    row["submittedById"] = submitted_by
    row["submittedBy"] = get_user_name(
        submitted_by,
        user_map
    )

    row["managerId"] = manager_id
    row["manager"] = get_user_name(
        manager_id,
        user_map
    )

    row["ballInCourtId"] = ball_in_court_id
    row["ballInCourt"] = get_user_name(
        ball_in_court_id,
        user_map
    )

    # ======================================================
    # Dates
    # ======================================================

    row["createdAt"] = revision.get("createdAt", "")
    row["updatedAt"] = revision.get("updatedAt", "")

    row["submittedAt"] = (
        revision.get("submittedAt")
        or revision.get("submissionDate")
        or ""
    )

    row["dueDate"] = (
        revision.get("dueDate")
        or revision.get("requiredDate")
        or ""
    )

    row["respondedAt"] = (
        revision.get("respondedAt")
        or revision.get("completedAt")
        or revision.get("closedAt")
        or ""
    )

    # ======================================================
    # Preserve other fields returned by APS
    # ======================================================

    processed_fields = {
        "id",
        "revision",
        "revisionNumber",
        "version",
        "sequence",
        "statusId",
        "stateId",
        "responseId",
        "responseComment",
        "comment",
        "itemTypeId",
        "packageId",
        "specSectionId",
        "createdBy",
        "updatedBy",
        "submittedBy",
        "submittedById",
        "managerId",
        "ballInCourtId",
        "createdAt",
        "updatedAt",
        "submittedAt",
        "submissionDate",
        "dueDate",
        "requiredDate",
        "respondedAt",
        "completedAt",
        "closedAt"
    }

    for key, value in revision.items():
        if key not in processed_fields:
            row[f"revision_{key}"] = (
                serialize_revision_value(value)
            )

    return row


def export_submittal_revisions_to_csv(
    revision_rows,
    output_file
):
    """
    Export all flattened revision rows into a separate CSV.
    """

    df = pd.DataFrame(revision_rows)

    df.to_csv(
        output_file,
        index=False,
        encoding="utf-8-sig"
    )

    print(
        f"Submittal revision CSV exported to {output_file}"
    )

    print(
        f"Total submittal revision rows: {len(df)}"
    )

# ==========================================================
# RFI CSV EXPORT
# ==========================================================

RFI_USER_ID_FIELDS = [
    "createdBy",
    "updatedBy",
    "submittedBy",
    "assignedTo",
    "manager",
    "managerId",
    "respondedBy",
    "closedBy",
    "officialResponseBy"
]

RFI_USER_LIST_FIELDS = [
    "reviewers",
    "watchers",
    "coReviewers",
    "assignedUsers",
    "remainingReviewers"
]


def map_rfi_user_value(value, user_map):
    """
    Convert an RFI user value into readable names.

    The RFI response may provide:
    - one user ID string;
    - a user object;
    - a list of user IDs or user objects.
    """
    if value is None:
        return ""

    if isinstance(value, list):
        names = [
            map_rfi_user_value(item, user_map)
            for item in value
        ]

        return ", ".join(
            name for name in names if name
        )

    if isinstance(value, dict):
        user_id = (
            value.get("id")
            or value.get("userId")
            or value.get("autodeskId")
            or value.get("uid")
            or ""
        )

        direct_name = (
            value.get("name")
            or value.get("displayName")
            or value.get("email")
        )

        if user_id:
            return user_map.get(
                str(user_id).strip(),
                direct_name or str(user_id)
            )

        return direct_name or json.dumps(
            value,
            ensure_ascii=False,
            default=str
        )

    user_id = str(value).strip()

    if not user_id:
        return ""

    return user_map.get(user_id, user_id)


def serialize_rfi_value(value):
    """
    Preserve nested RFI fields as JSON text in the CSV.
    """
    if value is None:
        return ""

    if isinstance(value, (dict, list)):
        return json.dumps(
            value,
            ensure_ascii=False,
            default=str
        )

    return value

def get_rfi_custom_attribute_name(
    attribute_id,
    custom_attribute_map
):
    attribute_key = str(attribute_id).strip()

    definition = custom_attribute_map.get(
        attribute_key,
        {}
    )

    return (
        definition.get("name")
        or definition.get("displayName")
        or f"custom_{attribute_key}"
    )

def decode_rfi_custom_attribute_values(
    attribute_value,
    attribute_id,
    custom_attribute_map
):
    definition = custom_attribute_map.get(
        str(attribute_id),
        {}
    )

    option_map = definition.get("optionMap", {})

    if isinstance(attribute_value, list):
        decoded_values = [
            option_map.get(str(value), value)
            for value in attribute_value
        ]

        return ", ".join(
            str(value)
            for value in decoded_values
        )

    return option_map.get(
        str(attribute_value),
        attribute_value
    )


def flatten_rfi(rfi, user_map, custom_attribute_map):
    """
    Flatten one RFI into one CSV row.

    Known user fields are supplemented with readable name columns.
    All other fields returned by APS are retained.
    """
    row = {}
    
    
    for key, value in rfi.items():
        if key in RFI_USER_ID_FIELDS:
            row[key] = serialize_rfi_value(value)
            row[f"{key}Name"] = map_rfi_user_value(
                value,
                user_map
            )

        elif key in RFI_USER_LIST_FIELDS:
            row[key] = serialize_rfi_value(value)
            row[f"{key}Names"] = map_rfi_user_value(
                value,
                user_map
            )

        elif key == "customAttributes":
            row[key] = serialize_rfi_value(value)

            # Also expose each custom attribute in its own column
            # where the response is a dictionary.
            if isinstance(value, dict):
                for attribute_key, attribute_value in value.items():

                    column_name = get_rfi_custom_attribute_name(
                    attribute_key,
                    custom_attribute_map
                    )

                    row[column_name] = serialize_rfi_value(
                        attribute_value
                    )

            # Some RFI responses return custom attributes as a list.
            elif isinstance(value, list):
                for attribute in value:
                    if not isinstance(attribute, dict):
                        continue

                    attribute_id = (
                        attribute.get("id")
                        or attribute.get("attributeId")
                        or attribute.get("name")
                    )

                    attribute_value = (
                        attribute.get("value")
                        if "value" in attribute
                        else attribute.get("values")
                    )

                    if attribute_id:
                        column_name = get_rfi_custom_attribute_name(
                            attribute_id,
                            custom_attribute_map
                        )

                        decoded_value = decode_rfi_custom_attribute_values(
                            attribute_value,
                            attribute_id,
                            custom_attribute_map
                        )

                        row[column_name] = serialize_rfi_value(
                            decoded_value
                        )

        elif isinstance(value, (dict, list)):
            row[key] = serialize_rfi_value(value)

        else:
            row[key] = value

    return row


def export_rfis_to_csv(
    rfis,
    user_map,
    custom_attribute_map,
    output_file
):
    flattened_rfis = [
        flatten_rfi(
            rfi,
            user_map,
            custom_attribute_map
        
        )
        for rfi in rfis
    ]

    df = pd.DataFrame(flattened_rfis)

    df.to_csv(
        output_file,
        index=False,
        encoding="utf-8-sig"
    )

    print(f"RFI CSV exported to {output_file}")
    print(f"Total RFI rows: {len(df)}")


# ==========================================================
# ISSUE CSV EXPORT
# ==========================================================

ISSUE_USER_FIELDS = [
    "createdBy",
    "updatedBy",
    "closedBy",
    "openedBy",
    "assignedToId"
]


def serialize_issue_value(value):
    if value is None:
        return ""

    if isinstance(value, (dict, list)):
        return json.dumps(
            value,
            ensure_ascii=False,
            default=str
        )

    return value


def map_issue_user_value(
    value,
    user_map
):
    if value is None:
        return "", ""

    if isinstance(value, dict):
        user_id = (
            value.get("id")
            or value.get("autodeskId")
            or value.get("userId")
            or ""
        )

        embedded_name = (
            value.get("name")
            or value.get("displayName")
            or value.get("email")
        )

        user_name = (
            embedded_name
            or user_map.get(
                str(user_id).strip(),
                user_id
            )
        )

        return user_id, user_name

    user_id = str(value).strip()

    return (
        user_id,
        user_map.get(user_id, user_id)
    )

def decode_issue_attribute_value(
    raw_value,
    option_map
):
    """
    Convert a custom attribute value into readable text.

    Handles:
    - direct text or numbers
    - one dropdown option GUID
    - multiple dropdown option GUIDs
    - values wrapped inside dictionaries
    """

    if raw_value is None:
        return ""

    if isinstance(raw_value, list):
        decoded_values = []

        for item in raw_value:
            decoded = decode_issue_attribute_value(
                item,
                option_map
            )

            if decoded not in ["", None]:
                decoded_values.append(
                    str(decoded)
                )

        return ", ".join(decoded_values)

    if isinstance(raw_value, dict):
        embedded_value = (
            raw_value.get("value")
            or raw_value.get("id")
            or raw_value.get("valueId")
            or raw_value.get("key")
        )

        embedded_name = (
            raw_value.get("displayValue")
            or raw_value.get("displayName")
            or raw_value.get("title")
            or raw_value.get("name")
            or raw_value.get("label")
        )

        if embedded_name:
            return embedded_name

        return decode_issue_attribute_value(
            embedded_value,
            option_map
        )

    lookup_key = str(raw_value).strip()

    return option_map.get(
        lookup_key,
        raw_value
    )


def flatten_issue_custom_attributes(
    custom_attributes,
    attribute_definition_map
):
    row = {}

    for attribute in custom_attributes or []:

        if not isinstance(attribute, dict):
            continue

        definition_id = (
            attribute.get("attributeDefinitionId")
            or attribute.get("id")
        )

        if not definition_id:
            continue

        definition = attribute_definition_map.get(
            str(definition_id),
            {}
        )

        title = (
            definition.get("title")
            or attribute.get("title")
            or f"custom_{definition_id}"
        )

        option_map = definition.get(
            "options",
            {}
        )

        value = attribute.get("value")

        if value is None:
            row[title] = ""

        elif isinstance(value, list):

            row[title] = ", ".join(
                option_map.get(str(v), str(v))
                for v in value
            )

        else:

            row[title] = option_map.get(
                str(value),
                value
            )

    return row

def flatten_issue(
    issue,
    subtype_map,
    root_cause_map,
    attribute_definition_map,
    user_map,
    admin_lookup,
):
    row = {}

    assigned_to_type = str(
        issue.get("assignedToType") or ""
    ).strip().lower()

    for key, value in issue.items():

        if key == "issueSubtypeId":
            row["issueSubtypeId"] = value

            subtype_info = subtype_map.get(
                str(value),
                {},
            )

            row["issueType"] = subtype_info.get(
                "type",
                "",
            )

            row["issueSubtype"] = subtype_info.get(
                "subtype",
                value,
            )

        elif key == "rootCauseId":
            row["rootCauseId"] = value

            root_cause_info = root_cause_map.get(
                str(value),
                {},
            )

            row["rootCauseCategory"] = (
                root_cause_info.get(
                    "category",
                    "",
                )
            )

            row["rootCause"] = (
                root_cause_info.get(
                    "rootCause",
                    value,
                )
            )

        elif key == "customAttributes":
            row.update(
                flatten_issue_custom_attributes(
                    value,
                    attribute_definition_map,
                )
            )

        elif key == "assignedTo":
            assigned_id = (
                str(value).strip()
                if value is not None
                else ""
            )

            assigned_name = (
                admin_lookup.resolve_assignee(
                    assigned_id,
                    assigned_to_type,
                )
            )

            row["assignedTo"] = assigned_id
            row["assignedToName"] = assigned_name

        elif key == "assignedToType":
            row["assignedToType"] = value

        elif key in ISSUE_USER_FIELDS:
            user_id, user_name = map_issue_user_value(
                value,
                user_map,
            )

            row[key] = user_id
            row[f"{key}Name"] = user_name

        elif key == "watchers":
            row["watchers"] = serialize_issue_value(
                value
            )

            watcher_names = []

            for watcher in value or []:
                _, watcher_name = map_issue_user_value(
                    watcher,
                    user_map,
                )

                if watcher_name:
                    watcher_names.append(
                        str(watcher_name)
                    )

            row["watcherNames"] = ", ".join(
                watcher_names
            )

        elif key == "watcherObjects":
            watcher_object_names = []

            for watcher in value or []:
                if not isinstance(watcher, dict):
                    continue

                watcher_id = str(
                    watcher.get("id") or ""
                ).strip()

                watcher_type = str(
                    watcher.get("type") or ""
                ).strip().lower()

                watcher_name = (
                    admin_lookup.resolve_assignee(
                        watcher_id,
                        watcher_type,
                    )
                )

                if watcher_name:
                    watcher_object_names.append(
                        f"{watcher_name} "
                        f"({watcher_type})"
                    )

            row["watcherObjects"] = (
                serialize_issue_value(value)
            )

            row["watcherObjectNames"] = ", ".join(
                watcher_object_names
            )

        elif isinstance(value, (dict, list)):
            row[key] = serialize_issue_value(value)

        else:
            row[key] = value

    return row

# ==========================================================
# Review CSV EXPORT
# ==========================================================


def export_issues_to_csv(
    issues,
    subtype_map,
    root_cause_map,
    attribute_definition_map,
    user_map,
    admin_lookup,
    output_file
):
    flattened_issues = [
        flatten_issue(
            issue,
            subtype_map,
            root_cause_map,
            attribute_definition_map,
            user_map,
            admin_lookup,
        )
        for issue in issues
    ]

    df = pd.DataFrame(flattened_issues)

    df.to_csv(
        output_file,
        index=False,
        encoding="utf-8-sig"
    )

    print(
        f"Issue CSV exported to {output_file}"
    )



def export_reviews_to_csv(
    reviews,
    output_file,
    admin_lookup=None,
):
    flattened_reviews = [
        flatten_review(
            review=review,
            admin_lookup=admin_lookup,
        )
        for review in reviews
    ]

    dataframe = pd.DataFrame(flattened_reviews)

    dataframe.to_csv(
        output_file,
        index=False,
        encoding="utf-8-sig",
    )

    print(
        f"Review CSV exported to: {output_file}"
    )
    print(
        f"Review rows exported: {len(dataframe)}"
    )