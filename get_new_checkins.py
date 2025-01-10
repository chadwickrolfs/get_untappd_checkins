"""get_new_checkins.py
check for running fastapi and get last checkin_id
then to to untappd one page at a time
when a corresponding checkin_id is found:
    - stop going to untappd
    - consolidate the data to only new checkins
    - write file
    - exit
"""
import time
import json
import requests
from datetime import datetime
from pathlib import Path

from untappd_cred import cred


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


def get_local_checkins(checkins_url, pagina, checkins):
    try:
        local_response = requests.get(checkins_url, timeout=5)
    except requests.exceptions.ConnectionError as e:
        print(f"connection error:\n{e}")
        return "get_checkins connection to current checkins failure"

    return local_response.json()


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


def to_last_checkin(checkins, last_checkin_id, new_checkins):
    found_last = False
    checkin_items = checkins[0]["response"]["checkins"]["items"]
    checkins_ids = [checkin["checkin_id"] for checkin in checkin_items]
    print(
        f"looking for {last_checkin_id}"
        f"\nin {checkins_ids}\n"
    )
    if last_checkin_id in checkins_ids:
        print("last_checkin_id found")
        found_last = True
        position = checkins_ids.index(last_checkin_id)
        print(f"position of last id: {position}")
        new_checkins += [checkin for checkin in checkin_items[:position - 1]]
    else:
        print("last_checkin_id NOT found")
        new_checkins += [checkin for checkin in checkin_items]

    return new_checkins, found_last


def write_db_and_log(new_checkins, checkins_log_path, checkins_file_path):
    checkins_log_path.write_text(f"{new_checkins}")
    checkins_file_path.write_text(json.dumps(new_checkins, indent=4))


def get_new_checkins(
    local_hostname,
    local_port,
    local_path,
    db_pathname,
    checkins_log,
    checkins_file,
):
    pagina = 1
    checkins = []
    new_checkins = []

    local_checkins = get_local_checkins(
        f"http://{local_hostname}:{local_port}{local_path}",
        pagina,
        checkins,
    )
    if isinstance(local_checkins, dict):
        last_checkin_id = next(iter(local_checkins))
        print(f"last_checkin_id: {last_checkin_id}")
    else:
        print(f"last_checkin_id not found ! : {last_checkin_id}")
        #  could be none, could be string
        #  in any case, something wrong, just return and stop
        return local_checkins

    db_path = Path(db_pathname)
    if db_path.exists():
        db_path.rename(f"db_{datetime.now().strftime('%F')}")
    else:
        db_path.mkdir()

    checkins_file_path = db_path/Path(checkins_file)
    checkins_log_path = Path(checkins_log)

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
    new_checkins, found_last = to_last_checkin(
        checkins,
        last_checkin_id,
        new_checkins,
    )
    if found_last:
        print("found last")
        write_db_and_log(new_checkins, checkins_log_path, checkins_file_path)
        return "SUCCESS get_checkins ended on first page"
    else:
        print("did not find last")

    while nu := checkins_json["response"]["pagination"].get("next_url"):
        pagina += 1
        next_url = (f"{nu}{cred_add}")
        time.sleep(5)

        checkins, checkins_json = get_checkins_json(next_url, pagina, checkins)
        new_checkins, found_last = to_last_checkin(
            checkins,
            last_checkin_id,
            new_checkins,
        )

        if found_last:
            break
        elif nu == "" or nu is None:
            break
        elif pagina > 2:
            break

    write_db_and_log(new_checkins, checkins_log_path, checkins_file_path)
    return "SUCCESS get_checkins ended"


def main():
    local_hostname = "localhost"
    local_port = "9990"
    local_path = "/all"
    db_pathname = "new_checkins_db"
    checkins_log = "new_checkins.log"
    checkins_file = "new_checkins.json"
    print(
        f"{get_new_checkins(
            local_hostname,
            local_port,
            local_path,
            db_pathname,
            checkins_log,
            checkins_file,
        )}"
    )


if __name__ == "__main__":
    main()
