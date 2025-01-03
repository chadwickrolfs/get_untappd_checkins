# TODO:
# mock the untapd server with fastapi
# use click to ask to continue during while loop
# backup checkins_file
# read in checkins_file and get latest checkin_id
# during while loop
#    break if latest checkin_id found
#    ask if continue or break
# update checkins dict
# write checkins dict to new checkins_file
# put it all in sqlite

import json
import requests

from untappd_cred import cred


def get_checkins_response(url):
    return requests.get(
        url,
        headers={
            "Content-Type": "application/json",
            "Origin": "https://freeshell.de",
        }
    )


def get_checkins():
    pagina = 1
    checkins_log = "checkins.log"
    checkins_file = "checkins.json"
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

    checkins_response = get_checkins_response(checkins_url)
    checkins_json = checkins_response.json()
    if checkins_json["meta"]["code"] == 200:
        with open(f"checkins_{pagina:02d}.log", "w") as clph:
            json.dump(checkins_json, clph, indent=4)

        checkins = checkins_json

        while checkins_json["response"]["pagination"].get("next_url"):
            nu = checkins["response"]["pagination"]["next_url"]
            print(f"next_url: {nu}")
            pagina += 1
            print(f"pagina: {pagina:02d}")
            next_url = (f"{nu}{cred_add}")
            checkins_response = get_checkins_response(next_url)
            checkins_json = checkins_response.json()
            with open(f"checkins_{pagina:02d}.log", "w") as clph:
                json.dump(checkins_json, clph, indent=4)
            checkins.update(checkins_json)
            if nu == "" or nu is None:
                break
            if pagina > 2:
                break

        with open(checkins_log, "w") as clh:
            clh.write(f"{checkins}")

        with open(checkins_file, "w") as cfh:
            json.dump(checkins, cfh, indent=4)
    else:
        print(f"non 200 response: {checkins_json['meta']}")


def main():
    get_checkins()


if __name__ == "__main__":
    main()
