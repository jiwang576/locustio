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
        token = "ya29.GlyOBcKTof-Djg9EzhEbf2W6LASs3XGtRI92oHduvx_BmriwQhsL57jNA6kB5njBUaA_Uj0PFR1GLbgUN4VKDqcqD_w7R5ajeBITblOofcHNZ4R6ki0Efs_e0LLybQ\n"
        self.client.headers['Authorization'] = 'Bearer ' + token[:-1]
        self.client.post("", payload, auth="something")
            
class WebsiteUser(HttpLocust):
    """
    Locust user class that does requests to the locust web server running on localhost
    """
    min_wait = 200
    max_wait = 200
    task_set = UserTasks
