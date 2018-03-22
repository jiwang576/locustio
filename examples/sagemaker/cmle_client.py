from locust import HttpLocust, TaskSet, task
import os
import subprocess
import sys

class UserTasks(TaskSet):
    @task
    def invocations(self):
        fname = os.getcwd() + "/criteo_inference_data.json"
        with open(fname, 'rb') as f:
            payload = f.read()
#        token = subprocess.check_output(["gcloud", "auth", "print-access-token"])
        token = "ya29.GlyGBSZDkKvcgk-2keOKUnHrDZQQwdH15L2yOja-DTDBvapZvezLHH6TBCaoNNPE877tIgEEcB0fabUADtrWUlNvuKKLr4Y3HqdOzKt37LVfFVRVIDTcK4_s5Z_0ZQ\n"
        self.client.headers['Authorization'] = 'Bearer ' + token[:-1]
        self.client.post("", payload, auth="something")
            
class WebsiteUser(HttpLocust):
    """
    Locust user class that does requests to the locust web server running on localhost
    """
    min_wait = 200
    max_wait = 200
    task_set = UserTasks
