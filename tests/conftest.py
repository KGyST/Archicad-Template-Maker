def pytest_collection_modifyitems(items):
    for item in items:
        if 'Note' in item._request.node.callspec.params['inTestCase'] and item._request.node.callspec.params['inTestCase']['Note']:
            item._nodeid = item._request.node.callspec.params['inTestCase']['Note'] + '::' + item._request.node.callspec.params['inTestCase']['fileName']
        else:
            item._nodeid = item._request.node.callspec.params['inTestCase']['fileName'] + '::' + item._request.node.callspec.params['inTestCase']['fileName']
