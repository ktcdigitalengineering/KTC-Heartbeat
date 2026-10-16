import os
import time
import requests

from concurrent.futures import ThreadPoolExecutor, as_completed
from Services.submittals_api import get_all_submittals
from Services.submittal_revisions_api import get_submittal_revisions

from Modules.csv_export import (
    flatten_submittal_revision,
    export_submittal_revisions_to_csv
)


MAX_WORKERS = 5


def normalize_project_id(project_id):
    if project_id.startswith("b."):
        return project_id[2:]

    return project_id


def fetch_revisions_for_submittal(
    submittal,
    project_id,
    access_token
):
    """
    Retrieve revisions for one submittal.

    This function runs inside a worker thread.
    """

    item_id = submittal.get("id")

    identifier = (
        submittal.get("identifier")
        or submittal.get("customIdentifier")
        or submittal.get("number")
        or item_id
        or "Unknown"
    )

    if not item_id:
        return {
            "success": False,
            "submittal": submittal,
            "identifier": identifier,
            "item_id": "",
            "revisions": [],
            "error": "No item ID"
        }

    try:
        revisions = get_submittal_revisions(
            project_id,
            item_id,
            access_token
        )

        return {
            "success": True,
            "submittal": submittal,
            "identifier": identifier,
            "item_id": item_id,
            "revisions": revisions,
            "error": ""
        }

    except Exception as error:
        return {
            "success": False,
            "submittal": submittal,
            "identifier": identifier,
            "item_id": item_id,
            "revisions": [],
            "error": str(error)
        }


def export_submittal_revisions(
    project,
    access_token,
    item_type_map,
    package_map,
    spec_section_map,
    status_map,
    response_map,
    user_map
):
    """
    Extract all revisions using concurrent API requests.

    One CSV row represents one submittal revision.
    """

    project_name = project["name"]

    project_id = normalize_project_id(
        project["project_id"]
    )

    output_file = project["output_files"][
        "submittal_revisions"
    ]

    output_directory = os.path.dirname(output_file)

    if output_directory:
        os.makedirs(
            output_directory,
            exist_ok=True
        )

    print("=" * 60)
    print(
        f"Starting submittal revision extraction "
        f"for {project_name}"
    )
    print("=" * 60)

    print("Retrieving submittal item list...", flush=True)

    submittals = get_all_submittals(
        project_id,
        access_token
    )

    total_submittals = len(submittals)

    print(
        f"Total submittal items found: "
        f"{total_submittals}"
    )

    print(
        f"Concurrent requests: {MAX_WORKERS}"
    )

    revision_rows = []
    failed_items = []

    start_time = time.time()
    completed_count = 0

    with ThreadPoolExecutor(
        max_workers=MAX_WORKERS
    ) as executor:

        future_map = {
            executor.submit(
                fetch_revisions_for_submittal,
                submittal,
                project_id,
                access_token
            ): submittal
            for submittal in submittals
        }

        for future in as_completed(future_map):
            completed_count += 1

            result = future.result()

            identifier = result["identifier"]

            if result["success"]:
                submittal = result["submittal"]
                revisions = result["revisions"]

                for revision in revisions:
                    revision_row = flatten_submittal_revision(
                        submittal=submittal,
                        revision=revision,
                        item_type_map=item_type_map,
                        package_map=package_map,
                        spec_section_map=spec_section_map,
                        status_map=status_map,
                        response_map=response_map,
                        user_map=user_map
                    )

                    revision_rows.append(
                        revision_row
                    )

                elapsed_seconds = (
                    time.time() - start_time
                )

                average_seconds = (
                    elapsed_seconds / completed_count
                )

                remaining_items = (
                    total_submittals - completed_count
                )

                estimated_remaining = (
                    average_seconds * remaining_items
                )

                print(
                    f"[{completed_count}/{total_submittals}] "
                    f"{identifier}: "
                    f"{len(revisions)} revision(s) | "
                    f"Estimated remaining: "
                    f"{estimated_remaining / 60:.1f} min",
                    flush=True
                )

            else:
                print(
                    f"[{completed_count}/{total_submittals}] "
                    f"Failed {identifier}: "
                    f"{result['error']}",
                    flush=True
                )

                failed_items.append({
                    "identifier": identifier,
                    "itemId": result["item_id"],
                    "reason": result["error"]
                })

    print("Writing revision CSV...", flush=True)

    export_submittal_revisions_to_csv(
        revision_rows,
        output_file
    )

    total_seconds = time.time() - start_time

    print("-" * 60)
    print(f"Project: {project_name}")
    print(f"Submittal items processed: {total_submittals}")
    print(f"Revision rows exported: {len(revision_rows)}")
    print(f"Failed submittal items: {len(failed_items)}")
    print(f"Total running time: {total_seconds / 60:.1f} minutes")
    print(f"Output file: {output_file}")
    print("-" * 60)

    if failed_items:
        print("Failed items:")

        for failed_item in failed_items:
            print(
                f"- {failed_item.get('identifier')}: "
                f"{failed_item.get('reason')}"
            )

    return revision_rows