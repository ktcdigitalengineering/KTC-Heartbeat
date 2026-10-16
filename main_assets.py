from config import PROJECTS, UPLOAD_INTERVAL_SECONDS
import time

from Modules.auth import get_access_token
from Modules.logger import write_log, write_exception
from Workflow.asset_export import export_assets


def main():
    try:
        write_log("Starting ACC Assets Export")

        access_token = get_access_token()

        for index, project in enumerate(PROJECTS):
            if not project["exports"].get("assets"):
                continue

            write_log(f"===== Processing Assets: {project['name']} =====")
            export_assets(project, access_token)

            if index < len(PROJECTS) - 1:
                time.sleep(UPLOAD_INTERVAL_SECONDS)

        write_log("Assets export completed")

    except Exception as ex:
        write_exception(ex)
        write_log("Assets export failed")


if __name__ == "__main__":
    main()