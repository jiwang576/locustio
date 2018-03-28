from locust import HttpLocust, TaskSet, task
import os
import sys

class UserTasks(TaskSet):
    @task
    def invocations(self):
        fname = os.getcwd() + "/one_line_criteo.csv"
        with open(fname, 'rb') as f:
            payload = f.read()
            self.client.post("/invocations", payload)
            
class WebsiteUser(HttpLocust):
    """
    Locust user class that does requests to the locust web server running on localhost
    """
    min_wait = 1000
    max_wait = 1000
    task_set = UserTasks
