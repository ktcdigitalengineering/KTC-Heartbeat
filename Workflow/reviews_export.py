import os

from Modules.admin_lookup import AdminLookup
from Modules.csv_export import export_reviews_to_csv
from Modules.logger import write_log
from Modules.upload import upload_csv_to_acc

from Services.reviews_api import (
    enrich_reviews_with_workflows,
    get_all_reviews,
)


def export_reviews(
    project,
    access_token,
):
    """
    Exports Autodesk Forma Reviews for one project.

    Workflow:
    1. Validate configuration
    2. Load AdminLookup where available
    3. Retrieve all reviews
    4. Retrieve the workflow snapshot for each review
    5. Export the flattened review data to CSV
    6. Upload the CSV to ACC when a target folder is configured
    """

    project_name = project["name"]
    project_id = project["project_id"]

    output_file = (
        project
        .get("output_files", {})
        .get("reviews")
    )

    if not output_file:
        raise ValueError(
            f"{project_name}: Reviews output file "
            "is not configured."
        )

    output_directory = os.path.dirname(
        output_file
    )

    if output_directory:
        os.makedirs(
            output_directory,
            exist_ok=True,
        )

    write_log(
        f"===== Starting Reviews Export : "
        f"{project_name} ====="
    )

    write_log(
        f"{project_name}: "
        f"Project ID = {project_id}"
    )

    # ---------------------------------------------------------
    # LOAD ADMIN LOOKUP
    # ---------------------------------------------------------

    admin_lookup = None

    data_connector_folder = (
        project
        .get("output_files", {})
        .get("data_connector")
    )

    if data_connector_folder:
        write_log(
            "Loading Admin lookup..."
        )

        try:
            admin_lookup = AdminLookup(
                data_connector_folder=(
                    data_connector_folder
                ),
                project_id=project_id,
            )

            write_log(
                "Admin lookup loaded successfully."
            )

        except Exception as error:
            write_log(
                "Admin lookup could not be loaded. "
                "Embedded review user names and raw "
                "user IDs will be exported."
            )

            write_log(
                f"Admin lookup error: {error}"
            )

            admin_lookup = None

    else:
        write_log(
            "Data Connector folder is not configured. "
            "Admin lookup will be skipped."
        )

    # ---------------------------------------------------------
    # RETRIEVE REVIEWS
    # ---------------------------------------------------------

    write_log(
        "Reading Reviews..."
    )

    reviews = get_all_reviews(
        project_id=project_id,
        access_token=access_token,
    )

    write_log(
        f"{project_name}: "
        f"Reviews extracted = {len(reviews)}"
    )

    if not reviews:
        write_log(
            f"{project_name}: "
            "No reviews were returned."
        )

    # ---------------------------------------------------------
    # RETRIEVE WORKFLOW SNAPSHOTS
    # ---------------------------------------------------------

    if reviews:
        write_log(
            "Reading workflow snapshot for each review..."
        )

        reviews = enrich_reviews_with_workflows(
            reviews=reviews,
            project_id=project_id,
            access_token=access_token,
            max_workers=1,
        )

        workflow_success_count = sum(
            1
            for review in reviews
            if review.get("_workflowSnapshot")
        )

        workflow_error_count = sum(
            1
            for review in reviews
            if review.get("_workflowError")
        )

        write_log(
            f"{project_name}: "
            f"Workflow snapshots retrieved = "
            f"{workflow_success_count}"
        )

        if workflow_error_count:
            write_log(
                f"{project_name}: "
                f"Workflow snapshot errors = "
                f"{workflow_error_count}"
            )

    # ---------------------------------------------------------
    # EXPORT CSV
    # ---------------------------------------------------------

    write_log(
        "Exporting Reviews CSV..."
    )

    export_reviews_to_csv(
        reviews=reviews,
        output_file=output_file,
        admin_lookup=admin_lookup,
    )

    write_log(
        f"{project_name}: "
        f"Reviews CSV created at {output_file}"
    )

    # ---------------------------------------------------------
    # OPTIONAL ACC UPLOAD
    # ---------------------------------------------------------

    target_folder_id = (
        project
        .get("target_folders", {})
        .get("reviews")
    )

    if target_folder_id:
        write_log(
            "Uploading Reviews CSV to ACC..."
        )

        try:
            upload_csv_to_acc(
                project_id,
                target_folder_id,
                output_file,
                access_token,
            )

            write_log(
                f"{project_name}: "
                "Reviews CSV uploaded successfully."
            )

        except Exception as error:
            write_log(
                f"{project_name}: "
                f"Reviews CSV upload failed: {error}"
            )

            raise

    else:
        write_log(
            f"{project_name}: "
            "Reviews target folder is not configured. "
            "ACC upload skipped."
        )

    write_log(
        f"===== Reviews Export Completed : "
        f"{project_name} ====="
    )

    return output_file