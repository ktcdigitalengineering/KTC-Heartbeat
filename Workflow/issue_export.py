import json

from Services.issues_api import (
    get_all_issues
)
from Services.issue_settings_api import (
    get_issue_types,
    get_root_cause_categories,
    get_issue_attribute_definitions,
    build_issue_subtype_map,
    build_root_cause_map,
    build_attribute_definition_map
)
from Services.project_users_api import (
    get_project_users
)

from Modules.admin_lookup import (
    AdminLookup
)
from Modules.csv_export import (
    export_issues_to_csv
)
from Modules.upload import (
    upload_csv_to_acc
)
from Modules.logger import (
    write_log
)


def export_issues(
    project,
    access_token
):
    project_name = project["name"]
    project_id = project["project_id"]

    output_file = (
        project["output_files"]["issues"]
    )

    target_folder_id = (
        project["target_folders"]["issues"]
    )

    data_connector_folder = (
        project["output_files"]["data_connector"]
    )

    write_log(
        f"===== Starting Issues Export : "
        f"{project_name} ====="
    )

    write_log("Loading Admin lookup...")

    try:
        admin_lookup = AdminLookup(
            data_connector_folder=data_connector_folder,
            project_id=project_id,
        )

    except Exception as error:
        write_log(
            f"Admin lookup failed: {error}"
        )

        raise

    write_log("Reading Issue Types...")

    try:
        issue_types = get_issue_types(
            project_id,
            access_token
        )

        subtype_map = (
            build_issue_subtype_map(
                issue_types
            )
        )

    except Exception as error:
        write_log(
            f"Issue type lookup failed: {error}"
        )

        subtype_map = {}

    write_log("Reading Issue Root Causes...")

    try:
        root_cause_categories = (
            get_root_cause_categories(
                project_id,
                access_token
            )
        )

        root_cause_map = (
            build_root_cause_map(
                root_cause_categories
            )
        )

    except Exception as error:
        write_log(
            f"Root cause lookup failed: {error}"
        )

        root_cause_map = {}

    write_log(
        "Reading Issue Custom Attribute Definitions..."
    )

    try:
        definitions = (
            get_issue_attribute_definitions(
                project_id,
                access_token
            )
        )

        attribute_definition_map = (
            build_attribute_definition_map(
                definitions
            )
        )

    except Exception as error:
        write_log(
            f"Attribute definition lookup failed: "
            f"{error}"
        )

        attribute_definition_map = {}

    write_log("Reading Project Users...")

    try:
        user_map = get_project_users(
            project_id,
            access_token
        )

    except Exception as error:
        write_log(
            f"Project users lookup failed: {error}"
        )

        user_map = {}

    write_log("Reading Issues...")

    issues = get_all_issues(
        project_id,
        access_token
    )

    write_log(
        f"{project_name}: "
        f"Issues extracted = {len(issues)}"
    )

    export_issues_to_csv(
        issues=issues,
        subtype_map=subtype_map,
        root_cause_map=root_cause_map,
        attribute_definition_map=attribute_definition_map,
        user_map=user_map,
        admin_lookup=admin_lookup,
        output_file=output_file,
    )

    write_log(
        "Uploading Issues CSV to ACC..."
    )

    
    upload_csv_to_acc(
        project_id,
        target_folder_id,
        output_file,
        access_token
    )
    

    write_log(
        f"===== Issues Export Completed : "
        f"{project_name} ====="
    )