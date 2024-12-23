from utils.slack import app
from utils.env import env
from utils.deadline_checker import deadline_checker

from threading import Thread

if __name__ == "__main__":
    deadline_thread = Thread(target=deadline_checker, daemon=True)
    deadline_thread.start()
    
    app.start(port=env.port)