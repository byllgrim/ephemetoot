#  #####################################################################
#     Ephemetoot - A script to delete your old toots
#     Copyright (C) 2018 Hugh Rundle, 2019 Hugh Rundle & Mark Eaton
#     Based partially on tweet-deleting script by @flesueur
#     (https://gist.github.com/flesueur/bcb2d9185b64c5191915d860ad19f23f)
#
#     This program is free software: you can redistribute it and/or modify
#     it under the terms of the GNU General Public License as published by
#     the Free Software Foundation, either version 3 of the License, or
#     (at your option) any later version.

#     This program is distributed in the hope that it will be useful,
#     but WITHOUT ANY WARRANTY; without even the implied warranty of
#     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#     GNU General Public License for more details.

#     You should have received a copy of the GNU General Public License
#     along with this program.  If not, see <http://www.gnu.org/licenses/>.

#     You can contact Hugh on Mastodon @hugh@ausglam.space
#     or email hugh [at] hughrundle [dot] net
#  #####################################################################

from argparse import ArgumentParser
import config
from mastodon import Mastodon, MastodonError
from datetime import datetime, timedelta, timezone
import time

def deleteBoost(toot):
        print(
            "unboosting "
            + str(toot.id)
            + " from "
            + toot.created_at.strftime("%d %b %Y")
        )

        if options.test:
            return

        # unreblog the original toot (their toot), not the toot
        # created by boosting (your toot)
        if mastodon.ratelimit_remaining == 0:
            print("Rate limit reached. Waiting for reset...")
        mastodon.status_unreblog(toot.reblog)

def deleteToot(toot):
    print(
        "deleting "
        + str(toot.id)
        + " from "
        + toot.created_at.strftime("%d %b %Y")
    )

    if options.test:
        return

    time.sleep(1) # Be nice to the server
    if mastodon.ratelimit_remaining == 0:
        print("Rate limit reached. Waiting for reset...")
    mastodon.status_delete(toot)

def checkToots(timeline):
    for toot in timeline:
        try:
            if toot.created_at >= cutoff_date:
                break

            if hasattr(toot, "reblog") and toot.reblog:
                deleteBoost(toot)
            else:
                deleteToot(toot)
        except MastodonError as e:
            print("ERROR deleting toot - " + str(toot.id) + " - " + e.args[3])
            print("Waiting 1 minute before re-trying...")
            time.sleep(60)

            try:
                print("Attempting delete again")
                mastodon.status_delete(toot)
                time.sleep(1) # be nice to the server
            except Exception as e:
                print("🛑 ERROR deleting toot - " + str(toot.id))
                print(e)
                print("Exiting due to error.")
                break
        except KeyboardInterrupt:
            print("Operation aborted.")
            break
        except Exception as e:
            print("🛑 Unknown ERROR deleting toot - " + str(toot.id))
            print(e)

    # account_statuses has a 40-toot limit.
    # Get id of last toot to use as 'max_id' in next call.
    # Then repeat checkToots() until no more toots to check.
    try:
        max_id = timeline[-1:][0].id
        next_batch = mastodon.account_statuses(user_id, limit=40, max_id=max_id)
        if len(next_batch) > 0:
            checkToots(next_batch)
    except IndexError:
        print("No toots found!")

if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument(
        "--test",
        action = "store_true",
        help = "test run without deleting anything"
    )
    options = parser.parse_args()
    if options.test:
        print("This is a test run...")

    mastodon = Mastodon(
        access_token=config.access_token,
        api_base_url=config.base_url,
        ratelimit_method="wait",
    )

    cutoff_date = datetime.now(timezone.utc) - timedelta(days=config.days_to_keep)
    user_id = mastodon.account_verify_credentials().id
    timeline = mastodon.account_statuses(user_id, limit=40)
    checkToots(timeline)
