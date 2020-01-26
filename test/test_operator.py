import json


def test_operator(client):
    rv = client.get('/')
    assert json.loads(rv.data.decode('utf-8'))['software'] == 'Operator service'


def test_start_compute_job(client):
    return


def test_stop_compute_job(client):
    return


def test_delete_compute_job(client):
    return


def test_get_compute_job_status(client):
    return
