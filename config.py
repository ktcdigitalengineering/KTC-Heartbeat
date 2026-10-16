import os
from pathlib import Path


def _load_env(path):
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def _require_env(name):
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"{name} is not set. Add it to .env (see .env.example).")
    return value


_load_env(Path(__file__).resolve().parent / ".env")

CLIENT_ID = _require_env("APS_CLIENT_ID")
CLIENT_SECRET = _require_env("APS_CLIENT_SECRET")
REDIRECT_URI = "http://localhost:8080/callback"
SCOPES = "data:read data:write data:create account:read account:write"

UPLOAD_INTERVAL_SECONDS = 180
ACCOUNT_ID = "b3d87fc2-a2ca-4c89-bac1-908fd051e4d2"

PROJECTS = [
   
    
    {
        "name": "BD202",
        "project_id": "b.32e76fb1-32d3-491f-b819-cf51e155ba2c",

        "exports": {
            "assets": True,
            "submittals": True,
            "issues": True,
            "rfis": True,
            "data_connector": True
        },

        "output_files": {
            "assets": "output/BD202_assets.csv",
            "submittals": "output/BD202_submittals.csv",
            "issues": "output/BD202_issues.csv",
            "rfis": "output/BD202_rfis.csv",
            "data_connector": "output/DataConnector/BD202"
        },

        "target_folders": {
            "assets": "urn:adsk.wipprod:fs.folder:co.S3ky4GizQpe1LbRnEUZoFw",
            "submittals": "urn:adsk.wipprod:fs.folder:co.Uc-PpOdFTPiHFA2E9hYGFg",
            "issues": "urn:adsk.wipprod:fs.folder:co.Uc-PpOdFTPiHFA2E9hYGFg",
            "rfis": "urn:adsk.wipprod:fs.folder:co.Uc-PpOdFTPiHFA2E9hYGFg",
            "data_connector": "urn:adsk.wipprod:fs.folder:co.Uc-PpOdFTPiHFA2E9hYGFg"
        }
    },
    {
        "name": "BD202-SWC",
        "project_id": "b.1bfd3753-19b6-4e85-ad24-a5d10accdd32",

        "exports": {
            "issues": True,
            "data_connector": True
            
        },

        "output_files": {
            "issues": "output/BD202-SWC_issues.csv",
            "data_connector": "output/DataConnector/BD202-SWC"
        },

        "target_folders": {
            "issues": "urn:adsk.wipprod:fs.folder:co.YC2Jxmo0QUimH-ux0cddBQ",
            "data_connector": "urn:adsk.wipprod:fs.folder:co.CR211_ISSUE_FOLDER_ID"
            
        }
    },
    {
        "name": "SGHP2A",
        "project_id": "b.63b1b894-0596-4419-95de-8f0d0eab30f2",

        "exports": {
            "assets": False,
            "submittals": True,
            "issues": False,
            "rfis": True,
            "data_connector": False
        },

        "output_files": {
            "assets": "output/SGHP2A_assets.csv",
            "submittals": "output/SGHP2A_submittals.csv",
            "issues": "output/SGHP2A_issues.csv",
            "rfis": "output/SGHP2A_rfis.csv",
            "data_connector": "output/DataConnector/SGHP2A"
        },

        "target_folders": {
            "assets": "urn:adsk.wipprod:fs.folder:co.4-qa808-QhOr6GN8GwfAig",
            "submittals": "urn:adsk.wipprod:fs.folder:co.-HDX43SdQVun_rfTQqni_g",
            "issues": "urn:adsk.wipprod:fs.folder:co.CR211_ISSUE_FOLDER_ID",
            "rfis": "urn:adsk.wipprod:fs.folder:co.-HDX43SdQVun_rfTQqni_g",
            "data_connector": "urn:adsk.wipprod:fs.folder:co.CR211_ISSUE_FOLDER_ID"
        }
    },
    {
        "name": "HDBTGP5A",
        "project_id": "b.278a3420-60dc-471a-ae9f-84206032c3e0",

        "exports": {
            "assets": False,
            "submittals": True,
            "issues": False,
            "rfis": True,
            "data_connector": False
        },

        "output_files": {
            "assets": "output/HDBTGP5A_assets.csv",
            "submittals": "output/HDBTGP5A_submittals.csv",
            "issues": "output/HDBTGP5A_issues.csv",
            "rfis": "output/HDBTGP5A_rfis.csv",
            "data_connector": "output/DataConnector/HDBTGP5A"
        },

        "target_folders": {
            "assets": "",
            "submittals": "urn:adsk.wipprod:fs.folder:co.NsIZvnCCQIKKMvVlVsRn2A",
            "issues": "urn:adsk.wipprod:fs.folder:co.CR211_ISSUE_FOLDER_ID",
            "rfis": "urn:adsk.wipprod:fs.folder:co.NsIZvnCCQIKKMvVlVsRn2A",
            "data_connector": "urn:adsk.wipprod:fs.folder:co.CR211_ISSUE_FOLDER_ID"
        }
    },
    {
        "name": "CR206",
        "project_id": "b.661fb2d1-eb9d-4df3-9edc-2258247c74c7",

        "exports": {
            "assets": True,
            "submittals": True,
            "submittal_revisions": False,
            "issues": True,
            "rfis": False,
            "data_connector": True
            
        },

        "output_files": {
            "assets": "output/CR206_assets.csv",
            "submittals": "output/CR206_submittals.csv",
            "submittal_revisions": "output/CR206_submittals_revision.csv",
            "issues": "output/CR206_issues.csv",
            "rfis": "output/CR206_rfis.csv",
            "data_connector": "output/DataConnector/CR206"
        },

        "target_folders": {
            "assets": "urn:adsk.wipprod:fs.folder:co.AAZxt72fR0yrQgotBmaHoQ",
            "submittals": "urn:adsk.wipprod:fs.folder:co.i3rDbtuPSRir3RoJx6E0vg",
            "submittal_revisions": "urn:adsk.wipprod:fs.folder:co.i3rDbtuPSRir3RoJx6E0vg",
            "issues": "urn:adsk.wipprod:fs.folder:co.i3rDbtuPSRir3RoJx6E0vg",
            "rfis": "urn:adsk.wipprod:fs.folder:co.i3rDbtuPSRir3RoJx6E0vg",
            "data_connector": "urn:adsk.wipprod:fs.folder:co.CR211_ISSUE_FOLDER_ID"
            
        }
    },
    {
        "name": "CR206-SWC",
        "project_id": "b.8fc846c0-d2cc-4d80-932e-cc2909618109",

        "exports": {
            "issues": True,
            "data_connector": True
            
        },

        "output_files": {
            "issues": "output/CR206-SWC_issues.csv",
            "data_connector": "output/DataConnector/CR206-SWC"
        },

        "target_folders": {
            "issues": "urn:adsk.wipprod:fs.folder:co.Xi9FB_QRT2G9oi1bTYlFng",
            "data_connector": "urn:adsk.wipprod:fs.folder:co.CR211_ISSUE_FOLDER_ID"
            
        }
    },
    {
        "name": "CR211",
        "project_id": "b.926c95f3-c800-4954-9f6a-f89be8c5fc67",

        "exports": {
            "assets": True,
            "submittals": True,
            "issues": True,
            "rfis": False,
            "data_connector": True,
            "reviews": True
        },

        "output_files": {
            "assets": "output/CR211_assets.csv",
            "submittals": "output/CR211_submittals.csv",
            "issues": "output/CR211_issues.csv",
            "rfis": "output/CR211_rfis.csv",
            "data_connector": "output/DataConnector/CR211",
            "reviews": "output/CR211_reviews.csv"
        },

        "target_folders": {
            "assets": "urn:adsk.wipprod:fs.folder:co.HDtN4ujrRgKj85B5u_tc2w",
            "submittals": "urn:adsk.wipprod:fs.folder:co.8p7JXnHjQqu8xIuBLrHSVQ",
            "issues": "urn:adsk.wipprod:fs.folder:co.8p7JXnHjQqu8xIuBLrHSVQ",
            "rfis": "urn:adsk.wipprod:fs.folder:co.8p7JXnHjQqu8xIuBLrHSVQ",
            "data_connector": "urn:adsk.wipprod:fs.folder:co.CR211_ISSUE_FOLDER_ID",
            "reviews":"urn:adsk.wipprod:fs.folder:co.8p7JXnHjQqu8xIuBLrHSVQ"
        }
    },
    {
        "name": "CR211-SWC",
        "project_id": "b.914484c9-d3cf-47d7-a109-d5ae4400ed49",

        "exports": {
            "issues": True,
            "data_connector": True
            
        },

        "output_files": {
            "issues": "output/CR211-SWC_issues.csv",
            "data_connector": "output/DataConnector/CR211-SWC"
        },

        "target_folders": {
            "issues": "urn:adsk.wipprod:fs.folder:co.c0i_JEvcQ5e9qspmZc6U-Q",
            "data_connector": "urn:adsk.wipprod:fs.folder:co.CR211_ISSUE_FOLDER_ID"
            
        }
    },
    {
        "name": "LWD",
        "project_id": "b.59174974-d3c4-4e18-bd1d-a63602b7904e",

        "exports": {
            "issues": True,
            "data_connector": True
            
        },

        "output_files": {
            "issues": "output/LWD_issues.csv",
            "data_connector": "output/DataConnector/LWD"
        },

        "target_folders": {
            "issues": "urn:adsk.wipprod:fs.folder:co.2cJLLIS7QfGaSdapJJ12-Q",
            "data_connector": "urn:adsk.wipprod:fs.folder:co.CR211_ISSUE_FOLDER_ID"
            
        }
    },
        {
        "name": "Digital Engineering",
        "project_id": "b.b6896fc5-c75f-495a-a2e0-a5dac21caea8",

        "exports": {
            "data_connector": False,
            "reviews": False
            
        },

        "output_files": {
            "data_connector": "output/DataConnector/Digital Engineering",
            "reviews": "output/DE_Reviews.csv"

        },

        "target_folders": {
            "data_connector": "urn:adsk.wipprod:fs.folder:co.CR211_ISSUE_FOLDER_ID",
            "reviews": "urn:adsk.wipprod:fs.folder:co.071J42AmQ2STNzZr6ZQSxg"
            
        }
    }     
]