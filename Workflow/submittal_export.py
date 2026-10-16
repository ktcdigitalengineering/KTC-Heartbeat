from Services.submittals_api import get_all_submittals
from Services.submittal_lookups_api import (
    get_package_map,
    get_spec_section_map
)
from Services.submittal_metadata_api import get_metadata_maps
from Services.project_users_api import get_project_users
from Modules.csv_export import export_submittals_to_csv
from Modules.upload import upload_csv_to_acc
from Modules.logger import write_log



def export_submittals(project, access_token):

    project_name = project["name"]
    project_id = project["project_id"]

    output_file = project["output_files"]["submittals"]
    target_folder_id = project["target_folders"]["submittals"]

    write_log(f"===== Starting Submittal Export : {project_name} =====")

    # Read metadata maps
    write_log("Reading Submittal Metadata...")

    item_type_map, status_map, response_map = get_metadata_maps(
        project_id,
        access_token
    )

    # Read lookup maps
    write_log("Reading Submittal Packages...")
    try:
        package_map = get_package_map(project_id, access_token)
    except Exception as e:
        write_log(f"Package lookup failed: {e}")
        package_map = {}

    write_log("Reading Spec Sections...")
    try:
        spec_section_map = get_spec_section_map(project_id, access_token)
    except Exception as e:
        write_log(f"Spec section lookup failed: {e}")
        spec_section_map = {}

    # Read submittals
    write_log("Reading Submittals...")
    submittals = get_all_submittals(project_id, access_token)

    write_log(f"{project_name}: Submittals extracted = {len(submittals)}")

    write_log("Reading Project Users...")
    try:
        user_map = get_project_users(project_id, access_token)
        
    except Exception as e:
        write_log(f"Project users lookup failed: {e}")
        user_map = {}
    


    print("Total users:", len(user_map))

    """for user_id, user_name in list(user_map.items())[:10]:
        print(user_id, "->", user_name)"""

    # Export to CSV
    export_submittals_to_csv(
        submittals,
        item_type_map,
        package_map,
        spec_section_map,
        status_map,
        response_map,
        user_map,
        output_file
    )

    write_log("Uploading Submittal CSV to ACC...")

    

    upload_csv_to_acc(
        project_id,
        target_folder_id,
        output_file,
        access_token
    )

    write_log(f"===== Submittal Export Completed : {project_name} =====")