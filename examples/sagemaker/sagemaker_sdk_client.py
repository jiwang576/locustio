from locust import events, HttpLocust, TaskSet, task
import boto3
import os
import time

endpoint_name = "BuiltInXGBoostEndpointPkl-2018-03-15-20-25-44"
task_name = "SagemMaker SDK Benchmark"

class SageMakerSdkClient(object):
  def __init__(self):
      pass

  def get_time_for_prediction(self, runtime_client, endpoint_name, content_type, payload):
      start_time = time.time()
      response = runtime_client.invoke_endpoint(EndpointName=endpoint_name,
                                              ContentType=content_type,
                                              Body=payload)
      end_time = time.time()
      return (end_time - start_time) * 1000

  def execute(self, name, endpoint_name, content_type, payload):
      runtime_client = boto3.client('runtime.sagemaker')
      start_time = time.time()
      try:
          response_time = self.get_time_for_prediction(runtime_client, endpoint_name, content_type, payload)
          events.request_success.fire(request_type="execute", name=name, response_time=response_time, response_length=0)
      except Exception as e:
          totla_time = (time.time() - start_time) * 1000
          events.request_failure.fire(request_type="execute", name=name, response_time=total_time, exception=e)

class UserTasks(TaskSet):
    @task
    def invocations(self):
        fname = os.getcwd() + "/iris_inference_data.csv"
        with open(fname, 'rb') as f:
            payload = f.read()
        self.client.execute(name=task_name, endpoint_name=endpoint_name, content_type='text/csv', payload=payload)

class WebsiteUser(HttpLocust):
    """
    Locust user class that does requests to the locust web server running on localhost
    """

    def __init__(self, *args, **kwargs):
      super(WebsiteUser, self).__init__(*args, **kwargs)
      self.client = SageMakerSdkClient()

    min_wait = 200
    max_wait = 200
    task_set = UserTasks
