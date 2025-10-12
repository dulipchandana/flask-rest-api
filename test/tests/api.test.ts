import { test, expect } from '@playwright/test';
import axios from 'axios';

const API_URL = 'http://localhost:5000/api';

test.describe('User API Tests', () => {
  let userId: number;
  let testUsername: string;
  let testEmail: string;

  function generateRandomUser() {
    const timestamp = new Date().getTime();
    const random = Math.floor(Math.random() * 10000);
    return {
      username: `testuser_${timestamp}_${random}`,
      email: `testuser_${timestamp}_${random}@example.com`
    };
  }

  test.beforeAll(async () => {
    console.log('Setting up: Clearing existing data...');
    try {
      // Soft delete all existing users
      const response = await axios.get(`${API_URL}/users`);
      for (const user of response.data) {
        console.log(`Soft deleting user ${user.id}...`);
        await axios.delete(`${API_URL}/users/${user.id}`);
      }
      
      // Verify cleanup
      const afterDelete = await axios.get(`${API_URL}/users`);
      if (afterDelete.data.length === 0) {
        console.log('Database cleared successfully');
      } else {
        console.warn(`Warning: ${afterDelete.data.length} active users remain`);
      }
    } catch (error: any) {
      if (error.response?.status === 404) {
        console.log('No users to clean up');
      } else {
        console.error('Error during database cleanup:', error.message);
      }
    }
  });

  test('should create and manage users', async () => {
    // 1. Create a new user with random credentials
    const { username, email } = generateRandomUser();
    testUsername = username;
    testEmail = email;
    console.log(`Creating new user with username: ${username}, email: ${email}`);
    
    let response = await axios.post(`${API_URL}/users`, {
      username: testUsername,
      email: testEmail
    });
    
    expect(response.status).toBe(201);
    expect(Array.isArray(response.data)).toBeTruthy();
    expect(response.data[0]).toBeDefined();
    userId = response.data[0].id;
    console.log('Created user with ID:', userId);

    // 2. Get all users
    console.log('Getting all users...');
    response = await axios.get(`${API_URL}/users`);
    expect(response.status).toBe(200);
    expect(Array.isArray(response.data)).toBeTruthy();
    expect(response.data.length).toBeGreaterThan(0);
    console.log('Found users:', response.data.length);

    // 3. Get specific user
    console.log('Getting specific user:', userId);
    response = await axios.get(`${API_URL}/users/${userId}`);
    expect(response.status).toBe(200);
    expect(response.data.id).toBe(userId);
    expect(response.data.username).toBe(testUsername);
    expect(response.data.email).toBe(testEmail);
    console.log('Retrieved user:', response.data);

    // 4. Update user with new random credentials
    const { username: newUsername, email: newEmail } = generateRandomUser();
    console.log(`Updating user ${userId} with username: ${newUsername}, email: ${newEmail}`);
    response = await axios.put(`${API_URL}/users/${userId}`, {
      username: newUsername,
      email: newEmail
    });
    expect(response.status).toBe(200);
    expect(response.data.username).toBe(newUsername);
    expect(response.data.email).toBe(newEmail);
    console.log('Updated user:', response.data);

    // 5. Delete user
    console.log('Deleting user:', userId);
    response = await axios.delete(`${API_URL}/users/${userId}`);
    expect(response.status).toBe(204);

    // 6. Verify deletion
    response = await axios.get(`${API_URL}/users`);
    const deletedUser = response.data.find((user: any) => user.id === userId);
    expect(deletedUser).toBeUndefined();
    console.log('User successfully deleted');
  });

  test('should handle non-existent user', async () => {
    try {
      await axios.get(`${API_URL}/users/999999`);
      // If we get here, the test should fail because we expected a 404
      expect(false).toBe(true);
    } catch (error: any) {
      expect(error.response.status).toBe(404);
      expect(error.response.data.message).toBe('Could not find user with that id');
    }
  });

  test('should handle duplicate usernames and emails', async () => {
    // Create first user
    const { username, email } = generateRandomUser();
    let response = await axios.post(`${API_URL}/users`, {
      username,
      email
    });
    expect(response.status).toBe(201);
    
    // Try to create another user with same username and email
    try {
      await axios.post(`${API_URL}/users`, {
        username,
        email
      });
      expect(false).toBe(true); // Should not reach here
    } catch (error: any) {
      expect(error.response.status).toBe(400);
      expect(error.response.data.message).toContain('already exists');
    }

    // Clean up
    const userId = response.data[0].id;
    await axios.delete(`${API_URL}/users/${userId}`);
  });
});