# TODO:
# [ ] put it all in sqlite
#    but this module is get_ so hmm...
#    this will make it easier to synchronise
#    since just json files cannot be easily shifted
# [P] mock the untapd server with fastapi
# [ ] use typer to ask to continue during while loop
# [X] backup checkins_file
# [X] read in checkins_file and get latest checkin_id
# [ ] during while loop
# [ ]    break if latest checkin_id found
# [ ]    ask if continue or break
# [X] update checkins dict (now a list)
# [ ] write checkins dict to new checkins_file

import time
import json
import requests
from datetime import datetime
from pathlib import Path

from untappd_cred import cred


RATE_THRESHOLD = 5


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


def get_checkins_json(checkins_url, pagina, checkins, just_checkins):
    print(f"url: {checkins_url}")
    print(f"pagina: {pagina:02d}")
    checkins_response = get_checkins_response(checkins_url)
    rate_limit = checkins_response.headers["x-ratelimit-limit"]
    rate_remain = checkins_response.headers["x-ratelimit-remaining"]
    print(f"{rate_remain} requests left of {rate_limit} this hour")
    if int(rate_remain) < RATE_THRESHOLD:
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
    checkins_items = checkins_json["response"]["checkins"]["items"]
    Path(f"db/checkins_{pagina:02d}.json").write_text(
        json.dumps(checkins_json, indent=4)
    )
    Path(f"db/just_checkins_{pagina:02d}.json").write_text(
        json.dumps(checkins_items, indent=4)
    )
    just_checkins.append(checkins_items)
    checkins.append(checkins_json)

    return checkins, checkins_json, just_checkins


def get_checkins():
    found_last_db_id = False
    last_db_id = 0
    db_path = Path("db")
    if db_path.exists():
        db_path.rename(f"db_{datetime.now().strftime('%F')}")
    else:
        db_path.mkdir()
    if db_files := sorted([f for f in db_path.iterdir()]):
        last_checkins = json.loads(db_files[0].read_text())
        last_db_id = last_checkins[
                "response"]["checkins"]["items"][0]["checkin_id"]

    pagina = 1
    checkins = []
    just_checkins = []

    checkins_file = "checkins.json"
    checkins_file_path = db_path/Path(checkins_file)
    just_checkins_file = "just_checkins.json"
    just_checkins_file_path = db_path/Path(just_checkins_file)

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

    checkins, checkins_json, just_checkins = get_checkins_json(
        checkins_url, pagina, checkins, just_checkins
    )

    checkins_ids = [checkin["checkin_id"] for checkin in just_checkins]
    # if not here, then also must check in the while loop
    # put in a function ?
    if last_db_id in checkins_ids:
        # does this truncate the json or just the local var ?
        # position = checkins_ids.index(last_db_id)
        # just_checkins = just_checkins[:position - 1]
        found_last_db_id = True

    if found_last_db_id:
        return "get_checkins ended on first page"
        # return "SUCCESS get_checkins ended on first page"

    while nu := checkins_json["response"]["pagination"].get("next_url"):
        pagina += 1
        next_url = (f"{nu}{cred_add}")
        time.sleep(5)

        checkins, checkins_json, just_checkins = get_checkins_json(
            next_url, pagina, checkins, just_checkins
        )

        if nu == "" or nu is None:
            break
        if pagina > 7:
            break

    Path(checkins_log).write_text(f"{checkins}")
    checkins_file_path.write_text(json.dumps(checkins, indent=4))
    just_checkins_file_path.write_text(json.dumps(just_checkins, indent=4))

    return "SUCCESS get_checkins ended"


def main():
    print(f"{get_checkins()}")


if __name__ == "__main__":
    main()
