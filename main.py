# main.py
import os
import requests
import pandas as pd
from openai import OpenAI
from datetime import datetime
import smtplib
from email.mime.text import MIMEText

from dotenv import load_dotenv

load_dotenv()


#### FUNCTION DEFINITIONS #####
def refresh_access_token():
    res = requests.post(
        "https://www.strava.com/oauth/token",
        data={
            "client_id": os.getenv("STRAVA_CLIENT_ID"),
            "client_secret": os.getenv("STRAVA_CLIENT_SECRET"),
            "refresh_token": os.getenv("STRAVA_REFRESH_TOKEN"),
            "grant_type": "refresh_token",
        }
    )
    print(res.status_code)
    print(res.json())
    res.raise_for_status()
    return res.json()["access_token"]

def get_strava_activities(access_token, per_page=5):
    url = "https://www.strava.com/api/v3/athlete/activities"
    headers = {"Authorization": f"Bearer {access_token}"}
    params = {"per_page": per_page}
    
    response = requests.get(url, headers=headers, params=params)
    response.raise_for_status()
    return response.json()

def call_strava_and_format_response(activity_count=10):
    """this gets a refreshed strava access token, calls strava to get latest n activities,
    formats them with better units, and drops unnecessary columns. It returns a pd df wih 10 rows in
    descending order by date"""
    # get strava access token
    token_data = refresh_access_token()
    # call up strava
    strava_data = get_strava_activities(access_token=token_data, per_page=activity_count)

    strava_results = pd.DataFrame(strava_data)

    strava_results['moving_time_mins'] = round(strava_results['moving_time']/60, 1)
    strava_results['distance_miles'] = round(strava_results['distance']/1609.34, 2)
    strava_results['elevation_gain_ft'] = round(strava_results['total_elevation_gain']*3.281, 1)

    filtered_strava_results = strava_results[['distance_miles', 'moving_time_mins', 'elevation_gain_ft', 'type', 'start_date_local', 'average_speed', 'average_heartrate', 'max_heartrate']]


    return filtered_strava_results

def create_good_morning_strava_prompt():
    """this returns a PROMPT to request a good morning message that includes today's date and
    an encouraging message based on the last 10 strava activities, which it formats as an array for chatgpt to read"""
    # get latest 10 strava activities (returns a pd df)
    filtered_strava_results = call_strava_and_format_response(activity_count=10)

    # sort activities just in case
    df = filtered_strava_results.sort_values("start_date_local", ascending=False)

    # format activities as text instead of current df
    activity_lines = []
    for _, row in df.iterrows():
        date = pd.to_datetime(row['start_date_local']).strftime('%Y-%m-%d')
        activity_type = row['type']
        distance = f"{row['distance_miles']:.2f} mi"
        time = f"{row['moving_time_mins']:.1f} min"
        elev = f"{row['elevation_gain_ft']:.0f} ft"
        avg_hr = f"{row['average_heartrate']:.0f}" if not pd.isnull(row['average_heartrate']) else "N/A"
        max_hr = f"{row['max_heartrate']:.0f}" if not pd.isnull(row['max_heartrate']) else "N/A"
        line = f"{date}: {activity_type} - {distance}, {time}, {elev} gain, Avg HR: {avg_hr}, Max HR: {max_hr}"
        activity_lines.append(line)

    # add date
    today = datetime.now().strftime("%Y-%m-%d")

    # put it all together
    activity_str = "\n".join(activity_lines)
    prompt = (
        f"Today is {today}.\n"
        "Here are my most recent Strava activities:\n"
        f"{activity_str}\n\n"
        """Please send me a good morning text message that includes an encouraging message about my recent strava activity and incorporates today's date.
        for example, you could tell me how my mileage this week compares to previous weeks or tell me if i've had a particularly fast run recently."""
    )

    return(prompt)


def call_large_model(instructions, prompt):
    client = OpenAI()

    # NOTES ON PROMPT ENGINEERING
    # -- If you say it's an expert on history of SF as well as local flora/fauna and then ask for a fact, every fact will be about GGP being bigger than central park
    # -- chatGPT seems to hallucinate a lot more via API than in the GUI even for the exact same model/prompt.

    response = client.responses.create(
        model="gpt-4.1",
        instructions = instructions,
        input = prompt,
    )

    return(response.output_text)

# create function to send SMS message from my email (free) instead of using twilio
def send_text_from_email(message_body="nobody told me what to say!"):
    """takes a string and sends SMS from my email address"""
    to_number = os.getenv('MY_CELL_EMAIL')
    from_email = os.getenv("MY_EMAIL")
    app_password = os.getenv("GMAIL_APP_PASSWORD")

    # create message
    msg = MIMEText(message_body)
    msg['From'] = from_email
    msg['To'] = to_number

    # dale
    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
        server.login(from_email, app_password)
        server.sendmail(from_email, [to_number], msg.as_string())

    print("Sent!")




#### MAKE IT HAPPEN ####

instructions = """You are a supportive life coach and personal trainer named Zeus Groos. Your trainee, Zach, is training for the New York Marathon on November 3 2025.
            He is doing a half marathon training program that ends on June 29 and then he'll begin the full marathon training program. You should play the role of 
            an expert coach, giving general running advice as well as specific feedback tailored to your trainee's workout history. This will be sent via SMS so please format accordingly."""

prompt = create_good_morning_strava_prompt()

message_body = call_large_model(instructions=instructions, prompt=prompt)

send_text_from_email(message_body=message_body)

print("sent message!")