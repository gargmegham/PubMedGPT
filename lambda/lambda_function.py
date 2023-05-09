import json
import os

import sqlalchemy


def lambda_handler(event, context):
    """
    triggered by cal.com webhook
    """
    try:
        MYSQL_USER = os.environ["MYSQL_USER"]
        MYSQL_PASSWORD = os.environ["MYSQL_PASSWORD"]
        MYSQL_PORT = os.environ["MYSQL_PORT"]
        MYSQL_DATABASE = os.environ["MYSQL_DATABASE"]
        MYSQL_HOST = os.environ["MYSQL_HOST"]
        event_body = event["body"]
        payload = json.loads(event_body)
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
        username = str(payload["payload"]["responses"]["name"]["value"])
        event_id = str(payload["payload"]["uid"])
        with engine.connect() as conn:
            if payload["triggerEvent"] == "BOOKING_CREATED":
                user_id = conn.execute(
                    sqlalchemy.text(
                        f"SELECT user_id FROM user WHERE username = '{username}'"
                    )
                ).fetchone()[0]
                res = conn.execute(
                    sqlalchemy.text(
                        f"INSERT INTO booking (user_id, event_id, timestamp) VALUES ({user_id}, '{event_id}', NOW())"
                    )
                )
                conn.commit()
            elif payload["triggerEvent"] == "BOOKING_CANCELLED":
                res = conn.execute(
                    sqlalchemy.text(
                        f"DELETE FROM booking WHERE event_id = '{event_id}'"
                    )
                )
                conn.commit()
        return {"statusCode": 200, "body": json.dumps("Completed successfully")}
    except Exception as err:
        print(err)
        return {"statusCode": 500, "body": json.dumps("Failed to complete")}
