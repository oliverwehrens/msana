import calendar
import json
import os
import webbrowser
from datetime import datetime, timedelta
from pathlib import Path
from typing import List

import requests
import rumps
from rumps import quit_application


def asana_tasks():
    headers = {"Authorization": f"Bearer {auth}"}
    # documentation of fields https://asana.github.io/developer_docs_prerelease/api_reference/#operation/getTask
    response = requests.get(
        f'https://app.asana.com/api/1.0/tasks?assignee=me&completed_since=now&limit=100&workspace={workspace}&opt_fields=due_on,name',
        headers=headers, )
    api_response = response.json()
    tasks = []
    for task in api_response['data']:
        if task['due_on']:
            t = Task(task['name'], task['due_on'], task['gid'])
            if t.due_date and t.due_date <= (datetime.now() + timedelta(days=7)):
                tasks.append(t)

    return tasks


class Task:
    label: str
    due_date: datetime
    weekday: str
    overdue: bool
    due_today: bool
    gid: str

    def __init__(self, text: str, due: str, gid: str):
        self.label = text
        self.due_date = datetime.strptime(due, "%Y-%m-%d")
        self.weekday = calendar.day_name[self.due_date.isoweekday() - 1]
        self.overdue = datetime.now().date() > self.due_date.date()
        self.due_today = self.due_date.date() == datetime.now().date()
        self.gid = gid

    def menu_title(self):
        attention = "⚪️"
        if self.due_today:
            attention = "🟡"
        if self.overdue:
            attention = "🔴"
        return f"{attention} {self.nice_date()} - {self.label}"

    def nice_date(self):
        return self.due_date.strftime("%-d. %b") if self.overdue else self.due_date.strftime("%A")

    def __str__(self):
        return f"{self.label} due on {self.due_date} {self.weekday} is overdue: {self.overdue} - {self.nice_date()}"


class MyMenuItem(rumps.MenuItem):
    gid: str

    def __init__(self, title, callback, gid):
        super().__init__(title, callback)
        self.gid = gid


class MsanaApp(object):
    current_tasks: List[Task] = []
    display_tasks: List[rumps.MenuItem] = []

    def __init__(self):
        self.config = {
            "app_name": "Msana",
        }

        self.app = rumps.App(self.config["app_name"])
        self.set_up_menu()
        rumps.Window(message="No .msana.json config file found", title="Error", default_text="Yes", ok="Ok")
        self.timer = rumps.Timer(callback=self.update_tasks, interval=refresh_interval_seconds)
        self.timer.start()

    def update_tasks(self, sender):
        self.app.menu.clear()
        self.current_tasks = asana_tasks()
        self.display_tasks = []
        self.app.title = f"⏰ {sum([1 for x in self.current_tasks if x.overdue or x.due_today])}"
        for task in self.current_tasks:
            item = rumps.MenuItem(title=task.menu_title(), callback=self.open_browser)
            self.display_tasks.append(item)
            self.app.menu.add(item)
        self.app.menu.add(None)
        self.app.menu.add(rumps.MenuItem(title="Quit", callback=quit_application))

    def set_up_menu(self):
        self.app.title = "🤔"

    def open_browser(self, sender):
        gid = None
        for t in self.current_tasks:
            if t.menu_title() == sender.title:
                gid = t.gid

        if not gid:
            rumps.Window(message="No such", title="Error", default_text="Yes", ok="Ok")
        else:
            webbrowser.open(f"https://app.asana.com/0/{workspace}/{gid}", new=0, autoraise=True)

    def run(self):
        self.app.run()


if __name__ == '__main__':
    home = str(Path.home())
    config_path = os.path.join(home, ".msana.json")
    if os.path.exists(config_path):
        with open(config_path) as config_file:
            config = json.load(config_file)

            auth = config['auth']
            workspace = config['workspace']
            refresh_interval_seconds = config['refresh_interval_seconds']
    else:
        exit(1)

    app = MsanaApp()
    app.run()
