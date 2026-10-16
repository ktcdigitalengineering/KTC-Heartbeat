import json
import time
from pathlib import Path
from typing import Any

from config import ACCOUNT_ID, PROJECTS
from Modules.auth import get_access_token

from Services.data_connector_api import (
    create_admin_data_request,
    wait_for_data_connector_job,
    get_job_data_listing,
    find_zip_file,
    get_signed_download_details,
    download_signed_file,
    extract_zip_file,
)


POLLING_INTERVAL_SECONDS = 15
MAXIMUM_WAIT_SECONDS = 1800
WAIT_BETWEEN_PROJECTS_SECONDS = 10


def get_project_output_folder(project: dict[str, Any]) -> Path:
    output_files = project.get("output_files", {})
    output_folder = output_files.get("data_connector")

    if not output_folder:
        raise ValueError(
            f"Missing output_files['data_connector'] "
            f"for project {project.get('name', 'Unknown Project')}."
        )

    return Path(output_folder)


def validate_project_config(project: dict[str, Any]) -> None:
    project_name = project.get("name")
    project_id = project.get("project_id")

    if not project_name:
        raise ValueError("Project name is missing in config.py.")

    if not project_id:
        raise ValueError(
            f"Project ID is missing for project {project_name}."
        )

    get_project_output_folder(project)


def extract_project_data_connector(
    project: dict[str, Any],
    access_token: str,
) -> dict[str, Any]:
    validate_project_config(project)

    project_name = project["name"]
    project_id = project["project_id"]

    output_folder = get_project_output_folder(project)
    extracted_folder = output_folder / "Extracted"

    output_folder.mkdir(
        parents=True,
        exist_ok=True,
    )

    print("\n" + "=" * 70)
    print(f"DATA CONNECTOR STARTED: {project_name}")
    print("=" * 70)
    print(f"Project ID: {project_id}")
    print(f"Output folder: {output_folder}")

    print(
        f"\nCreating Data Connector request for "
        f"{project_name}..."
    )

    request_data = create_admin_data_request(
        account_id=ACCOUNT_ID,
        project_id=project_id,
        access_token=access_token,
        description=f"{project_name} Admin lookup extraction",
        send_email=False,
    )

    print("\nRequest created successfully:")
    print(json.dumps(request_data, indent=4))

    request_id = request_data.get("id")

    if not request_id:
        raise RuntimeError(
            f"No request ID returned for {project_name}."
        )

    print(f"\nRequest ID: {request_id}")
    print(
        f"\nWaiting for Data Connector job for "
        f"{project_name}..."
    )

    job_data = wait_for_data_connector_job(
        account_id=ACCOUNT_ID,
        request_id=request_id,
        access_token=access_token,
        polling_interval=POLLING_INTERVAL_SECONDS,
        maximum_wait_seconds=MAXIMUM_WAIT_SECONDS,
    )

    print("\nJob completed successfully:")
    print(json.dumps(job_data, indent=4))

    job_id = job_data.get("id")

    if not job_id:
        raise RuntimeError(
            f"No job ID returned for {project_name}."
        )

    print(f"\nJob ID: {job_id}")
    print(
        f"\nRetrieving generated files for "
        f"{project_name}..."
    )

    data_listing = get_job_data_listing(
        account_id=ACCOUNT_ID,
        job_id=job_id,
        access_token=access_token,
    )

    if not data_listing:
        raise RuntimeError(
            f"No generated files returned for {project_name}."
        )

    print("\nGenerated files:")

    for item in data_listing:
        print(json.dumps(item, indent=4))

    zip_info = find_zip_file(data_listing)

    if not zip_info:
        raise RuntimeError(
            f"No ZIP file found for {project_name}."
        )

    print("\nZIP file found:")
    print(json.dumps(zip_info, indent=4))

    file_key = zip_info.get("key")

    if not file_key:
        raise RuntimeError(
            f"ZIP file key is missing for {project_name}."
        )

    signed_url, download_headers = get_signed_download_details(
        account_id=ACCOUNT_ID,
        job_id=job_id,
        file_key=file_key,
        access_token=access_token,
    )

    print("\nSigned download URL obtained.")

    zip_name = zip_info.get("name")

    if not zip_name:
        zip_name = f"{project_name}_admin_data.zip"

    output_zip = output_folder / zip_name

    downloaded_zip = download_signed_file(
        signed_url=signed_url,
        output_file=output_zip,
        download_headers=download_headers,
    )

    print("\nZIP downloaded to:")
    print(downloaded_zip)

    extracted_path = extract_zip_file(
        zip_file=downloaded_zip,
        output_folder=extracted_folder,
    )

    print("\nZIP extracted to:")
    print(extracted_path)

    extracted_files = [
        file_path
        for file_path in Path(extracted_path).rglob("*")
        if file_path.is_file()
    ]

    print("\nExtracted files:")

    for file_path in extracted_files:
        print(f"- {file_path}")

    print("\n" + "=" * 70)
    print(f"DATA CONNECTOR COMPLETED: {project_name}")
    print("=" * 70)

    return {
        "project_name": project_name,
        "request_id": request_id,
        "job_id": job_id,
        "zip_file": str(downloaded_zip),
        "extracted_folder": str(extracted_path),
        "file_count": len(extracted_files),
    }


def main() -> None:
    print("=" * 70)
    print("MULTI-PROJECT DATA CONNECTOR EXTRACTION")
    print("=" * 70)

    if not ACCOUNT_ID:
        raise ValueError(
            "ACCOUNT_ID is missing from config.py."
        )

    print("\nGetting Autodesk access token...")

    access_token = get_access_token()

    if not access_token:
        raise RuntimeError(
            "Unable to obtain Autodesk access token."
        )

    completed_projects: list[dict[str, Any]] = []
    failed_projects: list[dict[str, str]] = []
    skipped_projects: list[str] = []

    enabled_projects = [
        project
        for project in PROJECTS
        if project.get("exports", {}).get(
            "data_connector",
            False,
        )
    ]

    for project_index, project in enumerate(
        enabled_projects,
        start=1,
    ):
        project_name = project.get(
            "name",
            "Unknown Project",
        )

        try:
            result = extract_project_data_connector(
                project=project,
                access_token=access_token,
            )

            completed_projects.append(result)

        except Exception as error:
            print("\n" + "!" * 70)
            print(
                f"DATA CONNECTOR FAILED: "
                f"{project_name}"
            )
            print("!" * 70)
            print(f"Error: {error}")

            failed_projects.append(
                {
                    "project_name": project_name,
                    "error": str(error),
                }
            )

        is_last_project = project_index == len(
            enabled_projects
        )

        if not is_last_project:
            print(
                f"\nWaiting "
                f"{WAIT_BETWEEN_PROJECTS_SECONDS} seconds "
                f"before the next project..."
            )

            time.sleep(
                WAIT_BETWEEN_PROJECTS_SECONDS
            )

    for project in PROJECTS:
        project_name = project.get(
            "name",
            "Unknown Project",
        )

        data_connector_enabled = (
            project
            .get("exports", {})
            .get("data_connector", False)
        )

        if not data_connector_enabled:
            skipped_projects.append(project_name)

    print("\n" + "=" * 70)
    print("DATA CONNECTOR EXTRACTION SUMMARY")
    print("=" * 70)

    print(
        f"\nCompleted projects: "
        f"{len(completed_projects)}"
    )

    for result in completed_projects:
        print(
            f"- {result['project_name']}: "
            f"{result['file_count']} files extracted"
        )

    print(
        f"\nSkipped projects: "
        f"{len(skipped_projects)}"
    )

    for project_name in skipped_projects:
        print(f"- {project_name}")

    print(
        f"\nFailed projects: "
        f"{len(failed_projects)}"
    )

    for failure in failed_projects:
        print(
            f"- {failure['project_name']}: "
            f"{failure['error']}"
        )

    print("\nExtraction process finished.")


if __name__ == "__main__":
    main()