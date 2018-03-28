from locust import HttpLocust, TaskSet, task
import os
import subprocess
import sys

class UserTasks(TaskSet):
    @task
    def invocations(self):
        fname = os.getcwd() + "/one_line_criteo.json"
        with open(fname, 'rb') as f:
            payload = f.read()
#        token = subprocess.check_output(["gcloud", "auth", "print-access-token"])
        token = "ya29.GlyLBcN-otLPp-lMH8e0aCRCpZ7yh3D3nNqlDqT-iQpUCBfO-Djzh-r8Cow6RpAOs1Ja-FUha30Uf9DJxWI2nf_nYboHSPtVvmQsDjEd-QHaT-U0GKeB8OZ2sgYxeg\n"
        self.client.headers['Authorization'] = 'Bearer ' + token[:-1]
        self.client.post("", payload, auth="something")
            
class WebsiteUser(HttpLocust):
    """
    Locust user class that does requests to the locust web server running on localhost
    """
    min_wait = 1000
    max_wait = 1000
    task_set = UserTasks
