from typing import Callable
from slack_bolt import App
from slack_sdk import WebClient

from .env import env

app = App(
    token=env.slack_bot_token,
    signing_secret=env.slack_signing_secret
)

@app.event("app_home_opened")
def update_home_tab(client: WebClient, event: dict):
    user_id = event["user"]
    user = env.airtable.find_user(user_id=user_id)
    if not user or (not user.get("Rounds") and not user["fields"].get("Rounds")):
        client.views_publish(
            user_id=event["user"],
            view={
                "type": "home",
                "blocks": [
                    {
                        "type": "header",
                        "text": {
                            "type": "plain_text",
                            "text": "Mail Rounds"
                        }
                    },
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": "Looks like you've not participated in any Mail Rounds yet :roo-sad:"
                        }
                    }
                ]
            }
        )
    else:
        participated_round_ids = user["fields"].get("Rounds", [])
        participated_rounds = [env.airtable.find_mail(airtable_id=round_id) for round_id in participated_round_ids]
        created_round_ids = user['fields'].get("Created Rounds", [])
        created_rounds = [env.airtable.find_mail(airtable_id=round_id) for round_id in created_round_ids]
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "Mail Rounds"
                },
            }
        ]
        participated_blocks = [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "Here are the Mail Rounds you've participated in:"
                }
            },
            {
                "type": "divider"
            },
            *[{
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*{round['fields']['Name']}* - {round['fields']['Status']}"
                }
            } for round in participated_rounds if round],
            {
                "type": "divider"
            }
        ] if participated_rounds else []
        created_blocks = [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "Here are the Mail Rounds you've created:"
                },
            },
                *[
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"*{round['fields']['Name']}* - {round['fields']['Status']}"
                        }
                    } for round in created_rounds if round
                ],
                {
                    "type": "divider"
                }
        ] if created_rounds else []
        
        blocks += participated_blocks + created_blocks
        
        client.views_publish(
            user_id=event["user"],
            view={
                "type": "home",
                "blocks": blocks
            }
        )
    
@app.shortcut("create_mail")
def create_mail_shortcut(ack: Callable, client: WebClient, body: dict):
    ack()
    user_id = body["user"]["id"]
    user = env.airtable.find_user(user_id)
    if not user or not user["fields"].get("Admin", False):
        client.chat_postEphemeral(
            channel=body["channel"]["id"],
            user=user_id,
            text="You don't have permission to use this!"
        )
        return
    client.views_open(
        trigger_id=body["trigger_id"],
        view={
            "type": "modal",
            "callback_id": "create_mail",
            "title": {
                "type": "plain_text",
                "text": "Crete Mail"
            },
            "submit": {
                "type": "plain_text",
                "text": "Submit"
            },
            "close": {
                "type": "plain_text",
                "text": "Cancel"
            },
            "blocks": [
                {
                    "type": "input",
                    "block_id": "mail_name",
                    "element": {
                        "type": "plain_text_input",
                        "action_id": "mail_name",
                        "placeholder": {
                            "type": "plain_text",
                            "text": "Name of the mail"
                        }
                    },
                    "label": {
                        "type": "plain_text",
                        "text": "Mail Name"
                    }
                },
                {
                    "type": "input",
                    "block_id": "submission_deadline",
                    "element": {
                        "type": "datepicker",
                        "action_id": "submission_deadline",
                        "placeholder": {
                            "type": "plain_text",
                            "text": "Select a date"
                        }
                    },
                    "label": {
                        "type": "plain_text",
                        "text": "Submission Deadline"
                    }
                },
                {
                    "type": "input",
                    "block_id": "max_ppl",
                    "element": {
                        "type": "number_input",
                        "is_decimal_allowed": False,
                        "min_value": "2",
                        "action_id": "max_ppl",
                        "placeholder": {
                            "type": "plain_text",
                            "text": "Max number of people"
                        }
                    },
                    "label": {
                        "type": "plain_text",
                        "text": "Max People"
                    }
                }
                
            ],
            "private_metadata": f"{body["channel"]["id"]};{body["message"]["ts"]};{user['id']}"
        }
    )

@app.view("create_mail")
def create_mail_view_callback(ack: Callable, body: dict, client: WebClient, say: Callable):
    ack()
    values = body["view"]["state"]["values"]
    mail_name = values["mail_name"]["mail_name"]["value"]
    
    submission_deadline = values["submission_deadline"]["submission_deadline"]["selected_date"]
    max_ppl = values["max_ppl"]["max_ppl"]["value"]
    
    channel_id, ts, user_id = body["view"]["private_metadata"].split(";")
    say(f"{channel_id}, {ts}, {user_id}", channel=env.slack_mailroom_channel)
    msg_link = f"https://hackclub.slack.com/archives/{env.slack_mailroom_channel}/p{ts.replace('.', '')}"
    
    client.chat_postMessage(
        channel=env.slack_mailroom_channel,
        text=f"{mail_name} created by <@{body['user']['id']}> on <{msg_link}|this message>."
    )
    
    env.airtable.create_mail(
        mail_name,
        ts,
        channel_id,
        submission_deadline,
        int(max_ppl),
        user_id,
    )
    
    client.reactions_add(
        channel=channel_id,
        name="rm-stamp",
        timestamp=ts
    )
    
@app.event("reaction_added")
def reaction_added_event(body: dict, client: WebClient, say: Callable):
    event = body["event"]
    if not event["reaction"] == "rm-stamp":
        return
    
    mail = env.airtable.find_mail(msg_ts=event["item"]["ts"])
    if not mail:
        return
    
    user = env.airtable.find_user(event["user"])
    if user and user.get('fields', {}).get("Address"):
        env.airtable.update_user(event["user"], **{
            "Rounds": list(set(user["fields"].get("Rounds", []) + [mail["id"]]))
        })
        client.chat_postEphemeral(channel=event["item"]["channel"], user=event["user"], text="You've signed up for this mail round!")
    elif user:
        env.airtable.update_user(event["user"], **{
            "Rounds": list(set(user["fields"].get("Rounds", []) + [mail["id"]]))
        })
        client.chat_postEphemeral(channel=event["item"]["channel"], user=event["user"], text="Looks like you've never taken part in a Mail Round before. Please use the `/mailround` command to add your information! I've already added you to this Mail Round, but you'll need to add your information to take part.")
    else:
        user = env.airtable.create_user(event["user"], round=mail["id"])
        client.chat_postEphemeral(channel=event["item"]["channel"], user=event["user"], text="Looks like you've never taken part in a Mail Round before. Please use the `/mailround` command to add your information! I've already added you to this Mail Round, but you'll need to add your information to take part.")

@app.event("reaction_removed")
def reaction_removed_event(body: dict, client: WebClient, say: Callable):
    event = body["event"]
    if not event["reaction"] == "rm-stamp":
        return
    
    mail = env.airtable.find_mail(msg_ts=event["item"]["ts"])
    if not mail:
        return
    
    user = env.airtable.find_user(event["user"])
    if user:
        env.airtable.update_user(event["user"], **{
            "Rounds": [round_id for round_id in set(user['fields'].get('Rounds', [])) if round_id != mail["id"]]
        })
        client.chat_postEphemeral(channel=event["item"]["channel"], user=event["user"], text="You've been removed from this mail round.")

@app.command('/mailround')
def mailround_command(ack: Callable, body: dict, client: WebClient):
    ack()
    user = env.airtable.find_user(body["user_id"])
    if not user:
        user = env.airtable.create_user(body["user_id"])
    client.views_open(
        trigger_id=body["trigger_id"],
        view={
            "type": "modal",
            "callback_id": "update_user",
            "title": {
                "type": "plain_text",
                "text": "Update Info"
            },
            "submit": {
                "type": "plain_text",
                "text": "Submit"
            },
            "close": {
                "type": "plain_text",
                "text": "Cancel"
            },
            "blocks": [
                {
                    "type": "input",
                    "block_id": "name",
                    "element": {
                        "type": "plain_text_input",
                        "action_id": "name",
                        "placeholder": {
                            "type": "plain_text",
                            "text": "Heidi Hakkuun"
                        }
                    },
                    "label": {
                        "type": "plain_text",
                        "text": "Shipping Name"
                    }
                },
                {
                    "type": "context",
                    "elements": [
                        {
                            "type": "mrkdwn",
                            "text": "This name will be used on all mail sent to you, make sure you're ok with other people seeing it."
                        }
                    ]
                },
                {
                    "type": "input",
                    "block_id": "raw_address",
                    "element": {
                        "type": "plain_text_input",
                        "action_id": "raw_address",
                        "multiline": True,
                        "placeholder": {
                            "type": "plain_text",
                            "text": "17 Orpheus Grove\nHeidi Corner\nBristol\nBS34 6JE"
                        }
                    },
                    "label": {
                        "type": "plain_text",
                        "text": "Address"
                    }
                },
                {
                    "type": "context",
                    "elements": [
                        {
                            "type": "mrkdwn",
                            "text": "This address will be used to send you mail, make sure it's correct. Do not include your name or country."
                        }
                    ]
                },
                {
                    "type": "input",
                    "block_id": "country",
                    "element": {
                        "type": "static_select",
                        "action_id": "country",
                        "initial_option": {
                            "value": user["fields"].get("Country", "United Kingdom"),
                            "text": {
                                "type": "plain_text",
                                "text": user["fields"].get("Country", "United Kingdom")
                            }
                        },
                        "options": [
                            {
                                "text": {
                                    "type": "plain_text",
                                    "text": country,
                                    "emoji": True
                                },
                                "value": country
                            } for country in env.COUNTRIES
                        ]
                    },
                    "label": {
                        "type": "plain_text",
                        "text": "Country"
                    }
                }
            ]
        }
    )

@app.view("update_user")
def update_user_view(ack: Callable, body: dict, client: WebClient):
    ack()
    values = body["view"]["state"]["values"]
    name = values["name"]["name"]["value"]
    raw_address = values["raw_address"]["raw_address"]["value"]
    country = values["country"]["country"]["selected_option"]["value"]
    
    env.airtable.update_user(body["user"]["id"], **{
        "Name": name,
        "Raw Address": raw_address,
        "Country": country
    })
    client.chat_postMessage(
        channel=body["user"]["id"],
        text="Your information has been updated!"
    )
    
