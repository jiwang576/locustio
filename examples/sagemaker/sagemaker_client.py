from locust import HttpLocust, TaskSet, task
import os
import sys

class UserTasks(TaskSet):
    @task
    def invocations(self):
        fname = os.getcwd() + "/criteo_inference_data.csv"
        with open(fname, 'rb') as f:
            payload = f.read()
            self.client.post("/invocations", payload)
            
class WebsiteUser(HttpLocust):
    """
    Locust user class that does requests to the locust web server running on localhost
    """
    min_wait = 200
    max_wait = 200
    task_set = UserTasks
