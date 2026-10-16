from config import PROJECTS, UPLOAD_INTERVAL_SECONDS
import time

from Modules.auth import get_access_token
from Modules.logger import write_log, write_exception
from Workflow.submittal_export import export_submittals


def main():
    try:
        write_log("Starting ACC Submittals Export")

        access_token = get_access_token()

        for index, project in enumerate(PROJECTS):
            if not project["exports"].get("submittals"):
                continue

            write_log(f"===== Processing Submittals: {project['name']} =====")
            export_submittals(project, access_token)

            if index < len(PROJECTS) - 1:
                time.sleep(UPLOAD_INTERVAL_SECONDS)

        write_log("Submittals export completed")

    except Exception as ex:
        write_exception(ex)
        write_log("Submittals export failed")


if __name__ == "__main__":
    main()