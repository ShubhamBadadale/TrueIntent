from fastapi.testclient import TestClient

from api.main import app


client = TestClient(app)


def test_compile_success():
    source = 'cloud app "A" { network "main" { cidr = "10.0.0.0/16" } }'
    response = client.post("/api/compile", json={"source": source, "target": "aws"})
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert 'resource "aws_vpc" "main"' in body["generated"]["aws"]
    assert body["ast"]["type"] == "CloudApp"
    assert body["ir"]["nodes"][0]["id"] == "network.main"


def test_compile_user_error_is_200():
    source = 'cloud app "A" { compute "web" { image = ${missing} cpu = 1 memory = 1 } }'
    response = client.post("/api/compile", json={"source": source, "target": "aws"})
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is False
    assert any(d["code"] == "E202" for d in body["diagnostics"])


def test_examples_endpoint():
    response = client.get("/api/examples")
    assert response.status_code == 200
    assert [item["name"] for item in response.json()] == [
        "static_web_server",
        "negative_unsupported_resource",
    ]


def test_malformed_request_is_422():
    response = client.post("/api/compile", json={"source": "", "target": "aws"})
    assert response.status_code == 422
