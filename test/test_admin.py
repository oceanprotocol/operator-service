from operator_service.constants import BaseURLs

API_URL = f"{BaseURLs.BASE_OPERATOR_URL}"


def test_admin(client, monkeypatch):
    monkeypatch.setenv(
        "ALLOWED_ADMINS", '["0x6d39a833d1a6789aeca50db85cb830bc08319f45"]'
    )

    # Test with the right admin
    headers = {"Admin": "0x6d39a833d1a6789aeca50db85cb830bc08319f45"}
    pgsql_init_response = client.post(f"{API_URL}/pgsqlinit", headers=headers)
    assert pgsql_init_response.status_code == 200
    assert "" in pgsql_init_response.text

    # Test with no headers
    pgsql_init_response = client.post(f"{API_URL}/pgsqlinit")
    assert pgsql_init_response.status_code == 400
    assert "Admin header is empty." in pgsql_init_response.text

    # Test with no allowed admin
    pgsql_init_response = client.post(f"{API_URL}/pgsqlinit", headers={})
    assert pgsql_init_response.status_code == 400
    assert "Admin header is empty." in pgsql_init_response.text

    # Test with foo admin
    headers = {"Admin": "foo_admin"}
    pgsql_init_response = client.post(f"{API_URL}/pgsqlinit", headers=headers)
    assert pgsql_init_response.status_code == 401
    assert (
        "Access admin route failed due to invalid admin address."
        in pgsql_init_response.text
    )
