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
        #token = subprocess.check_output(["gcloud", "auth", "print-access-token"])
        token = "ya29.GlyPBZbwev400nsSNrLkR5aEnMeFTN3YC4ceRWjOyvegfK28EqnvIK0q2lH6Qeyt9RclVnrwo2IYZSko96uP1LRjqGxxIFrzh2Kw1yYWcWqFoGlQDgkmbUiTbgsbRA\n"
        self.client.headers['Authorization'] = 'Bearer ' + token[:-1]
        self.client.post("", payload, auth="something")
            
class WebsiteUser(HttpLocust):
    """
    Locust user class that does requests to the locust web server running on localhost
    """
    min_wait = 200
    max_wait = 200
    task_set = UserTasks
