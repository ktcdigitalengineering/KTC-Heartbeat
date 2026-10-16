import time

from config import (
    PROJECTS,
    UPLOAD_INTERVAL_SECONDS
)

from Modules.auth import (
    get_access_token
)
from Modules.logger import (
    write_log,
    write_exception
)
from Workflow.issue_export import (
    export_issues
)


def main():
    try:
        write_log(
            "Starting ACC Issues Export"
        )

        access_token = get_access_token()

        enabled_projects = [
            project
            for project in PROJECTS
            if project.get(
                "exports",
                {}
            ).get(
                "issues",
                False
            )
        ]

        for index, project in enumerate(
            enabled_projects
        ):
            write_log(
                f"===== Processing Issues: "
                f"{project['name']} ====="
            )

            export_issues(
                project,
                access_token
            )

            if index < len(enabled_projects) - 1:
                write_log(
                    f"Waiting "
                    f"{UPLOAD_INTERVAL_SECONDS} "
                    f"seconds before next project..."
                )

                time.sleep(
                    UPLOAD_INTERVAL_SECONDS
                )

        write_log(
            "Issues export completed"
        )

    except Exception as ex:
        write_exception(ex)

        write_log(
            "Issues export failed"
        )


if __name__ == "__main__":
    main()