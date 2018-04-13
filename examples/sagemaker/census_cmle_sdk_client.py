from locust import events, HttpLocust, TaskSet, task
from googleapiclient import discovery
from oauth2client.client import GoogleCredentials
from oauth2client.service_account import ServiceAccountCredentials
import json
import logging
import os
import time

logging.getLogger('oauth2client').setLevel(logging.ERROR)
logging.getLogger('googleapiclient.discovery').setLevel(logging.ERROR)
logging.getLogger('googleapiclient.discovery_cache').setLevel(logging.ERROR)

project = "op-beta-walkthrough"
model = "census"
api = 'https://ml.googleapis.com/v1/projects/op-beta-walkthrough/models/census:predict'
task_name = "CMLE SDK Benchmark"

headers = {}
body = {
  'instances': [
    {
      "age": 25,
      "workclass":" Private",
      "education": " 11th",
      "education_num": 7,
      "marital_status": " Never-married",
      "occupation": " Machine-op-inspct",
      "relationship": " Own-child",
      "race": " Black",
      "gender": " Male",
      "capital_gain": 0,
      "capital_loss": 0,
      "hours_per_week": 40,
      "native_country": " United-States"
    }
  ]
}

SERVICE_ACCOUNT_FILE='/home/jiwang/.cloud_credentials/op-beta-walkthrough-b46f5aa03e01.json'
SCOPES = ['https://www.googleapis.com/auth/cloud-platform']

creds = ServiceAccountCredentials.from_json_keyfile_name(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
creds.get_access_token()
creds.apply(headers)

class CmleSdkClient(object):
  def __init__(self):
    pass

  def get_time_for_prediction(self, service, parent, payload):
      start_time = time.time()
      response = service.projects().predict(body=payload, name=parent).execute()
      end_time = time.time()
      return (end_time - start_time) * 1000

  def execute(self, name, service, parent, payload):
      start_time = time.time()
      try:
          response_time = self.get_time_for_prediction(service, parent, payload)
          print(response_time)
          events.request_success.fire(request_type="execute", name=name, response_time=response_time, response_length=0)
      except Exception as e:
          total_time = (time.time() - start_time) * 1000
          events.request_failure.fire(request_type="execute", name=name, response_time=total_time, exception=e)

class UserTasks(TaskSet):
    @task
    def invocations(self):
        payload=body

        credentials = GoogleCredentials.get_application_default()
        service = discovery.build('ml', 'v1', credentials=creds)
        #service = discovery.build('ml', 'v1', cache_discovery=False)
        parent = "projects/{}/models/{}".format(project, model)
        self.client.execute(name=task_name, service=service, parent=parent, payload=payload)

class WebsiteUser(HttpLocust):
    """
    Locust user class that does requests to the locust web server running on localhost
    """

    host = "whatever. it's shortcuited"
    def __init__(self, *args, **kwargs):
      super(WebsiteUser, self).__init__(*args, **kwargs)
      self.client = CmleSdkClient()

    min_wait = 1000
    max_wait = 1000
    task_set = UserTasks
