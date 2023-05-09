import json
import os
import sqlalchemy


def lambda_handler(event, context):
    """
    triggered by cal.com webhook
    """
    try:
        MYSQL_USER=os.environ['MYSQL_USER']
        MYSQL_PASSWORD=os.environ['MYSQL_PASSWORD']
        MYSQL_PORT=os.environ['MYSQL_PORT']
        MYSQL_DATABASE=os.environ['MYSQL_DATABASE']
        MYSQL_HOST=os.environ['MYSQL_HOST']
        payload = json.loads(event['body'])
        engine = sqlalchemy.create_engine(
            sqlalchemy.engine.url.URL(
                drivername="mysql+pymysql",
                username=MYSQL_USER,
                password=MYSQL_PASSWORD,
                host=MYSQL_HOST,
                port=MYSQL_PORT,
                database=MYSQL_DATABASE,
            ),
        )
        username = payload['payload']['responses']['name']['value']
        event_id = payload['payload']['uid']
        with engine.connect() as conn:
            if payload['triggerEvent'] == 'BOOKING_CREATED':
                user_id = conn.execute(
                    f"SELECT user_id FROM user WHERE username = '{username}'"
                ).fetchone()[0]
                conn.execute(
                    f"INSERT INTO booking (user_id, event_id) VALUES ({user_id}, '{event_id}')"
                )
            elif payload['triggerEvent'] == 'BOOKING_CANCELLED':
                conn.execute(
                    f"DELETE FROM booking WHERE event_id = '{event_id}'"
                )
            conn.commit()
        return {
            'statusCode': 200,
            'body': json.dumps('Completed successfully')
        }
    except:
        return {
            'statusCode': 500,
            'body': json.dumps('Failed to complete')
        }
