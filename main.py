from bottle import route, run, static_file, post, request
import os
import json
import requests
import pprint
import xmltodict
import logging
import csv
import re
import datetime as dt

logger = logging.getLogger('emailexist')
file_logger_name = 'emailexists_' + dt.datetime.today().strftime("%m_%d_%Y") + '.log'
file_logger = logging.FileHandler(file_logger_name)
NEW_FORMAT = '%(asctime)s: %(message)s'
file_logger_format = logging.Formatter(NEW_FORMAT, '%m/%d/%Y %I:%M:%S %p')
file_logger.setFormatter(file_logger_format)
logger.addHandler(file_logger)
logger.setLevel(logging.INFO)
console = logging.StreamHandler()
console.setLevel(logging.INFO)
console_format = logging.Formatter(NEW_FORMAT, '%m/%d/%Y %I:%M:%S %p')
console.setFormatter(console_format)
logging.getLogger('emailexist').addHandler(console)

GetListXML = """<Envelope>
                  <Body>
                    <GetLists>
                      <VISIBILITY>1</VISIBILITY>
                      <LIST_TYPE>0</LIST_TYPE>
                    </GetLists>
                  </Body>
                </Envelope>"""

SelectRecipXML = """<Envelope>
                      <Body>
                        <SelectRecipientData>
                        <LIST_ID>{}</LIST_ID>
                        <EMAIL>{}</EMAIL>
                        <COLUMN>
                          <NAME>Email</NAME>
                          <VALUE>{}</VALUE>
                        </COLUMN>
                      </SelectRecipientData>
                     </Body>
                    </Envelope>"""

current_path = os.getcwd()

@route('/images/<filename>')
def send_image(filename):
    return static_file(filename, root=current_path)

@route('/')
def help():
    return static_file('index.html', root=current_path)

@post('/auth')
def do_auth():
    logger.info("Received Authentication Request")
    authdata = request.json
    req_param = {
        "grant_type": "refresh_token",
        "client_id": authdata['clientid'],
        "client_secret": authdata['clientsecret'],
        "refresh_token": authdata['refreshtoken']
    }

    logger.info(pprint.pformat(authdata))
    api_endpoint = 'https://api{}.ibmmarketingcloud.com/oauth/token'.format(authdata['pod'])

    logger.info("Making OAuth token request to: {}\nWith this header: {}".format(api_endpoint, str(req_param)))
    oauth_req = requests.post(api_endpoint, data=req_param)

    logger.info("Response code: {}".format(oauth_req.status_code))
    logger.info("Response body: {}".format(oauth_req.text))

    return json.loads(oauth_req.text)

def bad_return(note):
    return {'state': 'FAIL', 'note': "{}".format(note)}

def good_return(note, data):
    return dict(state='SUCCEED',data=data,note="{}".format(note))

class ApiCalls:
    def __init__(self, pod, access_token):
        self.endpoint = 'https://api{}.silverpop.com/XMLAPI'.format(pod)
        self.access_token = access_token
        self.req_headers = {
        "Content-Type": "text/xml;charset=utf-8",
        "Authorization": 'Bearer ' + access_token
        }

    def do_post(self, xml):
        logger.info("Headers: {}".format(self.req_headers))
        logger.info("XML: {}".format(xml))
        api_req = requests.post(self.endpoint, data=xml, headers=self.req_headers)
        logger.info("Response code: {}".format(api_req.status_code))
        logger.info("Response body: {}".format(api_req.text))
        api_response = json.dumps(xmltodict.parse(api_req.text), indent=4)
        response_json = json.loads(api_response)
        return response_json

class RestApiCalls:
    def __init__(self, pod, access_token, listid):
        self.endpoint = 'https://api{}.ibmmarketingcloud.com/rest/databases/{}/gdpr_erasure'.format(pod, listid)
        self.access_token = access_token
        self.req_headers = {
        "Content-Type": "text/csv",
        "Authorization": 'Bearer ' + access_token
        }

    def do_erasure(self, email):
        logger.info("Headers: {}".format(self.req_headers))
        logger.info("Email: {}".format(email))
        api_req = requests.post(self.endpoint, data="EMAIL,{}".format(email), headers=self.req_headers)
        logger.info("Response code: {}".format(api_req.status_code))
        logger.info("Response body: {}".format(api_req.text))
        response_json = json.loads(api_req.text)
        return response_json


@post('/emailexists')
def do_emailexists():
    logger.info("Received emailexists Request")
    list_of_lists = []
    check_for_emails = []

    emailexists = request.json
    logger.info(pprint.pformat(emailexists))
    accesstoken = emailexists['accesstoken']
    pod = emailexists['pod']
    emailaddress = emailexists['email']

    api = ApiCalls(pod, accesstoken)

    logger.info("Making GetLists API Call")
    json_response = api.do_post(GetListXML)

    if json_response['Envelope']['Body']['RESULT']['SUCCESS'] == 'TRUE':
        logger.info("Parsing lists from GetLists API Call")
        for ca_list in json_response['Envelope']['Body']['RESULT']['LIST']:
            if ca_list['IS_FOLDER'] == 'false':
                list_of_lists.append({'listid': ca_list['ID'],
                                      'name': ca_list['NAME']})
        logger.info(pprint.pformat(list_of_lists))
    else:
        logger.info("GetLists call failed")
        return bad_return(json_response)

    num_of_lists = len(list_of_lists)

    for ind, li in enumerate(list_of_lists):
        if ind < 100:
            print("({}/{}) Checking List ID {} | Name {}".format(ind+1, num_of_lists, li['listid'], li['name']))
            selectxml = SelectRecipXML.format(li['listid'], emailaddress, emailaddress)
            logger.info("Making SelectRecipient API Call")
            api_response = api.do_post(selectxml)
            if api_response['Envelope']['Body']['RESULT']['SUCCESS'] == 'TRUE':
                check_for_emails.append({'listid': li['listid'],
                                         'listname': li['name'],
                                         'recipientid': api_response['Envelope']['Body']['RESULT']['RecipientId']})
            elif api_response['Envelope']['Body']['RESULT']['SUCCESS'] == 'false':
                check_for_emails.append({'listid': li['listid'],
                                         'listname': li['name'],
                                         'recipientid': '0'})
            else:
                return bad_return(api_response)

    logger.info(pprint.pformat(check_for_emails))

    logger.info("Creating a csv for results for email address {}".format(emailaddress))
    safe_email = re.sub('[^0-9a-zA-Z]+', '_', emailaddress)
    with open(safe_email + ".csv", 'w', newline='') as csvfile:
        fieldnames = ['listid', 'listname', 'recipientid']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for r in check_for_emails:
            writer.writerow(r)

    return good_return(safe_email, check_for_emails)

@post('/gdprerasure')
def do_gdprerasure():
    logger.info("Received gdprerasure Request")

    erasure_data = request.json
    logger.info(pprint.pformat(erasure_data))
    accesstoken = erasure_data['accesstoken']
    pod = erasure_data['pod']
    listid = erasure_data['listid']
    emailaddress = erasure_data['email']

    api = RestApiCalls(pod, accesstoken, listid)

    logger.info("Making GDPR Erasure API Call")
    json_response = api.do_erasure(emailaddress)
    return json_response

@post('/gdprstatus')
def do_gdprstatus():
    logger.info("Received gdprstatus Request")

    status_data = request.json
    logger.info(pprint.pformat(status_data))
    accesstoken = status_data['accesstoken']
    statusurl = status_data['url']

    req_headers = {"Authorization": 'Bearer ' + accesstoken}

    logger.info("Headers: {}".format(req_headers))
    logger.info("URL: {}".format(statusurl))
    api_req = requests.get(statusurl, headers=req_headers)
    logger.info("Response code: {}".format(api_req.status_code))
    logger.info("Response body: {}".format(api_req.text))

    return json.loads(api_req.text)

run(host='localhost', port=8080, debug=True, reloader=True)