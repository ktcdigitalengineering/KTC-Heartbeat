import time

from config import PROJECTS, UPLOAD_INTERVAL_SECONDS
from Modules.auth import get_access_token
from Modules.logger import write_log, write_exception
from Workflow.rfi_export import export_rfis


def main():
    try:
        write_log("Starting ACC RFI Export")

        access_token = get_access_token()

        for index, project in enumerate(PROJECTS):
            if not project["exports"].get("rfis"):
                continue

            write_log(
                f"===== Processing RFIs: {project['name']} ====="
            )

            export_rfis(
                project,
                access_token
            )

            if index < len(PROJECTS) - 1:
                time.sleep(
                    UPLOAD_INTERVAL_SECONDS
                )

        write_log("RFI export completed")

    except Exception as ex:
        write_exception(ex)
        write_log("RFI export failed")


if __name__ == "__main__":
    main()

