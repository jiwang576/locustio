import logging
import re
import sys
import time

import requests
import six
from requests import Request, Response
from requests.auth import HTTPBasicAuth
from requests.exceptions import (InvalidSchema, InvalidURL, MissingSchema,
                                 RequestException)

from six.moves.urllib.parse import urlparse, urlunparse

from . import events
from .exception import CatchResponseError, ResponseError
from .log import console_logger, setup_logging
from .awscurl import make_request

absolute_http_url_regexp = re.compile(r"^https?://", re.I)


class LocustResponse(Response):

    def raise_for_status(self):
        if hasattr(self, 'error') and self.error:
            raise self.error
        Response.raise_for_status(self)


class HttpSession(requests.Session):
    """
    Class for performing web requests and holding (session-) cookies between requests (in order
    to be able to log in and out of websites). Each request is logged so that locust can display 
    statistics.
    
    This is a slightly extended version of `python-request <http://python-requests.org>`_'s
    :py:class:`requests.Session` class and mostly this class works exactly the same. However 
    the methods for making requests (get, post, delete, put, head, options, patch, request) 
    can now take a *url* argument that's only the path part of the URL, in which case the host 
    part of the URL will be prepended with the HttpSession.base_url which is normally inherited
    from a Locust class' host property.
    
    Each of the methods for making requests also takes two additional optional arguments which 
    are Locust specific and doesn't exist in python-requests. These are:
    
    :param name: (optional) An argument that can be specified to use as label in Locust's statistics instead of the URL path. 
                 This can be used to group different URL's that are requested into a single entry in Locust's statistics.
    :param catch_response: (optional) Boolean argument that, if set, can be used to make a request return a context manager 
                           to work as argument to a with statement. This will allow the request to be marked as a fail based on the content of the 
                           response, even if the response code is ok (2xx). The opposite also works, one can use catch_response to catch a request
                           and then mark it as successful even if the response code was not (i.e 500 or 404).
    """
    def __init__(self, base_url, *args, **kwargs):
        super(HttpSession, self).__init__(*args, **kwargs)

        self.base_url = base_url
        
        # Check for basic authentication
        parsed_url = urlparse(self.base_url)
        if parsed_url.username and parsed_url.password:
            netloc = parsed_url.hostname
            if parsed_url.port:
                netloc += ":%d" % parsed_url.port
            
            # remove username and password from the base_url
            self.base_url = urlunparse((parsed_url.scheme, netloc, parsed_url.path, parsed_url.params, parsed_url.query, parsed_url.fragment))
            # configure requests to use basic auth
            self.auth = HTTPBasicAuth(parsed_url.username, parsed_url.password)
    
    def _build_url(self, path):
        """ prepend url with hostname unless it's already an absolute URL """
        if absolute_http_url_regexp.match(path):
            return path
        else:
            return "%s%s" % (self.base_url, path)
    
    def request(self, method, url, name=None, catch_response=False, **kwargs):
        """
        Constructs and sends a :py:class:`requests.Request`.
        Returns :py:class:`requests.Response` object.

        :param method: method for the new :class:`Request` object.
        :param url: URL for the new :class:`Request` object.
        :param name: (optional) An argument that can be specified to use as label in Locust's statistics instead of the URL path. 
          This can be used to group different URL's that are requested into a single entry in Locust's statistics.
        :param catch_response: (optional) Boolean argument that, if set, can be used to make a request return a context manager 
          to work as argument to a with statement. This will allow the request to be marked as a fail based on the content of the 
          response, even if the response code is ok (2xx). The opposite also works, one can use catch_response to catch a request
          and then mark it as successful even if the response code was not (i.e 500 or 404).
        :param params: (optional) Dictionary or bytes to be sent in the query string for the :class:`Request`.
        :param data: (optional) Dictionary or bytes to send in the body of the :class:`Request`.
        :param headers: (optional) Dictionary of HTTP Headers to send with the :class:`Request`.
        :param cookies: (optional) Dict or CookieJar object to send with the :class:`Request`.
        :param files: (optional) Dictionary of ``'filename': file-like-objects`` for multipart encoding upload.
        :param auth: (optional) Auth tuple or callable to enable Basic/Digest/Custom HTTP Auth.
        :param timeout: (optional) How long to wait for the server to send data before giving up, as a float, 
            or a (`connect timeout, read timeout <user/advanced.html#timeouts>`_) tuple.
        :type timeout: float or tuple
        :param allow_redirects: (optional) Set to True by default.
        :type allow_redirects: bool
        :param proxies: (optional) Dictionary mapping protocol to the URL of the proxy.
        :param stream: (optional) whether to immediately download the response content. Defaults to ``False``.
        :param verify: (optional) if ``True``, the SSL cert will be verified. A CA_BUNDLE path can also be provided.
        :param cert: (optional) if String, path to ssl client cert file (.pem). If Tuple, ('cert', 'key') pair.
        """
        
        # prepend url with hostname unless it's already an absolute URL
        url = self._build_url(url)
        
        # store meta data that is used when reporting the request to locust's statistics
        request_meta = {}
        
        # set up pre_request hook for attaching meta data to the request object
        request_meta["method"] = method
        
        response, start_time, response_time = self._send_request_safe_mode(method, url, **kwargs)
        
        # record the consumed time
        request_meta["start_time"] = start_time
        request_meta["response_time"] = response_time
        
        request_meta["name"] = name or 'placeholder' or (response.history and response.history[0] or response).request.path_url
        
        request_meta["content_size"] = 0
        # get the length of the content, but if the argument stream is set to True, we take
        # the size from the content-length header, in order to not trigger fetching of the body
        if kwargs.get("stream", False):
            request_meta["content_size"] = int(response.headers.get("content-length") or 0)
        else:
            request_meta["content_size"] = len(response.content or "")
        
        if catch_response:
            response.locust_request_meta = request_meta
            return ResponseContextManager(response)
        else:
            try:
                response.raise_for_status()
            except RequestException as e:
                events.request_failure.fire(
                    request_type=request_meta["method"], 
                    name=request_meta["name"], 
                    response_time=request_meta["response_time"], 
                    exception=e, 
                )
            else:
                events.request_success.fire(
                    request_type=request_meta["method"],
                    name=request_meta["name"],
                    response_time=request_meta["response_time"],
                    response_length=request_meta["content_size"],
                )
            return response
    
    def _send_request_safe_mode(self, method, url, **kwargs):
        """
        Send an HTTP request, and catch any exception that might occur due to connection problems.
        
        Safe mode has been removed from requests 1.x.
        """
        wrap_start_time = time.time()

        try:
            # hard-coded for CMLE prediction
            if 'auth' in kwargs:
                self.headers['Content-Type'] = 'application/json'
                uri = url
                data = kwargs['data']
                method = method
                kwargs.pop('auth')
                start_time = time.time()
                response = requests.Session.request(self, method, url, **kwargs)
                response_time = (time.time() - start_time) * 1000
                return response, start_time, response_time
                
            # hard-coded for Sagemaker prediction
            else:
                uri, data, headers, method = make_request(
                     method = method,
                     service = 'sagemaker',
                     region = 'us-east-2',
                     uri = url,
                     headers = {'Content-Type': 'text/csv'},
                     data = kwargs['data'],
                     profile = 'default',
                     access_key = None,
                     secret_key = None,
                     security_token = None)
                start_time = time.time()
                response = requests.Session.request(self, method, uri, headers=headers, data=data)
                response_time = (time.time() - start_time) * 1000
                return response, start_time, response_time
        except (MissingSchema, InvalidSchema, InvalidURL):
            raise
        except RequestException as e:
            r = LocustResponse()
            r.error = e
            r.status_code = 0  # with this status_code, content returns None
            r.request = Request(method, url).prepare() 
            wrap_response_time = (time.time() - wrap_start_time) * 1000
            return r, wrap_start_time, wrap_response_time


class ResponseContextManager(LocustResponse):
    """
    A Response class that also acts as a context manager that provides the ability to manually 
    control if an HTTP request should be marked as successful or a failure in Locust's statistics
    
    This class is a subclass of :py:class:`Response <requests.Response>` with two additional 
    methods: :py:meth:`success <locust.clients.ResponseContextManager.success>` and 
    :py:meth:`failure <locust.clients.ResponseContextManager.failure>`.
    """
    
    _is_reported = False
    
    def __init__(self, response):
        # copy data from response to this object
        self.__dict__ = response.__dict__
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc, value, traceback):
        if self._is_reported:
            # if the user has already manually marked this response as failure or success
            # we can ignore the default haviour of letting the response code determine the outcome
            return exc is None
        
        if exc:
            if isinstance(value, ResponseError):
                self.failure(value)
            else:
                return False
        else:
            try:
                self.raise_for_status()
            except requests.exceptions.RequestException as e:
                self.failure(e)
            else:
                self.success()
        return True
    
    def success(self):
        """
        Report the response as successful
        
        Example::
        
            with self.client.get("/does/not/exist", catch_response=True) as response:
                if response.status_code == 404:
                    response.success()
        """
        
        events.request_success.fire(
            request_type=self.locust_request_meta["method"],
            name=self.locust_request_meta["name"],
            #response_time=self.locust_request_meta["response_time"],
            response_time=300000000,
            response_length=self.locust_request_meta["content_size"],
        )
        self._is_reported = True
    
    def failure(self, exc):
        """
        Report the response as a failure.
        
        exc can be either a python exception, or a string in which case it will
        be wrapped inside a CatchResponseError. 
        
        Example::
        
            with self.client.get("/", catch_response=True) as response:
                if response.content == "":
                    response.failure("No data")
        """
        if isinstance(exc, six.string_types):
            exc = CatchResponseError(exc)
        
        events.request_failure.fire(
            request_type=self.locust_request_meta["method"],
            name=self.locust_request_meta["name"],
            response_time=self.locust_request_meta["response_time"],
            exception=exc,
        )
        self._is_reported = True
