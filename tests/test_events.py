def test_landing_page(client):
    """Test landing page renders successfully."""
    response = client.get("/")
    assert response.status_code == 200
    assert b"TixGo" in response.data
    assert b"Book Your Happiness" in response.data
    assert b"IPL Grand Final" in response.data


def test_event_details(client):
    """Test event details page renders."""
    response = client.get("/events/1")
    assert response.status_code == 200
    assert b"IPL Grand Final" in response.data
    assert b"Chepauk" in response.data


def test_api_events_filter(client):
    """Test JSON events listing with category filter."""
    response = client.get("/api/events?category=Cricket")
    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    assert len(data["events"]) >= 1
    assert data["events"][0]["event_type"] == "Cricket"
