"""
Test for user api
"""
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse

from rest_framework.test import APIClient
from rest_framework import status

CREATE_USER_URL = reverse('user:create')
TOKEN_URL = reverse('user:token')

def create_user(**params):
    """ Create and return new user """
    return get_user_model().objects.create_user(**params)

class PublicUserApiTest(TestCase):
    """ Test the public features of the user API """

    def setUp(self):
        self.client = APIClient()

    def test_create_user_success(self):
        """ Test creating new user """ 
        payload = {
            'email': 'tester@example.com',
            'password': 'Passwd123',
            'name': 'Test User',
        }  
        res = self.client.post(CREATE_USER_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        user = get_user_model().objects.get(email=payload['email'])
        matches_password = user.check_password(payload['password'])
        self.assertTrue(matches_password)
        self.assertNotIn('password', res.data)

    def test_user_with_email_exists_error(self):
        """ Test error return if email exists """
        payload = {
            'email': 'tester@example.com',
            'password': 'Passwd123',
            'name': 'Test User',
        }  
        create_user(**payload)
        res = self.client.post(CREATE_USER_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_password_too_short_error(self):
        """ Test an error if password is less than 5 char """
        payload = {
            'email': 'tester@example.com',
            'password': 'test',
            'name': 'Test User',
        }  
        res = self.client.post(CREATE_USER_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        user_exists = get_user_model().objects.filter(
            email=payload['email']
        ).exists()
        self.assertFalse(user_exists)
    
    def test_token_for_user(self):
        """ Test generates token for valid credintials """
        user_details = {
            'email': 'tester@example.com',
            'password': 'Passwd123',
            'name': 'Test User',
        } 
        create_user(**user_details)
        payload = {
            'email': user_details['email'],
            'password': user_details['password']
        }
        res = self.client.post(TOKEN_URL, payload)
        self.assertIn('token', res.data)
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_create_token_bad_credentials(self):
        """ Test generates error for invalid credintials """
        user_details = {
            'email': 'tester@example.com',
            'password': 'Passwd123',
            'name': 'Test User',
        } 
        create_user(**user_details)
        payload = {
            'email': user_details['email'],
            'password': 'pass123'
        }
        res = self.client.post(TOKEN_URL, payload)
        self.assertNotIn('token', res.data)
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_token_blank_password(self):
        """ Test generates error for blank password """
        payload = {
            'email': 'bishaltest@example.com',
            'password': ''
        }
        res = self.client.post(TOKEN_URL, payload)
        self.assertNotIn('token', res.data)
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
