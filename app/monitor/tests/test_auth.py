"""
Tests for the basic authentication wrapper in monitor views.
"""
import base64
import pytest
from django.test import RequestFactory
from django.http import HttpResponse

from app.monitor.views import basic_auth_required

@pytest.fixture
def factory():
    """Request factory fixture."""
    return RequestFactory()


@pytest.fixture
def test_view():
    """Simple test view function."""
    return lambda request: HttpResponse("Test view response")


@pytest.fixture
def decorated_view(test_view):
    """View function with basic auth decorator applied with explicit credentials."""
    return basic_auth_required(auth_user='testuser', auth_pass='testpass')(test_view)


@pytest.mark.parametrize('username,password,expected_status', [
    ('testuser', 'testpass', 200),  # Valid credentials
    ('testuser', 'wrongpass', 401),  # Invalid password
    ('wronguser', 'testpass', 401),  # Invalid username
])
def test_auth_with_credentials(factory, decorated_view, username, password, expected_status):
    """Test authentication with various credentials."""
    # Create auth header with credentials
    credentials = base64.b64encode(f'{username}:{password}'.encode('utf-8')).decode('utf-8')
    request = factory.get('/metrics/')
    request.META['HTTP_AUTHORIZATION'] = f'Basic {credentials}'
    
    # Call the decorated view
    response = decorated_view(request)
    
    # Check response status
    assert response.status_code == expected_status
    
    # Additional checks based on status
    if expected_status == 200:
        assert response.content.decode('utf-8') == "Test view response"
    else:
        assert response['WWW-Authenticate'] == 'Basic realm="Metrics Authentication"'


def test_missing_auth_header(factory, decorated_view):
    """Test that missing auth header returns 401 Unauthorized."""
    request = factory.get('/metrics/')
    
    # Call the decorated view
    response = decorated_view(request)
    
    # Check that we got a 401 Unauthorized response
    assert response.status_code == 401
    assert response['WWW-Authenticate'] == 'Basic realm="Metrics Authentication"'


def test_malformed_auth_header(factory, decorated_view):
    """Test that malformed auth header returns 401 Unauthorized."""
    request = factory.get('/metrics/')
    request.META['HTTP_AUTHORIZATION'] = 'NotBasic abc123'
    
    # Call the decorated view
    response = decorated_view(request)
    
    # Check that we got a 401 Unauthorized response
    assert response.status_code == 401
    assert response['WWW-Authenticate'] == 'Basic realm="Metrics Authentication"'


def test_malformed_credentials(factory, decorated_view):
    """Test that malformed credentials return 401 Unauthorized."""
    # Create auth header with malformed credentials (not username:password)
    credentials = base64.b64encode(b'malformedcredentials').decode('utf-8')
    request = factory.get('/metrics/')
    request.META['HTTP_AUTHORIZATION'] = f'Basic {credentials}'
    
    # Call the decorated view
    response = decorated_view(request)
    
    # Check that we got a 401 Unauthorized response
    assert response.status_code == 401


def test_no_credentials_configured(factory, test_view):
    """Test that authentication is skipped if no credentials are configured."""
    # Create a decorated view with empty credentials
    view_with_empty_creds = basic_auth_required(auth_user='', auth_pass='')(test_view)
    
    request = factory.get('/metrics/')
    
    # Call the decorated view
    response = view_with_empty_creds(request)
    
    # Check that we got the expected response from the test view (auth skipped)
    assert response.status_code == 200
    assert response.content.decode('utf-8') == "Test view response"


def test_incomplete_credentials_configured(factory, test_view):
    """Test that authentication is skipped if credentials are incomplete."""
    # Create a decorated view with incomplete credentials
    view_with_incomplete_creds = basic_auth_required(auth_user='testuser', auth_pass='')(test_view)
    
    request = factory.get('/metrics/')
    
    # Call the decorated view
    response = view_with_incomplete_creds(request)
    
    # Check that we got the expected response from the test view (auth skipped)
    assert response.status_code == 200
    assert response.content.decode('utf-8') == "Test view response" 