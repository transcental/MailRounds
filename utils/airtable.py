from pyairtable import Api

class AirtableManager:
    def __init__(self, api_key: str, base_id: str, production: bool = False):
        api = Api(api_key)
        self.users_table = (
            api.table(base_id, "Users") 
            if production
            else api.table(base_id, "Test Users")
        )
        self.mail_table = (
            api.table(base_id, "Mail")
            if production
            else api.table(base_id, "Test Mail")
        )
        print("Connected to Airtable")

    def create_user(self, user_id: str, name: str = "", raw_address: str = "", country: str = "", round: str | None = None):
        user = self.users_table.create({
            "Slack ID": user_id,
            "Name": name,
            "Raw Address": raw_address,
            "Country": country,
            "Rounds": [round] if round else [],
        })
        return user

    def create_mail(self, name: str, msg_ts: str, channel_id: str, submission_deadline: str, max_ppl: int, creator_id: str):
        mail = self.mail_table.create({
            "Name": name,
            "Message TS": msg_ts,
            'Channel ID': channel_id,
            "Signup Deadline": submission_deadline,
            "Max People": max_ppl, 
            "Creator": [creator_id],
            "Participants": [creator_id]
        })
        return mail

    def find_user(self, airtable_id: str | None = None, user_id: str| None = None):
        return self.users_table.first(formula=f"{{Slack Id}} = '{user_id}'") if not airtable_id else self.users_table.get(airtable_id)

    def find_mail(self, msg_ts: str | None = None, airtable_id: str | None = None):
        return self.mail_table.first(formula=f"{{Message TS}} = '{msg_ts}'") if not airtable_id else self.mail_table.get(airtable_id)
        
    def update_user(self, user_id: str, **updates):
        user = self.find_user(user_id=user_id)
        if not user:
            return
        self.users_table.update(user["id"], updates)


    def update_mail(self, msg_ts: str, **updates):
        mail = self.find_mail(msg_ts=msg_ts)
        if not mail:
            return
        self.mail_table.update(mail["id"], updates)
    
    def get_all_mail(self, view: str | None = None):
        return self.mail_table.all(view=view) if view else self.mail_table.all()