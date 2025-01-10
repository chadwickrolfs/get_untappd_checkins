"""get_checkins.py
just get all checkins, backing up directory db if exists
there are 100 calls allowed per hour, and 64 pages.
if the pages ever get too large then this will fail
or a timer needs to be introduced

just call from a venv with requests like:
    python ./get_checkins.py
"""
import time
import json
from datetime import datetime
from pathlib import Path

from untappd_cred import cred

import requests


RATE_WARNING_THRESHOLD = 5


def Non200(Exception):
    pass


def RateLimitExceeded(Exception):
    pass


def get_checkins_response(url):
    return requests.get(
        url,
        headers={
            "Content-Type": "application/json",
            "Origin": "https://freeshell.de",
            "User-Agent": f"Simplified {cred['client_id']}",
        }
    )


def get_checkins_json(checkins_url, pagina, checkins):
    print(f"url: {checkins_url}")
    print(f"pagina: {pagina:02d}")
    checkins_response = get_checkins_response(checkins_url)
    rate_limit = checkins_response.headers["x-ratelimit-limit"]
    rate_remain = checkins_response.headers["x-ratelimit-remaining"]
    print(f"{rate_remain} requests left of {rate_limit} this hour")
    if int(rate_remain) < RATE_WARNING_THRESHOLD:
        print(f"WARNING {rate_remain} requests left of {rate_limit} this hour")
    if int(rate_remain) == 0:
        raise RateLimitExceeded(
            "ERROR rate_limit exceeded {rate_remain} of {rate_limit}"
        )
    # if DEBUG or something ?
    # Path("checkins_re_headers").write_text(f"{checkins_re_headers}")
    checkins_json = checkins_response.json()
    meta_code = checkins_json["meta"]["code"]
    if meta_code != 200:
        raise Non200(f"ERROR meta code not 200: {meta_code}")
    Path(f"db/checkins_{pagina:02d}.json").write_text(
        json.dumps(checkins_json, indent=4)
    )
    checkins.append(checkins_json)

    return checkins, checkins_json


def get_checkins():
    db_path = Path("db")
    if db_path.exists():
        db_path.rename(f"db_{datetime.now().strftime('%F')}")
    else:
        db_path.mkdir()

    pagina = 1
    checkins = []

    checkins_file = "checkins.json"
    checkins_file_path = db_path/Path(checkins_file)

    checkins_log = "checkins.log"

    checkins_access_token: str = cred["checkins_access_token"]
    checkins_url: str = (
        "https://api.untappd.com/v4/user/checkins?"
        f"access_token={checkins_access_token}"
    )
    cred_add = (
        f"&access_token={cred['checkins_access_token']}"
        f"&client_id={cred['client_id']}"
        f"&client_secret={cred['client_secret']}"
    )

    checkins, checkins_json = get_checkins_json(checkins_url, pagina, checkins)
    while nu := checkins_json["response"]["pagination"].get("next_url"):
        pagina += 1
        next_url = (f"{nu}{cred_add}")
        time.sleep(5)

        checkins, checkins_json = get_checkins_json(next_url, pagina, checkins)

        if nu == "" or nu is None:
            break
        if pagina > 2:
            break

    Path(checkins_log).write_text(f"{checkins}")
    checkins_file_path.write_text(json.dumps(checkins, indent=4))

    return "SUCCESS get_checkins ended"


def main():
    print(f"{get_checkins()}")


if __name__ == "__main__":
    main()
