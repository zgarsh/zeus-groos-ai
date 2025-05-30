# main.py
import requests
import os
from dotenv import load_dotenv

load_dotenv()

def refresh_strava_token():
    response = requests.post(
        url="https://www.strava.com/oauth/token",
        data={
            'client_id': os.getenv('STRAVA_CLIENT_ID'),
            'client_secret': os.getenv('STRAVA_CLIENT_SECRET'),
            'grant_type': 'refresh_token',
            'refresh_token': os.getenv('STRAVA_REFRESH_TOKEN')
        }
    )
    response.raise_for_status()
    return response.json()['access_token']


def get_latest_activity(access_token):
    response = requests.get(
        url="https://www.strava.com/api/v3/athlete/activities",
        headers={"Authorization": f"Bearer {access_token}"},
        params={"per_page": 1}
    )
    response.raise_for_status()
    return response.json()[0]  # Most recent activity