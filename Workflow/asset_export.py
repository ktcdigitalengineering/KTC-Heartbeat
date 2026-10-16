from config import PROJECTS
from Services.asset_api import get_all_assets
from Services.custom_attributes import get_custom_attribute_map
from Services.statues import get_status_map
from Services.categories import get_category_map

from Modules.csv_export import export_assets_to_csv
from Modules.upload import upload_csv_to_acc
from Modules.logger import write_log


def export_assets(project, access_token):

    project_name = project["name"]
    project_id = project["project_id"]
    target_folder_id = project["target_folders"]["assets"]
    output_file = project["output_files"]["assets"]

    write_log(f"===== Starting Asset Export : {project_name} =====")

    write_log("Reading Custom Attributes...")
    custom_attribute_map = get_custom_attribute_map(
        project_id,
        access_token
    )

    write_log("Reading Categories...")
    category_map = get_category_map(
        project_id,
        access_token
    )

    write_log("Reading Statuses...")
    status_map = get_status_map(
        project_id,
        access_token
    )

    write_log("Reading Assets...")
    assets = get_all_assets(
        project_id,
        access_token
    )

    write_log(f"{project_name}: Assets extracted = {len(assets)}")

    export_assets_to_csv(
        assets,
        custom_attribute_map,
        status_map,
        category_map,
        output_file
    )

    write_log("Uploading CSV to ACC...")

    upload_csv_to_acc(
        project_id,
        target_folder_id,
        output_file,
        access_token
    )

    write_log(f"===== Asset Export Completed : {project_name} =====")