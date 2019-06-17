

def test_empty_list_merchant_transactions(client):
    response = client.get("/merchants/23")
    assert response.status_code == 200
    assert response.json == "No transactions found."


def test_list_merchant_transactions(client):
    response = client.get("/merchants/40")
    assert response.status_code == 200
    assert len(response.json) != 0


def test_merchant_average_basket(client):
    response = client.get("/merchants/40/average")
    assert response.status_code == 200
    # assert response.json == 50.159662


def test_merchant_average_basket_per_month(client):
    response = client.get("/merchants/40/average/2019/06")
    assert response.status_code == 200
    # assert response.json == 50.250841
