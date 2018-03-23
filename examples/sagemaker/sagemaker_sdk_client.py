from locust import events, HttpLocust, TaskSet, task
import boto3
import logging
import os
import time

endpoint_name = "CriteoXgboostBuiltin-2018-03-22-16-57-01"
task_name = "SagemMaker SDK Benchmark"

print("The botocore log level is: {}".format(logging.getLogger('botocore').level))
print("The botocore.vendored.requests.packages.urllib3.connectionpool log level is: {}".format(logging.getLogger('botocore.vendored.requests.packages.urllib3.connectionpool').level))

logging.getLogger('botocore').setLevel(logging.ERROR)
class SageMakerSdkClient(object):
  def __init__(self):
      self.runtime_client = boto3.client('runtime.sagemaker')

  def get_time_for_prediction(self, runtime_client, endpoint_name, content_type, payload):
      start_time = time.time()
      response = self.runtime_client.invoke_endpoint(EndpointName=endpoint_name,
                                              ContentType=content_type,
                                              Body=payload)
      end_time = time.time()
      return (end_time - start_time) * 1000

  def execute(self, name, endpoint_name, content_type, payload):
      #runtime_client = boto3.client('runtime.sagemaker')
      start_time = time.time()
      try:
          response_time = self.get_time_for_prediction(self.runtime_client, endpoint_name, content_type, payload)
          events.request_success.fire(request_type="execute", name=name, response_time=response_time, response_length=0)
      except Exception as e:
          total_time = (time.time() - start_time) * 1000
          events.request_failure.fire(request_type="execute", name=name, response_time=total_time, exception=e)

class UserTasks(TaskSet):
    @task
    def invocations(self):
        fname = os.getcwd() + "/criteo_inference_data.csv"
        with open(fname, 'rb') as f:
            payload = f.read()
        self.client.execute(name=task_name, endpoint_name=endpoint_name, content_type='text/csv', payload=payload)

class WebsiteUser(HttpLocust):
    """
    Locust user class that does requests to the locust web server running on localhost
    """

    host = "whatever. it's short circuited"

    def __init__(self, *args, **kwargs):
      super(WebsiteUser, self).__init__(*args, **kwargs)
      self.client = SageMakerSdkClient()

    min_wait = 200
    max_wait = 200
    task_set = UserTasks
