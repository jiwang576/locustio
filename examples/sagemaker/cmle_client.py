from locust import HttpLocust, TaskSet, task
import os
import subprocess
import sys

class UserTasks(TaskSet):
    @task
    def invocations(self):
        fname = os.getcwd() + "/iris_inference_data.json"
        with open(fname, 'rb') as f:
            payload = f.read()
#        token = subprocess.check_output(["gcloud", "auth", "print-access-token"])
        token = "ya29.GluFBZozHsdbX-KI2NmcbvEmhSaayQ-5aEtaqMoB0SaEyqZQq0V7UCYpkiYEKAzt2cL83YX5unTmUaLr5f0qUdZ0N6Wj5EuPEL54bsIP1XTsBlfpSS-L88QFWIUM\n"
        self.client.headers['Authorization'] = 'Bearer ' + token[:-1]
        self.client.post("", payload, auth="something")
            
class WebsiteUser(HttpLocust):
    """
    Locust user class that does requests to the locust web server running on localhost
    """
    min_wait = 200
    max_wait = 200
    task_set = UserTasks
