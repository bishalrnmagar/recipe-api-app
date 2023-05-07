""" 
Tests for tags api
"""
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.test import TestCase

from rest_framework import status
from rest_framework.test import APIClient

from core.models import Tag

from recipe.serializers import TagSerializer

TAGS_URL = reverse('recipe:tag-list')

def detail_url(tag_id):
    """ Create and return tag detail URL """
    return reverse('recipe:tag-detail', args=[tag_id])

def create_user(email="test@example.com", password="testpass123"):
    """ Create and return a user """
    return get_user_model().objects.create_user(email, password)

class PublicTagsAPITest(TestCase):
    """ Test unauthorized API requests """

    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        """ test to check unauthorized user """
        res = self.client.get(TAGS_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

class PrivateTagsAPITest(TestCase):
    """ Test autorized API requests """

    def setUp(self):
        self.client = APIClient()
        self.user = create_user()
        self.client.force_authenticate(self.user)

    def test_retrieve_tags(self):
        """ Test retrieve list of tags """
        Tag.objects.create(user=self.user, name='Pork')
        Tag.objects.create(user=self.user, name='Buff')

        res = self.client.get(TAGS_URL)

        tags = Tag.objects.all().order_by('-name')
        serializer = TagSerializer(tags, many=True)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_tags_limited_to_user(self):
        """ Test list of tags limited to authenticate user """
        user2 = create_user("ram@email.com","ram12345")
        Tag.objects.create(user=user2, name='Sweets')
        tag = Tag.objects.create(user=self.user, name='Desert')

        res = self.client.get(TAGS_URL)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]['name'], tag.name)
        self.assertEqual(res.data[0]['id'], tag.id)
    
    def test_update_tag(self):
        """ Test update tags """
        tag = Tag.objects.create(user=self.user, name='Desert')

        payload = { 'name': 'Dessert' }
        url = detail_url(tag.id)
        res = self.client.patch(url, payload)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        tag.refresh_from_db()
        self.assertEqual(tag.name, payload['name'])

    def test_delete_tags(self):
        """ test deleting tags """
        tag = Tag.objects.create(user=self.user, name='Desert')

        url = detail_url(tag.id)
        res = self.client.delete(url)

        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Tag.objects.filter(id=tag.id).exists())


