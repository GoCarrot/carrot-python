# Carrot -- Copyright (C) 2012 GoCarrot Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import base64, hashlib, hmac, httplib, json, sys, time, urllib, uuid

class Carrot(object):
    NOT_CREATED = "Carrot user does not exist."
    NOT_AUTHORIZED = "Carrot user has not authorized application."
    UNDETERMINED = "Carrot user status unknown."
    READ_ONLY = "Carrot user has not granted 'publish_actions' permission."
    AUTHORIZED = "Carrot user authorized."

    def getHttpCon(self):
        if self.hostname.partition(":")[0] == "localhost":
            return httplib.HTTPConnection(self.hostname)
        else:
            return httplib.HTTPSConnection(self.hostname)

    def __init__(self, appId, appSecret, hostname = "gocarrot.com"):
        self.appId = appId
        self.appSecret = appSecret
        self.hostname = hostname

    def validateUser(self, userId, accessToken):
        ret = Carrot.UNDETERMINED
        params = urllib.urlencode({'access_token': accessToken, 'api_key': userId})
        headers = {"Content-type": "application/x-www-form-urlencoded"}
        conn = self.getHttpCon()
        conn.connect()
        conn.request("POST", "/games/" + self.appId + "/users.json", params, headers)
        response = conn.getresponse()
        if response.status == 201 or response.status == 200:
            ret = Carrot.AUTHORIZED
        elif response.status == 401:
            ret = Carrot.READ_ONLY
        elif response.status == 405:
            ret = Carrot.NOT_AUTHORIZED
        elif response.status == 422:
            ret = Carrot.NOT_CREATED
        else:
            sys.stderr.write("Error validating Carrot user (" + str(response.status) + "): " + response.read() + "\n")
        conn.close()
        return ret

    def postAchievement(self, userId, achievementId):
        endpoint = "/me/achievements.json"
        query_params = {'achievement_id': achievementId}
        return self.postSignedRequest(userId, endpoint, query_params)

    def postHighScore(self, userId, score):
        endpoint = "/me/scores.json"
        return self.postSignedRequest(userId, endpoint, {'value': score})

    def postAction(self, userId, actionId, objectInstanceId, actionProperties = {}, objectProperties = {}):
        endpoint = "/me/actions.json"
        query_params = {
            'action_id': actionId,
            'action_properties': json.dumps(actionProperties, separators=(',',':')),
            'object_properties': json.dumps(objectProperties, separators=(',',':'))
        }
        if objectInstanceId != None:
            query_params.update({'object_instance_id': objectInstanceId})
        return self.postSignedRequest(userId, endpoint, query_params)

    def postLike(self, userId, like_object):
        endpoint = "/me/like.json"
        return self.postSignedRequest(userId, endpoint, {'object':like_object})

    def getTweet(self, userId, actionId, objectInstanceId, actionProperties = {}, objectProperties = {}):
        endpoint = "/me/tweet.json"
        query_params = {
            'action_id': actionId,
            'action_properties': json.dumps(actionProperties, separators=(',',':')),
            'object_properties': json.dumps(objectProperties, separators=(',',':'))
        }
        if objectInstanceId != None:
            query_params.update({'object_instance_id': objectInstanceId})
        return self.getSignedRequest(userId, endpoint, query_params)

    def postSignedRequest(self, userId, endpoint, query_params):
        return self.makeSignedRequest("POST", userId, endpoint, query_params)

    def getSignedRequest(self, userId, endpoint, query_params):
        return self.makeSignedRequest("GET", userId, endpoint, query_params)

    def makeSignedRequest(self, method, userId, endpoint, query_params):
        ret = Carrot.UNDETERMINED
        url_params = {
            'api_key': userId,
            'game_id': self.appId,
            'request_date': str(int(time.time())),
            'request_id': str(uuid.uuid4())
        }
        url_params.update(query_params)
        sorted_kv = sorted(url_params.items(), key=lambda x: x[0])
        url_string = '&'.join('='.join(kv) for kv in sorted_kv)
        sign_string = method + "\n" + self.hostname.partition(":")[0] + "\n" + endpoint + "\n" + url_string
        dig = hmac.new(key = self.appSecret, msg = sign_string, digestmod = hashlib.sha256).digest()

        url_string = '&'.join('='.join([kv[0], urllib.quote_plus(kv[1])]) for kv in sorted_kv) + "&sig=" + urllib.quote_plus(base64.encodestring(dig).strip())
        headers = {"Content-type": "application/x-www-form-urlencoded"}
        conn = self.getHttpCon()
        conn.connect()
        conn.request(method, endpoint, url_string, headers)
        response = conn.getresponse()
        if response.status == 201 or response.status == 200:
            ret = Carrot.AUTHORIZED
        elif response.status == 401:
            ret = Carrot.READ_ONLY
        elif response.status == 405:
            ret = Carrot.NOT_AUTHORIZED
        else:
            sys.stderr.write("Error posting signed request to Carrot (" + str(response.status) + "):" + response.read() + "\n")
        conn.close()
        if method == "GET" and ret == Carrot.AUTHORIZED:
            return response.read()
        else:
            return ret
