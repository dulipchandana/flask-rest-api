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
    assert 'username' in data
    assert data['username'] == 'testuser'
    assert data['email'] == 'test@example.com'

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
    post_response = client.post('/api/users', json={
        'username': 'testuser',
        'email': 'test@example.com'
    })
    user_data = json.loads(post_response.data)
    
    response = client.get('/api/users')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert len(data) > 0
    assert any(user['username'] == user_data['username'] for user in data)

def test_get_specific_user(client):
    """Test getting a specific user"""
    # Create a test user
    response = client.post('/api/users', json={
        'username': 'testuser',
        'email': 'test@example.com'
    })
    user_id = json.loads(response.data)['id']
    
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
    user_id = json.loads(response.data)['id']
    
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
    user_id = json.loads(response.data)['id']
    
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

def test_username_length_limit(client):
    """Test username length limit validation"""
    response = client.post('/api/users', json={
        'username': 'a' * 81,  # More than 80 characters
        'email': 'test@example.com'
    })
    assert response.status_code == 400
    assert b'String length exceeds' in response.data

def test_email_length_limit(client):
    """Test email length limit validation"""
    response = client.post('/api/users', json={
        'username': 'testuser',
        'email': ('a' * 115) + '@example.com'  # More than 120 characters
    })
    assert response.status_code == 400
    assert b'String length exceeds' in response.data

def test_invalid_json_payload(client):
    """Test handling of invalid JSON payload"""
    response = client.post('/api/users', 
        data='invalid json',
        content_type='application/json')
    assert response.status_code == 400
    assert b'Invalid JSON' in response.data

def test_response_headers(client):
    """Test API response headers"""
    response = client.get('/api/users')
    assert response.headers['Content-Type'] == 'application/json'
    
def test_bulk_user_operations(client):
    """Test creating and retrieving multiple users"""
    # Create multiple users and store their data
    created_users = []
    for i in range(5):
        response = client.post('/api/users', json={
            'username': f'testuser{i}', 
            'email': f'test{i}@example.com'
        })
        assert response.status_code == 201
        created_users.append(json.loads(response.data))
    
    # Verify all users are retrieved
    response = client.get('/api/users')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert len(data) == 5
    
    # Verify user data matches what we created
    for user in created_users:
        found = False
        for retrieved_user in data:
            if (retrieved_user['username'] == user['username'] and 
                retrieved_user['email'] == user['email']):
                found = True
                break
        assert found, f"Created user {user['username']} not found in retrieved users"

def test_user_model_repr():
    """Test the string representation of UserModel"""
    user = UserModel(username='testuser', email='test@example.com', status=True)
    expected_repr = "User(name = testuser', email = 'test@example.com'. status = 'True')"
    assert str(user) == expected_repr

def test_swagger_ui_endpoint(client):
    """Test the Swagger UI endpoint"""
    response = client.get('/api/docs/')
    assert response.status_code == 200
    assert b'swagger' in response.data.lower()

def test_swagger_yaml_endpoint(client):
    """Test the Swagger YAML endpoint"""
    response = client.get('/static/swagger.yaml')
    assert response.status_code == 200

def test_create_user_after_soft_delete(client):
    """Test creating a user with same username/email after soft delete"""
    # Create and delete first user
    response = client.post('/api/users', json={
        'username': 'testuser',
        'email': 'test@example.com'
    })
    user_id = json.loads(response.data)['id']
    client.delete(f'/api/users/{user_id}')
    
    # Create new user with same username/email
    response = client.post('/api/users', json={
        'username': 'testuser',
        'email': 'test@example.com'
    })
    assert response.status_code == 201

@pytest.fixture
def mock_db_error(monkeypatch):
    """Fixture to simulate database errors"""
    def mock_commit_error(*args, **kwargs):
        raise Exception("Database error")
    monkeypatch.setattr(db.session, 'commit', mock_commit_error)

def test_database_error_handling(client, mock_db_error):
    """Test handling of database errors during user creation"""
    response = client.post('/api/users', json={
        'username': 'testuser',
        'email': 'test@example.com'
    })
    assert response.status_code == 500
    assert b'Internal server error' in response.data