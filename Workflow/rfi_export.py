from Services.rfi_api import get_all_rfis
from Services.project_users_api import get_project_users
from Services.rfi_custom_attributes_api import get_rfi_custom_attribute_map
from Services.rfi_detail_api import get_rfi_detail

from Modules.csv_export import export_rfis_to_csv
from Modules.upload import upload_csv_to_acc
from Modules.logger import write_log

import json
import requests


def export_rfis(project, access_token):
    project_name = project["name"]
    project_id = project["project_id"]

    output_file = project["output_files"]["rfis"]
    target_folder_id = project["target_folders"]["rfis"]

    write_log(f"===== Starting RFI Export : {project_name} =====")

    write_log("Reading RFIs...")
    rfis = get_all_rfis(
        project_id,
        access_token
    )

    write_log(f"{project_name}: RFIs extracted = {len(rfis)}")

    # ---------- TEMPORARY TEST ----------
    import json
    import requests

    first_rfi = rfis[0]

    rfi_id = first_rfi.get("id")

    project_api_id = (
        project_id[2:]
        if project_id.startswith("b.")
        else project_id
    )

    url = (
        "https://developer.api.autodesk.com/construction/rfis/v3/"
        f"projects/{project_api_id}/rfis/{rfi_id}"
    )

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json"
    }

    response = requests.get(url, headers=headers)

    print("Single RFI Status:", response.status_code)
    """print(json.dumps(response.json(), indent=4))"""
    # ---------- END TEST ----------
 
    write_log("Reading detailed RFI records...")

    detailed_rfis = []

    for index, rfi in enumerate(rfis, start=1):
        rfi_id = rfi.get("id")

        if not rfi_id:
            continue

        try:
            detailed_rfi = get_rfi_detail(
                project_id,
                rfi_id,
                access_token
            )

            detailed_rfis.append(detailed_rfi)

        except Exception as error:
            write_log(
                f"RFI detail failed for {rfi_id}: {error}"
            )

            # Keep the original search result if detail retrieval fails
            detailed_rfis.append(rfi)

        """print(
            f"RFI details retrieved: "
            f"{index}/{len(rfis)}"
        )"""

    rfis = detailed_rfis

    write_log("Reading Project Users...")

    try:
        user_map = get_project_users(
            project_id,
            access_token
        )
    except Exception as error:
        write_log(f"Project users lookup failed: {error}")
        user_map = {}

    write_log(f"Project user IDs mapped = {len(user_map)}")

    write_log("Reading RFI Custom Attributes...")

    try:
        custom_attribute_map = get_rfi_custom_attribute_map(
            project_id,
            access_token
        )
    except Exception as error:
        write_log(f"RFI custom attribute lookup failed: {error}")
        custom_attribute_map = {}

    write_log(f"RFI custom attributes mapped = {len(custom_attribute_map)}")

    """for key, value in custom_attribute_map.items():
        print(key)
        print(value)

    print(custom_attribute_map)"""

    for rfi in rfis:
        custom_values = rfi.get("customAttributes")

        if custom_values:
            """print("RFI with custom attribute values found:")
            print(custom_values)"""
            break
    else:
        print("No RFI contains custom attribute values.")

    export_rfis_to_csv(
        rfis,
        user_map,
        custom_attribute_map,
        output_file
    )

    write_log("Uploading RFI CSV to ACC...")

    upload_csv_to_acc(
        project_id,
        target_folder_id,
        output_file,
        access_token
    )

    write_log(f"===== RFI Export Completed : {project_name} =====")
