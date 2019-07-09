

def test_operator(client):
    rv = client.post('/api/v1/operator/init')
    assert rv.data.decode('utf-8') == 'Hello'
