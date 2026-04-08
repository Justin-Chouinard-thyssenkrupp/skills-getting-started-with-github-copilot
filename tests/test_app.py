"""Tests for the FastAPI application endpoints

Uses the Arrange-Act-Assert (AAA) pattern for clear test structure:
- Arrange: Set up test data and conditions
- Act: Execute the code being tested
- Assert: Verify the results
"""

import pytest


class TestRootEndpoint:
    """Tests for the root endpoint"""

    def test_root_redirect(self, client):
        """Test that root path redirects to static/index.html"""
        # Arrange
        # No setup needed - we're testing the default route behavior

        # Act
        response = client.get("/", follow_redirects=False)

        # Assert
        assert response.status_code == 307
        assert response.headers["location"] == "/static/index.html"


class TestActivitiesEndpoint:
    """Tests for GET /activities endpoint"""

    def test_get_all_activities(self, client):
        """Test retrieving all activities"""
        # Arrange
        expected_activities = ["Chess Club", "Programming Class", "Gym Class"]

        # Act
        response = client.get("/activities")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)
        for activity in expected_activities:
            assert activity in data

    def test_activities_have_required_fields(self, client):
        """Test that each activity has required fields"""
        # Arrange
        required_fields = ["description", "schedule", "max_participants", "participants"]

        # Act
        response = client.get("/activities")
        data = response.json()

        # Assert
        for activity_name, activity_data in data.items():
            for field in required_fields:
                assert field in activity_data, f"Missing {field} in {activity_name}"
            assert isinstance(activity_data["participants"], list)

    def test_initial_participants_populated(self, client):
        """Test that activities start with initial participants"""
        # Arrange
        expected_chess_club_participants = ["michael@mergington.edu", "daniel@mergington.edu"]
        expected_basketball_participants = ["alex@mergington.edu"]

        # Act
        response = client.get("/activities")
        data = response.json()

        # Assert
        assert len(data["Chess Club"]["participants"]) == 2
        assert all(p in data["Chess Club"]["participants"] for p in expected_chess_club_participants)
        assert len(data["Basketball Team"]["participants"]) == 1
        assert expected_basketball_participants[0] in data["Basketball Team"]["participants"]


class TestSignupEndpoint:
    """Tests for POST /activities/{activity_name}/signup endpoint"""

    def test_successful_signup(self, client):
        """Test successfully signing up for an activity"""
        # Arrange
        activity_name = "Chess Club"
        email = "newstudent@mergington.edu"

        # Act
        response = client.post(
            f"/activities/{activity_name}/signup",
            params={"email": email}
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert email in data["message"]
        
        # Verify participant was added
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        assert email in activities_data[activity_name]["participants"]

    def test_signup_nonexistent_activity(self, client):
        """Test signing up for an activity that doesn't exist"""
        # Arrange
        nonexistent_activity = "Nonexistent Club"
        email = "student@mergington.edu"

        # Act
        response = client.post(
            f"/activities/{nonexistent_activity}/signup",
            params={"email": email}
        )

        # Assert
        assert response.status_code == 404
        data = response.json()
        assert "Activity not found" in data["detail"]

    def test_signup_already_registered(self, client):
        """Test signing up when already registered for an activity"""
        # Arrange
        activity_name = "Chess Club"
        email = "michael@mergington.edu"  # Already registered

        # Act
        response = client.post(
            f"/activities/{activity_name}/signup",
            params={"email": email}
        )

        # Assert
        assert response.status_code == 400
        data = response.json()
        assert "Student already signed up" in data["detail"]

    def test_signup_multiple_activities_allowed(self, client):
        """Test that a student can sign up for multiple activities"""
        # Arrange
        email = "multistudent@mergington.edu"
        first_activity = "Chess Club"
        second_activity = "Basketball Team"

        # Act - Sign up for first activity
        response1 = client.post(
            f"/activities/{first_activity}/signup",
            params={"email": email}
        )
        # Act - Sign up for second activity
        response2 = client.post(
            f"/activities/{second_activity}/signup",
            params={"email": email}
        )

        # Assert
        assert response1.status_code == 200
        assert response2.status_code == 200
        
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        assert email in activities_data[first_activity]["participants"]
        assert email in activities_data[second_activity]["participants"]

    def test_signup_with_special_characters_in_email(self, client):
        """Test signup with special characters in email"""
        # Arrange
        email = "student+test@mergington.edu"
        activity_name = "Chess Club"

        # Act
        response = client.post(
            f"/activities/{activity_name}/signup",
            params={"email": email}
        )

        # Assert
        assert response.status_code == 200
        
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        assert email in activities_data[activity_name]["participants"]


class TestUnregisterEndpoint:
    """Tests for DELETE /activities/{activity_name}/participants endpoint"""

    def test_successful_unregister(self, client):
        """Test successfully unregistering from an activity"""
        # Arrange
        activity_name = "Chess Club"
        email = "michael@mergington.edu"  # Already registered

        # Act
        response = client.delete(
            f"/activities/{activity_name}/participants",
            params={"email": email}
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert email in data["message"]
        
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        assert email not in activities_data[activity_name]["participants"]

    def test_unregister_nonexistent_activity(self, client):
        """Test unregistering from an activity that doesn't exist"""
        # Arrange
        nonexistent_activity = "Nonexistent Club"
        email = "student@mergington.edu"

        # Act
        response = client.delete(
            f"/activities/{nonexistent_activity}/participants",
            params={"email": email}
        )

        # Assert
        assert response.status_code == 404
        data = response.json()
        assert "Activity not found" in data["detail"]

    def test_unregister_participant_not_in_activity(self, client):
        """Test unregistering someone not registered for the activity"""
        # Arrange
        activity_name = "Chess Club"
        email = "notregistered@mergington.edu"  # Not registered

        # Act
        response = client.delete(
            f"/activities/{activity_name}/participants",
            params={"email": email}
        )

        # Assert
        assert response.status_code == 404
        data = response.json()
        assert "Participant not found" in data["detail"]

    def test_unregister_then_resign_up(self, client):
        """Test unregistering and then signing up again"""
        # Arrange
        email = "flexible@mergington.edu"
        activity = "Chess Club"

        # Act - Initial signup
        client.post(f"/activities/{activity}/signup", params={"email": email})

        # Act - Unregister
        unregister_response = client.delete(
            f"/activities/{activity}/participants",
            params={"email": email}
        )

        # Act - Sign up again
        signup_again_response = client.post(
            f"/activities/{activity}/signup",
            params={"email": email}
        )

        # Assert
        assert unregister_response.status_code == 200
        assert signup_again_response.status_code == 200
        
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        assert email in activities_data[activity]["participants"]

    def test_unregister_multiple_participants(self, client):
        """Test removing different participants from the same activity"""
        # Arrange
        activity = "Chess Club"
        participant_one = "michael@mergington.edu"
        participant_two = "daniel@mergington.edu"

        # Act - Unregister first participant
        response1 = client.delete(
            f"/activities/{activity}/participants",
            params={"email": participant_one}
        )

        # Act - Unregister second participant
        response2 = client.delete(
            f"/activities/{activity}/participants",
            params={"email": participant_two}
        )

        # Assert
        assert response1.status_code == 200
        assert response2.status_code == 200
        
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        assert len(activities_data[activity]["participants"]) == 0


class TestActivityCapacity:
    """Tests for activity capacity limits"""

    def test_signup_count_accuracy(self, client):
        """Test that participant counts are tracked correctly"""
        # Arrange
        activity = "Basketball Team"
        new_email = "newplayer@mergington.edu"

        initial_response = client.get("/activities")
        initial_count = len(initial_response.json()[activity]["participants"])

        # Act
        client.post(
            f"/activities/{activity}/signup",
            params={"email": new_email}
        )

        # Assert
        final_response = client.get("/activities")
        final_count = len(final_response.json()[activity]["participants"])
        assert final_count == initial_count + 1

    def test_unregister_count_accuracy(self, client):
        """Test that participant counts decrease correctly after unregister"""
        # Arrange
        activity = "Chess Club"
        participant_to_remove = "michael@mergington.edu"

        initial_response = client.get("/activities")
        initial_count = len(initial_response.json()[activity]["participants"])

        # Act
        client.delete(
            f"/activities/{activity}/participants",
            params={"email": participant_to_remove}
        )

        # Assert
        final_response = client.get("/activities")
        final_count = len(final_response.json()[activity]["participants"])
        assert final_count == initial_count - 1
