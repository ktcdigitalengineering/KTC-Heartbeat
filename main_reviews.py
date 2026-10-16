from config import PROJECTS
from Workflow.reviews_export import export_reviews

from Modules.auth import get_access_token


def main():
    access_token = get_access_token()

    for project in PROJECTS:
        project_name = project.get(
            "name",
            "Unnamed Project",
        )

        reviews_enabled = (
            project
            .get("exports", {})
            .get("reviews", False)
        )

        if not reviews_enabled:
            print(
                f"Skipping {project_name}: "
                "Reviews export disabled."
            )
            continue

        try:
            export_reviews(
                project=project,
                access_token=access_token,
            )

        except Exception as error:
            print(
                f"Reviews export failed for "
                f"{project_name}: {error}"
            )


if __name__ == "__main__":
    main()