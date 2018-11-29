import httplib, urllib, json, webbrowser, urlparse, os, hashlib, base64
from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer

CLIENT_ID       = "NL8IZo82T84ZCOruAZom4LlmrzkQFXPW"
CLIENT_SECRET   = "5RNNKjqAAA1szIImP0CO2IFNC6Z8OoBMQeiMKwwoxST7ntSFJhIQKVG1s1DEbLOV"
REDIRECT_URI    = "http://localhost"
PORT_NUMBER     = 80
BROWSER_CLOSE_WINDOW = '''<!DOCTYPE html> 
                        <html> 
                                <script type="text/javascript"> 
                                    function close_window() { close(); }
                                </script>
                            <body onload="close_window()"/>
                        </html>'''
server = None
urlDict2 = None
data = {}
code_verifier = base64.b64encode(os.urandom(64))
# print code_verifier
code_challenge = base64.b64encode(hashlib.sha256(code_verifier).digest())[:-1]
# print code_challenge

#1. Logging in with access token
def read_access_token():
    with open('access_token.txt', 'r') as codeFile:
        access_token = codeFile.read()
    codeFile.close()

    with open('token_type.txt', 'r') as codeFile:
        token_type = codeFile.read()
    codeFile.close()

    return access_token, token_type

#2. If access token doesn't work, try refresh_token
def get_access_token_from_refresh_token(client_id, client_secret):
    with open('refresh_token.txt', 'r') as codeFile:
        refresh_token = codeFile.read()
    codeFile.close()

    conn = httplib.HTTPSConnection("www.wrike.com")
    urlDict = urllib.urlencode({"client_id":     client_id,
                                "client_secret": client_secret,
                                "grant_type": "refresh_token",
                                "refresh_token": refresh_token, })
    headers = {"Content-type": "application/x-www-form-urlencoded", }
    conn.request("POST", "/oauth2/token", urlDict, headers)
    response = conn.getresponse()
    if response.status == httplib.UNAUTHORIZED:
        access_token, token_type = get_token()
    else:
        rjson = json.load(response)
        access_token = rjson['access_token']
    print access_token
    print response
    with open('access_token.txt', 'w') as codeFile:
        codeFile.write(access_token)
    codeFile.close()
    return access_token

#3. Logging in explicitely
def get_token():
    global server

    authorizePath = '/identity/connect/authorize'
    urlDict = urllib.urlencode({"client_id"             : CLIENT_ID,
                                "response_type"         : "code",
                                "redirect_uri"          : REDIRECT_URI,
                                "scope"                 : "admin admin.brand",
                                # "scope"                 : "search_api search_api_downloadbinary",
                                "code_challenge"        : code_challenge,
                                "code_challenge_method" : "S256",
                                "state"                 : "1",
                                })

    ue = urlparse.urlunparse(('https',
                                'accounts.bimobject.com',
                                authorizePath,
                                '',
                                urlDict,
                                '', ))
    print "ue " + ue
    webbrowser.open(ue)
    server = HTTPServer(('', PORT_NUMBER), myHandler)

    try:
        server.serve_forever()
    except IOError:
        pass

    urlDict2 = urllib.urlencode({"client_id"        : CLIENT_ID,
                                 "client_secret"    : CLIENT_SECRET,
                                 "grant_type"       : "authorization_code",
                                 # "grant_type"       : "client_credentials_for_admin",
                                 "code"             : data['code'],
                                 "code_verifier"    : code_verifier,
                                 "redirect_uri"     : REDIRECT_URI, })

    print urlDict2

    headers = {"Content-type": "application/x-www-form-urlencoded", }
    conn = httplib.HTTPSConnection("accounts.bimobject.com")
    # conn.request("POST", "/identity/connect/token", urlDict2, headers)
    conn.request("POST", "/identity/connect/authorize", urlDict2, headers)
    response = conn.getresponse().read()
    print "response: " + response

    access_token  = json.loads(response)['access_token']
    # refresh_token = json.loads(response)['refresh_token']
    token_type    = json.loads(response)['token_type']

    with open('access_token.txt', 'w') as codeFile:
        codeFile.write(access_token)
    codeFile.close()

    # with open('refresh_token.txt', 'w') as codeFile:
    #     codeFile.write(refresh_token)
    # codeFile.close()

    with open('token_type.txt', 'w') as codeFile:
        codeFile.write(token_type)
    codeFile.close()

    return access_token, token_type


class myHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        global data
        self.wfile.write(BROWSER_CLOSE_WINDOW)
        data = urlparse.parse_qs(urlparse.urlparse(self.path).query)
        data = dict([(i, data[i][0]) if data[i] else (i, '') for i in data])
        print data['code']

        server.server_close()
        with open('code.txt', 'w') as codeFile:
            codeFile.write(data['code'])
        codeFile.close()


#TODO try: and def
access_token, token_type = read_access_token()
print 1
conn = httplib.HTTPSConnection("api.bimobject.com")
urlDict = urllib.urlencode({})
headers = {"Content-type": "application/x-www-form-urlencoded",
           "Authorization": token_type + " " + access_token}
conn.request("GET", "/admin/v1/brands", urlDict, headers)
# conn.request("GET", "/search/v1/products", urlDict, headers)
response = conn.getresponse()
print response.read()
print response.status, response.reason
# print json.load(response)

if response.status == 401:
    access_token, token_type = get_token()
    print 2
    conn = httplib.HTTPSConnection("api.bimobject.com")
    urlDict = urllib.urlencode({})
    headers = {"Content-type": "application/x-www-form-urlencoded",
               "Authorization": token_type + " " + access_token}
    conn.request("GET", "/admin/v1/brands", urlDict, headers)
    # conn.request("GET", "/search/v1/products", urlDict, headers)
    response = conn.getresponse()
    # print json.load(response)
    print response.read()


########################################################################################################################
########################################################################################################################
########################################################################################################################

# params = urllib.urlencode({ 'grant_type': 'client_credentials',
#                             'scope': 'search_api',
#                             'client_id': 'NL8IZo82T84ZCOruAZom4LlmrzkQFXPW',
#                             'client_secret': '5RNNKjqAAA1szIImP0CO2IFNC6Z8OoBMQeiMKwwoxST7ntSFJhIQKVG1s1DEbLOV'})
#
# headers = {"Content-type": "application/x-www-form-urlencoded", }
#
# conn = httplib.HTTPSConnection("accounts.bimobject.com")
# conn.request("POST", "/identity/connect/token", params, headers)
# response = conn.getresponse()
#
# data = json.loads(response.read())
#
# headers = {'Authorization':  data['token_type'] + ' ' + data['access_token'], }
#
# hasNext = True
# page = 1
# pageSize = 1000

# params = urllib.urlencode({ 'API': 'ac4e5af2-7544-475c-907d-c7d91c810039',
#                             'Objects': {'ProductId': 'https://bimobject.com/k-line/product/klgt-apd'}})
# headers = {"Content-type": "application/x-www-form-urlencoded"}
# # headers = {'Content-Type': 'application/xml'}
#
# _xml = "<?xml version='1.0' encoding='UTF-8'?><Bim API='ac4e5af2-7544-475c-907d-c7d91c810039'><Objects><Object ProductId='modartdesign.bimobject.com/13131' /></Objects></Bim>"
#
# conn = httplib.HTTPConnection("api.bimobject.com")
# conn.request("POST", "/GetBimObjectInfoXml2", _xml, headers)
# response = conn.getresponse()
#
# print response.read()
#

# request = urllib2.Request("https://api.bimobject.com/GetBimObjectInfoXml2", _xml)
#
# data = urllib2.urlopen(request).read()
#
# print data

# data = json.loads(response.read())
# print data

#
# while hasNext:
#     request = urllib2.Request("https://api.bimobject.com/search/v1/products/?page=" + str(page) + "&pageSize=" + str(pageSize), headers=headers)
#     data = json.loads(urllib2.urlopen(request).read())
#     hasNext = data['meta']['hasNextPage']
#     print hasNext
#
#     for a in data['data']:
#         print a['permalink']
#         # if a['permalink'] == 'S_36000_Series_See_Through_Designer_Wood_Lockers_Box_Style_1_Wide':
#         if a['permalink'] == 'klgt-apd':
#             print a['id']
#             print a
#             id = a['id']
#             for k in a.keys():
#                 print k, a[k]
#             hasNext = False
#             break
#     print "*", page, hasNext
#     page += 1



# request = urllib2.Request("https://api.bimobject.com/search/v1/products/?filter.brand.id=" + id, headers=headers)

# request = urllib2.Request("https://api.bimobject.com/search/v1/products/filters/brands", headers=headers)
# print data
# data = json.loads(urllib2.urlopen(request).read())
# print data['data'][0]['id']

