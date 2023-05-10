import os

import dotenv
import praw
import sqlalchemy

dotenv.load_dotenv(
    "config/config.env",
)


REDDIT_THREAD = os.environ["REDDIT_THREAD"]
REDDIT_SECRET_ID = os.environ["REDDIT_SECRET_ID"]
REDDIT_CLIENT_ID = os.environ["REDDIT_CLIENT_ID"]
MYSQL_USER = os.environ["MYSQL_USER"]
MYSQL_PASSWORD = os.environ["MYSQL_PASSWORD"]
MYSQL_PORT = os.environ["MYSQL_PORT"]
MYSQL_DATABASE = os.environ["MYSQL_DATABASE"]
MYSQL_HOST = os.environ["MYSQL_HOST"]


def scrape_titles():
    try:
        reddit = praw.Reddit(
            client_id=REDDIT_CLIENT_ID,
            client_secret=REDDIT_SECRET_ID,
            user_agent="MedicalGPT",
        )
        engine = sqlalchemy.create_engine(
            sqlalchemy.engine.url.URL(
                drivername="mysql+pymysql",
                username=MYSQL_USER,
                password=MYSQL_PASSWORD,
                host=MYSQL_HOST,
                port=int(MYSQL_PORT),
                database=MYSQL_DATABASE,
                query={"charset": "utf8mb4"},
            ),
        )
        with engine.connect() as conn:
            all_posts = reddit.subreddit("AskDocs").top(time_filter="all", limit=None)
            existing_titles = conn.execute(
                sqlalchemy.text("SELECT title FROM reddit_ask_docs")
            ).fetchall()
            existing_titles = [title[0] for title in existing_titles]
            titles_to_insert = []
            for post in all_posts:
                if post.title not in existing_titles:
                    titles_to_insert.append(post.title)
            print(f"Found {len(titles_to_insert)} new titles to insert.")
            if titles_to_insert:
                conn.execute(
                    sqlalchemy.text(
                        "INSERT INTO reddit_ask_docs (title) VALUES (:title)"
                    ),
                    [{"title": title} for title in titles_to_insert],
                )
                conn.commit()
            print("Finished inserting titles.")
    except:
        import traceback

        print(f"Error: {traceback.format_exc()}")


if __name__ == "__main__":
    scrape_titles()
