from locust import events, HttpLocust, TaskSet, task
from googleapiclient import discovery
from oauth2client.client import GoogleCredentials
import json
import os
import time

project = "cmljiwang"
model = "model_xgboost_iris"
version = "version_xgboost_iris"
task_name = "CMLE SDK Benchmark"

class CmleSdkClient(object):
  def __init__(self):
    pass

  def get_time_for_prediction(self, api, parent, payload):
      start_time = time.time()
      response = api.projects().predict(body=payload, name=parent).execute()
      end_time = time.time()
      return (end_time - start_time) * 1000

  def execute(self, name, api, parent, payload):
      start_time = time.time()
      try:
          response_time = self.get_time_for_prediction(api, parent, payload)
          events.request_success.fire(request_type="execute", name=name, response_time=response_time, response_length=0)
      except Exception as e:
          totla_time = (time.time() - start_time) * 1000
          events.request_failure.fire(request_type="execute", name=name, response_time=total_time, exception=e)

class UserTasks(TaskSet):
    @task
    def invocations(self):
        fname = os.getcwd() + "/iris_inference_data.json"
        with open(fname, 'rb') as f:
            payload = json.loads(f.read())

        credentials = GoogleCredentials.get_application_default()
        api = discovery.build('ml', 'v1', credentials=credentials)
        parent = "projects/{}/models/{}/versions/{}".format(project, model, version)
        self.client.execute(name=task_name, api=api, parent=parent, payload=payload)

class WebsiteUser(HttpLocust):
    """
    Locust user class that does requests to the locust web server running on localhost
    """

    def __init__(self, *args, **kwargs):
      super(WebsiteUser, self).__init__(*args, **kwargs)
      self.client = CmleSdkClient()

    min_wait = 200
    max_wait = 200
    task_set = UserTasks
