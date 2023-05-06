"""
Test for recipe api
"""
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from rest_framework import status
from rest_framework.test import APIClient

from core.models import Recipe

from recipe.serializers import (
    RecipeSerializer,
    RecipeDetailSerializer,
)

RECIPE_URL = reverse('recipe:recipe-list')

def detail_url(recipe_id):
    """ Create and return recipe detail URL """
    return reverse('recipe:recipe-detail', args=[recipe_id])

def create_recipe(user, **params):
    """ Create and return a sample recipe """
    defaults = {
        'title': 'Sample Recipe',
        'time_minutes': 5,
        'price': Decimal('5.50'),
        'description': 'Sample recipe description',
        'link': 'http://example.com/recipe.png'
    }
    defaults.update(params)

    recipe = Recipe.objects.create(user=user, **defaults)
    return recipe

class PublicRecipeAPITests(TestCase):
    """ Test unauthenticated API requests """

    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        """ Test auth is required to call API """
        res = self.client.get(RECIPE_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

def create_user(**params):
    """ create user """
    return get_user_model().objects.create_user(**params)

class PrivateRecipeAPITests(TestCase):
    """ Test authenticated API requests """

    def setUp(self):
        self.client = APIClient()
        self.user = create_user(email='user@example.com',password='testpass123')
        self.client.force_authenticate(self.user)

    def test_retrieve_recipes(self):
        """ Test retrieve list of receips """
        create_recipe(user=self.user)
        create_recipe(user=self.user)

        res = self.client.get(RECIPE_URL)

        recipes = Recipe.objects.all().order_by('-id')
        serializer = RecipeSerializer(recipes, many=True)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_recipe_list_limited_to_user(self):
        """ Test retrieve list of receips to limited user """
        other_user = create_user(email='user1@example.com',password='testpass123')
        create_recipe(user=other_user)
        create_recipe(user=self.user)

        res = self.client.get(RECIPE_URL)

        recipes = Recipe.objects.filter(user=self.user).order_by('-id')
        serializer = RecipeSerializer(recipes, many=True)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)
    
    def test_get_recipe_detail(self):
        """ Test get recipe details """
        recipe = create_recipe(user=self.user)

        url = detail_url(recipe.id)
        res = self.client.get(url)

        serializer = RecipeDetailSerializer(recipe)
        self.assertEqual(res.data, serializer.data)
        
    def test_create_recipe(self):
        """ Test create recipe """
        payload = {
            'title': 'Sample Recipe',
            'time_minutes': 5,
            'price': Decimal('5.50'),
        }
        res = self.client.post(RECIPE_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        recipe = Recipe.objects.get(id=res.data['id'])
        for key, value in payload.items():
            self.assertEqual(getattr(recipe, key), value)
        self.assertEqual(recipe.user, self.user)
    
    def test_partial_update(self):
        """ test partial update in recipe """
        original_link = 'http://example.com/recipe.png'
        recipe = create_recipe(
            user=self.user,
            title='Sample Recipe',
            link=original_link
        )
        payload = {'title': 'New sample title'}
        url = detail_url(recipe.id)
        res = self.client.patch(url, payload)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        recipe.refresh_from_db()
        self.assertEqual(recipe.title, payload['title'])
        self.assertEqual(recipe.user, self.user)
        self.assertEqual(recipe.link, original_link)

    def test_full_update(self):
        """ test full update in recipe """
        recipe = create_recipe(
            user=self.user,
            title='Sample Recipe',
            link='http://example.com/recipe.png',
            description='Sample recipe description'
        )
        payload = {
            'title': 'New sample title',
            'link': 'http://example.com/newrecipe.png',
            'description': 'New sample recipe description',
            'time_minutes': 13,
            'price': Decimal('12.32')
        }
        url = detail_url(recipe.id)
        res = self.client.put(url, payload)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        recipe.refresh_from_db()
        for k, v in payload.items():
            self.assertEqual(getattr(recipe, k), v)
        self.assertEqual(recipe.user, self.user)

    def test_update_user_returns_error(self):
        """ test changing recipe user results an error """
        new_user = create_user(email="test2@example.com", password="testpass123")
        recipe = create_recipe(user=self.user)

        payload = {'user': new_user.id}
        url = detail_url(recipe.id)
        self.client.patch(url, payload)

        recipe.refresh_from_db()
        self.assertEqual(recipe.user, self.user)

    def test_delete_recipe(self):
        """ test deleting recipe """
        recipe = create_recipe(user=self.user)

        url = detail_url(recipe.id)
        res = self.client.delete(url)

        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Recipe.objects.filter(id=recipe.id).exists())
        
        
    def test_recipe_other_users_recipe_error(self):
        """ test deleting recipe of other user results an error """
        new_user = create_user(email="test2@example.com", password="testpass123")
        recipe = create_recipe(user=new_user)

        url = detail_url(recipe.id)
        res = self.client.delete(url)

        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)
        self.assertTrue(Recipe.objects.filter(id=recipe.id).exists())