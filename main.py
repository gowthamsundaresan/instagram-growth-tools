import os
import logging
import random
import re
from dotenv import load_dotenv
from instagrapi import Client as InstagrapiClient
from instagrapi.exceptions import LoginRequired
from openai import OpenAI
from supabase import create_client, Client as SupabaseClient

# Init logger and env
logging.basicConfig(level=logging.ERROR)
load_dotenv()

# Init Instagrapi
cl = InstagrapiClient()

# Init OpenAI
client = OpenAI()

# Init Supabase
url: str = os.environ["SUPABASE_URL"]
key: str = os.environ["SUPABASE_KEY"]
supabase: SupabaseClient = create_client(url, key)

# Load username and password
username = os.environ['INSTAGRAM_USERNAME']
password = os.environ['INSTAGRAM_PASSWORD']

# Setup action limits
total_actions = 0
max_actions = random.choice(35, 50)

# Setup conditions to perform action on a post
required_like_count = 100
required_comment_count = 5

# Setup conditions to fallback to to comments.txt instead of generating comments via GPT-4
min_caption_length = 200

# Setup prompt for comments on expert hashtags
expert_system_message = "You are the social media manager for a brand promoting alternative natural supplements. Your role is to comment on Instagram posts in a way that's genuine, relatable and imparts knowledge. Add value with your comments by giving some facts in a conversational way. Don't be too positive just keep a netural tone. Don't be supportive or compliment the person. Avoid formal language. Don't be a nice guy, just be insightful and relatable. Use conversational phrases and millennial slang where appropriate. Draw on a range of real-life perspectives and your knowledge of alternative supplements. Each comment should be directly relevant to the post, ranging from 1 to 2 sentences. Don't use the person's username in the comment. Don't use exclamation marks. Don't use any hashtags."
expert_user_message = "Write an insightful comment for an Instagram post with the caption given below. Reply to me only with the comment, nothing else. Don't enclose it in quotes. Don't use exclamation marks. Don't use any hashtags. Caption: "

# Setup prompt for comments on general hashtags
general_system_message = "You are the social media manager for a brand promoting mental wellness. Your role is to comment on Instagram posts in a way that's genuine and relatable. Don't be too positive just keep a netural tone. Don't be supportive or compliment the person. Avoid formal language. Don't be a nice guy, just be insightful and relatable. Use conversational phrases and millennial slang where appropriate. Draw on a range of real-life perspectives and experiences related to mental wellness. Each comment should be directly relevant to the post, ranging from 1 to 2 sentences. Don't use the person's username in the comment. Don't use exclamation marks. Don't use any hashtags."
general_user_message = "Write an engaging comment for an Instagram post with the caption given below. Reply to me only with the comment, nothing else. Don't enclose it in quotes. Don't use exclamation marks. Don't use any hashtags. Caption: "


# Function definitions
def login_user():
    """
    Attempts to log in to Instagram using session data if provided.
    If not, attempts to login with username/password and then stores session data. 

    Returns:
    --------
        None. The function updates the client's login state on success.

    Raises:
    -------
        Exception: If login fails using both session data and username/password.
    """

    # Load session from file if session.json exists
    if os.path.exists("session.json"):
        session = cl.load_settings("session.json")

    # Set session to None if session.json does not exist
    else:
        session = None

    login_via_session = False
    login_via_pw = False

    if session:
        try:
            cl.set_settings(session)
            cl.login(username, password)
            cl.delay_range = [3, 5]

            # Check if session is valid
            try:
                cl.get_timeline_feed()
                print("Logged in")
            except LoginRequired:
                print(
                    "Session is invalid, need to login via username and password"
                )

                old_session = cl.get_settings()

                # Use the same device uuids across logins
                cl.set_settings({})
                cl.set_uuids(old_session["uuids"])

                cl.login(username, password)
                cl.delay_range = [3, 5]
            login_via_session = True
        except Exception as e:
            print("Couldn't login user using session information: %s" % e)

    if not login_via_session:
        # Login and store session
        try:
            print(
                "Attempting to login via username and password. Username: %s" %
                "getjoyroots")
            if cl.login(username, password):
                login_via_pw = True
                cl.dump_settings("session.json")
                cl.delay_range = [3, 5]
        except Exception as e:
            print("Couldn't login user using username and password: %s" % e)

    if not login_via_pw and not login_via_session:
        raise Exception("Couldn't login user with either password or session")


def read_lines_from_file(file_path):
    """
    Reads lines from a file located at 'file_path'.

    Parameters:
    -----------
        file_path : str
            The path of the file to read from.

    Returns:
    --------
        list of str
            A list containing each line in the file as a separate string.
    """
    with open(file_path, 'r') as file:
        return [line.strip() for line in file]


def remove_emojis(text):
    """
    Removes all emoji characters from a given string uses a regex.
    Covers a wide range of emojis, including emoticons, symbols, pictographs, transport and map symbols, flags, and more.

    Parameters:
    -----------
    text : str
        The input string from which emojis will be removed.

    Returns:
    --------
    str
        A new string with all emoji characters removed.
    """

    # Regex pattern to match all emoji characters
    emoji_pattern = re.compile(
        "["
        u"\U0001F600-\U0001F64F"  # emoticons
        u"\U0001F300-\U0001F5FF"  # symbols & pictographs
        u"\U0001F680-\U0001F6FF"  # transport & map symbols
        u"\U0001F1E0-\U0001F1FF"  # flags (iOS)
        u"\U00002702-\U000027B0"
        u"\U000024C2-\U0001F251"
        "]+",
        flags=re.UNICODE)
    return emoji_pattern.sub(r'', text)


def growth():
    """
    Executes the strategy of engaging with Instagram posts through specific hashtags.
    It iterates through hashtags from hashtags.txt, selects posts at random, screens it for selection and either likes it or posts a comment generated by GPT-4.
    In case a post doesn't have a caption, the function falls back on choosing a random comment from comments.txt

    The function runs 200 actions and ensures that login is maintained throughout the process.

    Returns:
    --------
        None. The function operates by interacting with Instagram posts and may output logs.
    """

    cl.delay_range = [1, 3]
    print("Entered hashtag_strategy()")

    try:
        # Read comments and randomize them
        comments = read_lines_from_file('comments.txt')
        random.shuffle(comments)

        # Get all hashtags, combine and randomize them
        general_hashtags = read_lines_from_file('general_hashtags.txt')
        expert_hashtags = read_lines_from_file('expert_hashtags.txt')
        combined_hashtags = general_hashtags + expert_hashtags
        random.shuffle(combined_hashtags)

        # Iterate over hashtags and comment on 3 random posts for each
        for hashtag in combined_hashtags:
            if total_actions >= max_actions:
                break

            print(f"Processing hashtag: #{hashtag}")

            # Reset media_found
            media_found = True

            # Fetch either top or recent posts for the hashtag, up to 100
            tab_key = random.choice(['recent', 'top'])
            medias, new_cursor = cl.hashtag_medias_v1_chunk(
                hashtag,
                max_amount=100,
                tab_key=tab_key,
            )
            print(
                f"Number of posts retrieved for {tab_key} posts of #{hashtag}: {len(medias)}"
            )
            cl.delay_range = [3, 5]

            # Choose 1 random post
            selected_posts = random.sample(medias, min(len(medias), 10))

            # Check if post meets requirements
            for media in selected_posts:
                # Retrieve past action on this post from DB
                result = supabase.from_('Media Actions').select('media_id').eq(
                    'media_id', media.id).execute()

                # Post has been touched in the past, we take no action
                data = result.data
                count = len(data) if data is not None else 0

                if count > 0:
                    print(f"A past action has been taken on this media")

                # Post selection checks
                elif (media.like_count > required_like_count
                      and media.comment_count > required_comment_count):
                    selected_post = media
                    media_found = True
                    print(
                        f"Media selected. Like count: {media.like_count} || Comment count: {media.comment_count}"
                    )
                    break

                # Post didn't meet requirements
                else:
                    print(
                        f"Media not selected. Like count: {media.like_count} || Comment count: {media.comment_count}"
                    )

            # Take action (like or comment) on the selected post
            if media_found == True:
                # Randomize what action would be taken
                action_type = random.choice(['like', 'comment'])

                # Get media info
                media_id = selected_post.id
                media_pk = selected_post.pk

                # Check if hashtag is from expert list
                is_expert_hashtag = hashtag in expert_hashtags

                # Perform like action
                if action_type == 'like':
                    if cl.media_like(media_id):
                        total_actions += 1

                        # Update DB
                        result = supabase.table('Media Actions').insert({
                            "media_id":
                            media_id,
                            "action_type":
                            "like",
                        }).execute()

                        # Print update
                        print(f"Liked post with ID {media_id}")
                        print(f"Total actions: {total_actions}")
                        print("Resting [240, 360]")
                        cl.delay_range = [240, 360]

                # Perform comment action
                else:
                    # Fetch media information
                    media_info = cl.media_info(media_pk).dict()
                    caption = media_info.get('caption_text', '').strip()
                    cl.delay_range = [3, 5]

                    # Fallback to random comment from comments.txt if no caption or caption too short
                    if not caption or len(caption < min_caption_length):
                        print(
                            f"Commenting on post of ID {media_id} with no caption"
                        )
                        comments = read_lines_from_file('comments.txt')
                        comment = random.choice(comments)

                    # Generate a comment using GPT-4
                    else:
                        print(
                            f"Commenting on post of ID {media_id} with caption: {caption}"
                        )

                        if is_expert_hashtag:
                            system_message = expert_system_message
                            user_message = expert_user_message + caption

                        else:
                            system_message = general_system_message
                            user_message = general_user_message + caption

                        response = client.chat.completions.create(
                            model="gpt-4",
                            messages=[{
                                "role": "system",
                                "content": system_message
                            }, {
                                "role": "user",
                                "content": user_message
                            }])
                        comment = response.choices[0].message.content
                        comment = remove_emojis(comment)

                    # Post comment
                    posted_comment = cl.media_comment(media_id, comment)
                    total_actions += 1

                    # Update DB
                    result = supabase.table('Media Actions').insert({
                        "media_id":
                        media_id,
                        "action_type":
                        "comment",
                        "action_details":
                        comment
                    }).execute()

                    # Print update
                    print(
                        f"Commented on post with hashtag #{hashtag}: {posted_comment.text}"
                    )
                    print(f"Total actions: {total_actions}")
                    print("Resting [500, 1000]")
                    cl.delay_range = [500, 1000]

            # None of the randomly chosen posts from this hashtag passed selection
            else:
                print(f"No suitable media found for #{hashtag}")

        # End of session
        print(f"Reached {max_actions} actions. Let's call it a day.")

    except LoginRequired:
        # Re-login
        print("Logged out. Attempting to re-login.")
        login_user()

        # Resume strategy
        print("Resuming strategy.")
        hashtag_strategy()


def main():
    """
    Main function to execute the Instagram engagement script. Performs the login and then starts the hashtag engagement strategy.

    Returns:
    --------
        None.
    """
    # Login
    login_user()
    cl.delay_range = [1, 3]

    # Begin strategy
    growth()


if __name__ == "__main__":
    main()