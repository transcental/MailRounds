from slack_sdk import WebClient
import schedule
import time

from .env import env

client = WebClient(token=env.slack_bot_token)

def check_deadlines():
    mail = env.airtable.get_all_mail(view="Signup Closed")
    for m in mail:
        if not m['fields'].get('Sent Closed Message'):
            creator_id = m['fields']['Creator'][0]
            creator = env.airtable.find_user(airtable_id=creator_id)
            if not creator:
                creator = {'fields': {'Slack ID': 'U086VKE7KLY'}}
            channel = m['fields']['Channel ID']
            ts = m['fields']['Message TS']
            signup_ids = m['fields'].get('Participants', [])
            signups = [env.airtable.find_user(airtable_id=signup) for signup in signup_ids]
            ready_signups = [signup for signup in signups if signup and signup.get('fields', {}).get('Ready', False)]

            client.chat_postMessage(channel=channel, text=f"The signup deadline has passed and {len(ready_signups)} people are ready for this mail round! <@{creator['fields']['Slack ID']}> will give out more information shortly.", thread_ts=ts, reply_broadcast=True)

            env.airtable.update_mail(m['fields']['Message TS'], **{'Sent Closed Message': True})


def deadline_checker():
    schedule.every(1).minutes.do(check_deadlines)
    while True:
        schedule.run_pending()
        time.sleep(1)