"""
Tests for the swaggerconformance package.

General strategy is to run validation of a schema set to use a specific URL as
the remote host, and then intercept the requests to that remot API using the
responses package.
Typically, there's no need to validate that the data caught actually matches
the constraints of the schema in these tests - the `pyswagger` module used to
drive the API does all the validation of input required for us.
"""
import logging
import unittest
import re
import os.path as osp
import json

import responses
import hypothesis

import swaggerconformance


TEST_SCHEMA_DIR = osp.relpath(osp.join(osp.dirname(osp.realpath(__file__)),
                                       'test_schemas/'))
TEST_SCHEMA_PATH = osp.join(TEST_SCHEMA_DIR, 'test_schema.json')
FULL_PUT_SCHEMA_PATH = osp.join(TEST_SCHEMA_DIR, 'full_put_schema.json')
ALL_CONSTRAINTS_SCHEMA_PATH = osp.join(TEST_SCHEMA_DIR,
                                       'all_constraints_schema.json')
PETSTORE_SCHEMA_PATH = osp.join(TEST_SCHEMA_DIR, 'petstore.json')
UBER_SCHEMA_PATH = osp.join(TEST_SCHEMA_DIR, 'uber.json')
MIRROR_REQS_SCHEMA_PATH = osp.join(TEST_SCHEMA_DIR, 'mirror_requests.json')
SCHEMA_URL_BASE = 'http://127.0.0.1:5000/api'
CONTENT_TYPE_JSON = 'application/json'


def _respond_to_method(method, path, response_json=None, status=200):
    url_re = re.compile(SCHEMA_URL_BASE + path + '$')
    responses.add(method, url_re, json=response_json, status=status,
                  content_type=CONTENT_TYPE_JSON)

def respond_to_get(path, response_json=None, status=200):
    """Respond to a GET request to the provided path."""
    _respond_to_method(responses.GET, path, response_json, status)

def respond_to_post(path, response_json=None, status=200):
    """Respond to a POST request to the provided path."""
    _respond_to_method(responses.POST, path, response_json, status)

def respond_to_put(path, response_json=None, status=200):
    """Respond to a PUT request to the provided path."""
    _respond_to_method(responses.PUT, path, response_json, status)

def respond_to_delete(path, response_json=None, status=200):
    """Respond to a DELETE request to the provided path."""
    _respond_to_method(responses.DELETE, path, response_json, status)


class APITemplateTestCase(unittest.TestCase):

    def setUp(self):
        self.client = swaggerconformance.SwaggerClient(TEST_SCHEMA_PATH)

    def tearDown(self):
        # No teardown of test fixtures required.
        pass

    def test_schema_parse(self):
        api_template = swaggerconformance.APITemplate(self.client)
        expected_endpoints = {'/schema', '/apps', '/apps/{appid}'}
        self.assertSetEqual(set(api_template.endpoints.keys()),
                            expected_endpoints)

    @responses.activate
    def test_endpoint_manually(self):
        api_template = swaggerconformance.APITemplate(self.client)

        # Find the template GET operation on the /apps/{appid} endpoint.
        app_id_get_op = None
        for operation_template in api_template.template_operations():
            if (operation_template.operation.method == 'get' and
                    operation_template.operation.path == '/apps/{appid}'):
                self.assertIsNone(app_id_get_op)
                app_id_get_op = operation_template
        self.assertIsNotNone(app_id_get_op)

        # The operation takes one parameter, 'appid', which is a string.
        self.assertEqual(list(app_id_get_op.parameters.keys()), ['appid'])
        self.assertEqual(app_id_get_op.parameters['appid'].type, 'string')

        # Send an example parameter in to the endpoint manually, catch the
        # request, and respond.
        params = {'appid': 'test_string'}
        respond_to_get('/apps/test_string', response_json={}, status=404)
        result = self.client.request(app_id_get_op, params)
        self.assertEqual(result.status, 404)


class ParameterTypesTestCase(unittest.TestCase):

    @responses.activate
    def test_full_put(self):
        # Handle all the basic endpoints.
        respond_to_get('/schema')
        respond_to_get('/example')
        respond_to_delete('/example', status=204)
        respond_to_put(r'/example/-?\d+', status=204)

        # Now just kick off the validation process.
        swaggerconformance.api_conformance_test(FULL_PUT_SCHEMA_PATH)

    @responses.activate
    def test_all_constraints(self):
        # Handle all the basic endpoints.
        respond_to_get('/schema')
        respond_to_put(r'/example/-?\d+', status=204)

        # Now just kick off the validation process.
        swaggerconformance.api_conformance_test(ALL_CONSTRAINTS_SCHEMA_PATH)


class ExternalExamplesTestCase(unittest.TestCase):

    @responses.activate
    def test_swaggerio_petstore(self):
        # Example responses matching the required models.
        pet = {"id": 0,
               "category": {"id": 0, "name": "string"},
               "name": "doggie",
               "photoUrls": ["string"],
               "tags": [{"id": 0, "name": "string"}],
               "status": "available"}
        pets = [pet]
        inventory = {"additionalProp1": 0, "additionalProp2": 0}
        order = {"id": 0,
                 "petId": 0,
                 "quantity": 0,
                 "shipDate": "2017-03-21T23:13:44.949Z",
                 "status": "placed",
                 "complete": True}
        api_response = {"code": 0, "type": "string", "message": "string"}
        user = {"id": 0,
                "username": "string",
                "firstName": "string",
                "lastName": "string",
                "email": "string",
                "password": "string",
                "phone": "string",
                "userStatus": 0}

        # Handle all the basic endpoints.
        respond_to_get('/pet')
        respond_to_post('/pet')
        respond_to_put('/pet')
        respond_to_get(r'/pet/-?\d+', response_json=pet)
        respond_to_delete(r'/pet/-?\d+')
        respond_to_post(r'/pet/-?\d+', response_json=api_response)
        respond_to_post(r'/pet/-?\d+/uploadImage', response_json=api_response)
        respond_to_get('/pet/findByStatus', response_json=pets)
        respond_to_get(r'/pet/findByStatus\?status=.*', response_json=pets)
        respond_to_get('/pet/findByTags', response_json=pets)
        respond_to_get(r'/pet/findByTags\?tags=.*', response_json=pets)
        respond_to_get('/store')
        respond_to_get('/store/inventory', response_json=inventory)
        respond_to_post('/store/order', response_json=order)
        respond_to_get(r'/store/order/-?\d+', response_json=order)
        respond_to_delete(r'/store/order/-?\d+')
        respond_to_get('/user')
        respond_to_post('/user')
        respond_to_delete('/user')
        respond_to_get(r'/user/(?!login).+', response_json=user)
        respond_to_put(r'/user/(?!login).+')
        respond_to_delete(r'/user/(?!login).+')
        respond_to_get(r'/user/login\?username=.*&password=.*',
                       response_json="example")
        respond_to_get('/user/logout')
        respond_to_post('/user/createWithArray')
        respond_to_post('/user/createWithList')
        respond_to_put(r'/example/-?\d+')

        # Now just kick off the validation process.
        swaggerconformance.api_conformance_test(PETSTORE_SCHEMA_PATH)

    @responses.activate
    def test_openapi_uber(self):
        profile = {"first_name": "steve",
                   "last_name": "stevenson",
                   "email": "example@stevemail.com",
                   "picture": "http://steve.com/stevepic.png",
                   "promo_code": "12341234"}
        activities = {"offset": 123,
                      "limit": 99,
                      "count": 432,
                      "history": [{"uuid": 9876543210}]}
        product = {"product_id": "example",
                   "description": "it's a product",
                   "display_name": "bestproductno1",
                   "capacity": "4 hippos",
                   "image": "http://hippotransports.com/hippocar.png"}
        products = [product]
        price_estimate = {"product_id": "example",
                          "currency_code": "gbp",
                          "display_name": "it's a product",
                          "estimate": "123.50",
                          "low_estimate": 123,
                          "high_estimate": 124,
                          "surge_multiplier": 22.2}
        price_estimates = [price_estimate]

        # Handle all the basic endpoints.
        respond_to_get(r'/estimates/price\?.*', response_json=price_estimates)
        respond_to_get(r'/estimates/time\?.*', response_json=products)
        respond_to_get(r'/history\?.*', response_json=activities)
        respond_to_get('/me', response_json=profile)
        respond_to_get(r'/products\?.*', response_json=products)

        # Now just kick off the validation process.
        swaggerconformance.api_conformance_test(UBER_SCHEMA_PATH)


class CompareResponsesTestCase(unittest.TestCase):

    @responses.activate
    def test_get_resp(self):
        url_base = SCHEMA_URL_BASE + '/example/'
        def request_callback(request):
            value = request.url[len(url_base):]
            value = value.replace("~", "%7E") # Hack to fix URL quoting
            # value = urllib.parse.unquote(value) # when pyswagger urlquotes
            return (200, {}, json.dumps({'in_str': value}))

        responses.add_callback(responses.GET, re.compile(url_base),
                               callback=request_callback,
                               content_type=CONTENT_TYPE_JSON)

        my_val_factory = swaggerconformance.ValueFactory()
        client = swaggerconformance.SwaggerClient(MIRROR_REQS_SCHEMA_PATH)
        api_template = swaggerconformance.APITemplate(client)
        operation = api_template.endpoints["/example/{in_str}"]["get"]
        strategy = operation.hypothesize_parameters(my_val_factory)

        @hypothesis.settings(max_examples=50)
        @hypothesis.given(strategy)
        def single_operation_test(client, operation, params):
            result = client.request(operation, params)
            assert result.status in operation.response_codes, \
                "{} not in {}".format(result.status,
                                      operation.response_codes)

            assert result.data.in_str == params["in_str"], \
                "{} != {}".format(result.data.in_str, params["in_str"])

        single_operation_test(client, operation) # pylint: disable=I0011,E1120


class MultiRequestTestCase(unittest.TestCase):

    @responses.activate
    def test_put_get_combined(self):
        """Test just to show how tests using multiple requests work."""
        body = []
        single_app_url_base = SCHEMA_URL_BASE + '/apps/'
        def put_request_callback(request):
            # Save off body to respond with.
            body.append(json.loads(request.body))
            return 204, {}, None
        def get_request_callback(request):
            # Respond with the last saved body.
            data = body.pop()
            data["name"] = "example"
            return 200, {}, json.dumps(data)

        responses.add_callback(responses.PUT, re.compile(single_app_url_base),
                               callback=put_request_callback,
                               content_type=CONTENT_TYPE_JSON)
        responses.add_callback(responses.GET, re.compile(single_app_url_base),
                               callback=get_request_callback,
                               content_type=CONTENT_TYPE_JSON)

        my_val_factory = swaggerconformance.ValueFactory()
        client = swaggerconformance.SwaggerClient(TEST_SCHEMA_PATH)
        api_template = swaggerconformance.APITemplate(client)
        put_operation = api_template.endpoints["/apps/{appid}"]["put"]
        put_strategy = put_operation.hypothesize_parameters(my_val_factory)
        get_operation = api_template.endpoints["/apps/{appid}"]["get"]
        get_strategy = get_operation.hypothesize_parameters(my_val_factory)

        @hypothesis.settings(max_examples=50)
        @hypothesis.given(put_strategy, get_strategy)
        def single_operation_test(client, put_operation, get_operation,
                                  put_params, get_params):
            """PUT an app, then get it again."""
            result = client.request(put_operation, put_params)
            assert result.status in put_operation.response_codes, \
                "{} not in {}".format(result.status,
                                      put_operation.response_codes)

            get_params["appid"] = put_params["appid"]
            result = client.request(get_operation, get_params)

            # Compare JSON representations of the data - as Python objects they
            # may contain NAN, instances of which are not equal to one another.
            out_data = json.dumps(result.data.data, sort_keys=True)
            in_data = json.dumps(put_params["payload"]["data"], sort_keys=True)
            assert out_data == in_data, \
                "{!r} != {!r}".format(out_data, in_data)

        single_operation_test(client, put_operation, get_operation) # pylint: disable=I0011,E1120


if __name__ == '__main__':
    LOG_FORMAT = '%(asctime)s:%(levelname)-7s:%(funcName)s:%(message)s'
    logging.basicConfig(format=LOG_FORMAT, level=logging.DEBUG)
    unittest.main()
