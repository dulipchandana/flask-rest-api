import pytest
from api import app, db, UserModel
import json

@pytest.fixture
def client():
    """Create a test client for the app."""
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['TESTING'] = True
    
    with app.test_client() as client:
        with app.app_context():
            db.create_all()
        yield client
        with app.app_context():
            db.drop_all()

def test_home_endpoint(client):
    """Test the home endpoint returns Hello, World!"""
    response = client.get('/')
    assert response.status_code == 200
    assert b'Hello, World!' in response.data

def test_create_user(client):
    """Test user creation endpoint"""
    response = client.post('/api/users', json={
        'username': 'testuser',
        'email': 'test@example.com'
    })
    assert response.status_code == 201
    data = json.loads(response.data)
    assert len(data) > 0
    assert data[0]['username'] == 'testuser'
    assert data[0]['email'] == 'test@example.com'

def test_create_duplicate_user(client):
    """Test creating user with duplicate username fails"""
    # Create first user
    client.post('/api/users', json={
        'username': 'testuser',
        'email': 'test@example.com'
    })
    
    # Try to create duplicate user
    response = client.post('/api/users', json={
        'username': 'testuser',
        'email': 'different@example.com'
    })
    assert response.status_code == 400
    assert b'already exists' in response.data

def test_get_users(client):
    """Test getting all users"""
    # Create a test user
    client.post('/api/users', json={
        'username': 'testuser',
        'email': 'test@example.com'
    })
    
    response = client.get('/api/users')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert len(data) > 0
    assert data[0]['username'] == 'testuser'

def test_get_specific_user(client):
    """Test getting a specific user"""
    # Create a test user
    response = client.post('/api/users', json={
        'username': 'testuser',
        'email': 'test@example.com'
    })
    user_id = json.loads(response.data)[0]['id']
    
    response = client.get(f'/api/users/{user_id}')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['username'] == 'testuser'
    assert data['email'] == 'test@example.com'

def test_get_nonexistent_user(client):
    """Test getting a user that doesn't exist"""
    response = client.get('/api/users/999')
    assert response.status_code == 404
    assert b'Could not find user' in response.data

def test_update_user(client):
    """Test updating a user"""
    # Create a test user
    response = client.post('/api/users', json={
        'username': 'testuser',
        'email': 'test@example.com'
    })
    user_id = json.loads(response.data)[0]['id']
    
    # Update the user
    response = client.put(f'/api/users/{user_id}', json={
        'username': 'updateduser',
        'email': 'updated@example.com'
    })
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['username'] == 'updateduser'
    assert data['email'] == 'updated@example.com'

def test_delete_user(client):
    """Test deleting a user (soft delete)"""
    # Create a test user
    response = client.post('/api/users', json={
        'username': 'testuser',
        'email': 'test@example.com'
    })
    user_id = json.loads(response.data)[0]['id']
    
    # Delete the user
    response = client.delete(f'/api/users/{user_id}')
    assert response.status_code == 204
    
    # Verify user is not returned in users list (soft deleted)
    response = client.get('/api/users')
    data = json.loads(response.data)
    assert len([user for user in data if user['id'] == user_id]) == 0

def test_update_nonexistent_user(client):
    """Test updating a user that doesn't exist"""
    response = client.put('/api/users/999', json={
        'username': 'updateduser',
        'email': 'updated@example.com'
    })
    assert response.status_code == 404
    assert b'Could not find user' in response.data

def test_delete_nonexistent_user(client):
    """Test deleting a user that doesn't exist"""
    response = client.delete('/api/users/999')
    assert response.status_code == 404
    assert b'Could not find user' in response.data

def test_create_user_missing_fields(client):
    """Test creating a user with missing required fields"""
    response = client.post('/api/users', json={
        'username': 'testuser'
        # missing email
    })
    assert response.status_code == 400
    assert b'required' in response.data.lower()

def test_create_user_duplicate_email(client):
    """Test creating a user with duplicate email"""
    # Create first user
    client.post('/api/users', json={
        'username': 'testuser1',
        'email': 'test@example.com'
    })
    
    # Try to create user with same email
    response = client.post('/api/users', json={
        'username': 'testuser2',
        'email': 'test@example.com'
    })
    assert response.status_code == 400
    assert b'already exists' in response.data