from dotenv import load_dotenv
import os
from instagrapi import Client
from instagrapi.exceptions import LoginRequired
from pathlib import Path
import logging
import random
import json

# Init logger
logger = logging.getLogger()

# Init client
cl = Client()

# Load username and password
load_dotenv()
username = os.environ['USERNAME']
password = os.environ['PASSWORD']


# Function definitions
def login_user():
    """"
    Attempts to login to Instagram using either the provided session information
    """

    session = cl.load_settings(Path("session.json"))

    login_via_session = False
    login_via_pw = False

    if session:
        try:
            cl.set_settings(session)
            cl.login(username, password)

            # Check if session is valid
            try:
                cl.get_timeline_feed()
                print("Logged in")
            except LoginRequired:
                logger.info(
                    "Session is invalid, need to login via username and password"
                )

                old_session = cl.get_settings()

                # Use the same device uuids across logins
                cl.set_settings({})
                cl.set_uuids(old_session["uuids"])

                cl.login(username, password)
            login_via_session = True
        except Exception as e:
            logger.info("Couldn't login user using session information: %s" %
                        e)

    if not login_via_session:
        try:
            logger.info(
                "Attempting to login via username and password. username: %s" %
                "getjoyroots")
            if cl.login(username, password):
                login_via_pw = True
        except Exception as e:
            logger.info("Couldn't login user using username and password: %s" %
                        e)

    if not login_via_pw and not login_via_session:
        raise Exception("Couldn't login user with either password or session")


def read_hashtag_cursors(file_path):
    try:
        with open(file_path, 'r') as file:
            return json.load(file)
    except FileNotFoundError:
        return {}


def save_hashtag_cursors(file_path, cursors):
    with open(file_path, 'w') as file:
        json.dump(cursors, file)


def read_lines_from_file(file_path):
    with open(file_path, 'r') as file:
        return [line.strip() for line in file]


def hashtag_strategy():
    """
    Based on certain hashtags, go comment on every 4th post
    """

    cl.delay_range = [1, 3]
    try:
        print("Entered hashtag_strategy()")

        # Setup comments from external file
        comments = read_lines_from_file('comments.txt')

        # Setup hashtags from external file
        hashtags = read_lines_from_file('hashtags.txt')

        # Read cursors
        cursors = read_hashtag_cursors('cursors.json')

        # Setup limit variable
        total_comments_posted = 0

        # Iterate on hashtags from hashtags.txt and post a random comment from comments.txt on every 4th post
        for hashtag in hashtags:
            print(f"Processing hashtag: #{hashtag}")

            cursor = cursors.get(hashtag)
            medias, new_cursor = cl.hashtag_medias_v1_chunk(hashtag,
                                                            max_amount=32,
                                                            tab_key='recent',
                                                            max_id=cursor)
            cursors[hashtag] = new_cursor
            save_hashtag_cursors('cursors.json', cursors)

            print(f"Number of posts retrieved for #{hashtag}: {len(medias)}")

            for i in range(0, len(medias), 4):
                if total_comments_posted >= 192:
                    print("Reached 200 comments. Ending process.")
                    return

                media = medias[i]
                media_id = media.id
                comment = cl.media_comment(media_id, random.choice(comments))
                print(
                    f"Commented on post with hashtag #{hashtag}: {comment.text}"
                )
                total_comments_posted += 1

                cl.delay_range = [280, 320]

            print(f"Completed posting on #{hashtag} posts")

        print("Reached 200 comments. Let's call it a day.")

    except LoginRequired:
        print("Logged out. Attempting to re-login.")
        login_user()
        print("Resuming strategy.")
        hashtag_strategy()


def main():
    # Login
    login_user()
    cl.delay_range = [1, 3]

    # Begin strategy
    hashtag_strategy()


if __name__ == "__main__":
    main()