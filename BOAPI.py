import httplib, urllib, urllib2, json
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
headers = {"Content-type": "application/x-www-form-urlencoded"}
# # headers = {'Content-Type': 'application/xml'}

_xml = "<?xml version='1.0' encoding='UTF-8'?><Bim API='ac4e5af2-7544-475c-907d-c7d91c810039'><Objects><Object ProductId='modartdesign.bimobject.com/13131' /></Objects></Bim>"

conn = httplib.HTTPConnection("api.bimobject.com")
conn.request("POST", "/GetBimObjectInfoXml2", _xml, headers)
response = conn.getresponse()

print response.read()
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

