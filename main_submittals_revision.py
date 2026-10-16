import os

from config import PROJECTS

from Modules.auth import get_access_token

from Services.submittal_metadata_api import get_metadata_maps
from Services.submittal_lookups_api import get_lookup_map
from Services.project_users_api import get_project_users

from Workflow.submittal_revision_export import (
    export_submittal_revisions
)


def normalize_project_id(project_id):
    """
    Remove the 'b.' prefix for the Submittals API.
    """

    if project_id.startswith("b."):
        return project_id[2:]

    return project_id


def main():

    access_token = get_access_token()

    os.makedirs("output", exist_ok=True)

    for project in PROJECTS:

        if not project["exports"].get(
            "submittal_revisions",
            False
        ):
            continue

        project_name = project["name"]

        raw_project_id = project["project_id"]

        submittal_project_id = normalize_project_id(
            raw_project_id
        )

        print("=" * 80)
        print(f"Processing Project : {project_name}")
        print("=" * 80)

        try:

            # -----------------------------------------
            # Metadata
            # -----------------------------------------

            item_type_map, status_map, response_map = (
                get_metadata_maps(
                    submittal_project_id,
                    access_token
                )
            )

            # -----------------------------------------
            # Packages
            # -----------------------------------------

            package_map = get_lookup_map(
                submittal_project_id,
                access_token,
                "packages",
                ["name", "displayName", "title"]
            )

            # -----------------------------------------
            # Specification Sections
            # -----------------------------------------

            spec_section_map = get_lookup_map(
                submittal_project_id,
                access_token,
                "specs",
                ["title", "name", "displayName", "number"]
            )

            # -----------------------------------------
            # Project Users
            # -----------------------------------------

            user_map = get_project_users(
                raw_project_id,
                access_token
            )

            # -----------------------------------------
            # Export Revision History
            # -----------------------------------------

            export_submittal_revisions(
                project=project,
                access_token=access_token,
                item_type_map=item_type_map,
                package_map=package_map,
                spec_section_map=spec_section_map,
                status_map=status_map,
                response_map=response_map,
                user_map=user_map
            )

            print()
            print(
                f"Completed revision export for "
                f"{project_name}"
            )

        except Exception as e:

            print()
            print(
                f"Submittal revision export failed "
                f"for {project_name}: {e}"
            )

        print()


if __name__ == "__main__":
    main()