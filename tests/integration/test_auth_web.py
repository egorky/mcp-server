import pytest
from flask import url_for, session
from werkzeug.security import generate_password_hash

# Note: app_config fixture in conftest.py sets web_auth.password_hash to hash of 'testpass'
# and username to 'testuser'

def test_login_page_loads(client, initialized_app_for_test):
    response = client.get(url_for('login'))
    assert response.status_code == 200
    assert b"Login</h2>" in response.data

def test_successful_login_logout(client, initialized_app_for_test, app_config):
    # Login
    login_response = client.post(url_for('login'), data={
        'username': app_config['web_auth']['username'], # 'testuser'
        'password': 'testpass' # Plaintext password for the test
    }, follow_redirects=True)

    assert login_response.status_code == 200
    assert b"Login successful!" in login_response.data # Flash message
    assert b"MCP Tool Dashboard" in login_response.data # On dashboard

    # Check session
    with client.session_transaction() as sess:
        assert sess['logged_in'] is True
        assert sess['username'] == app_config['web_auth']['username']

    # Access dashboard directly
    dashboard_response = client.get(url_for('dashboard'))
    assert dashboard_response.status_code == 200
    assert b"MCP Tool Dashboard" in dashboard_response.data

    # Logout
    logout_response = client.get(url_for('logout'), follow_redirects=True)
    assert logout_response.status_code == 200
    assert b"You have been logged out." in logout_response.data # Flash message
    assert b"Login</h2>" in logout_response.data # Back to login page

    with client.session_transaction() as sess:
        assert 'logged_in' not in sess

def test_login_invalid_username(client, initialized_app_for_test):
    response = client.post(url_for('login'), data={
        'username': 'wronguser',
        'password': 'testpass'
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b"Invalid username or password." in response.data
    assert b"Login</h2>" in response.data # Still on login page

def test_login_invalid_password(client, initialized_app_for_test, app_config):
    response = client.post(url_for('login'), data={
        'username': app_config['web_auth']['username'],
        'password': 'wrongpassword'
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b"Invalid username or password." in response.data

def test_dashboard_access_requires_login(client, initialized_app_for_test):
    response = client.get(url_for('dashboard'), follow_redirects=True)
    assert response.status_code == 200 # Redirects to login
    assert b"Please log in to access this page." in response.data # Flash message
    assert b"Login</h2>" in response.data # On login page

def test_root_redirects_to_login_if_not_logged_in(client, initialized_app_for_test):
    response = client.get(url_for('index_redirect'), follow_redirects=True)
    assert response.status_code == 200
    assert b"Please log in to access this page." in response.data
    assert b"Login</h2>" in response.data

def test_root_redirects_to_dashboard_if_logged_in(client, initialized_app_for_test, app_config):
    # Log in first
    client.post(url_for('login'), data={
        'username': app_config['web_auth']['username'],
        'password': 'testpass'
    })
    response = client.get(url_for('index_redirect'), follow_redirects=True)
    assert response.status_code == 200
    assert b"MCP Tool Dashboard" in response.data

    # Clean up session for other tests
    client.get(url_for('logout'))
