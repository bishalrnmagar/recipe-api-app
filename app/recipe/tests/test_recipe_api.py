"""
Test for recipe api
"""
from decimal import Decimal
import tempfile
import os

from PIL import Image

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from rest_framework import status
from rest_framework.test import APIClient

from core.models import Recipe, Tag, Ingredient

from recipe.serializers import (
    RecipeSerializer,
    RecipeDetailSerializer,
    IngredientSerializer
)

RECIPE_URL = reverse('recipe:recipe-list')

def detail_url(recipe_id):
    """ Create and return recipe detail URL """
    return reverse('recipe:recipe-detail', args=[recipe_id])

def image_upload_url(recipe_id):
    """ create and return image upload url """
    return reverse('recipe:recipe-upload-image', args=[recipe_id])

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

    def test_create_recipe_with_new_tags(self):
        """ test creating recipe new tags """
        payload = {
            'title': 'New sample title',
            'link': 'http://example.com/newrecipe.png',
            'description': 'New sample recipe description',
            'time_minutes': 13,
            'price': Decimal('12.32'),
            'tags': [{'name': 'Nepali'}, {'name': 'Chinese'}]
        }
        res = self.client.post(RECIPE_URL, payload, format='json')
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        recipes = Recipe.objects.filter(user=self.user)
        self.assertEqual(recipes.count(), 1)
        recipe = recipes[0]
        self.assertEqual(recipe.tags.count(), 2)
        for tag in payload['tags']:
            exists = recipe.tags.filter(
                name=tag['name'],
                user=self.user,
            ).exists()
            self.assertTrue(exists)
    
    def test_create_recipe_with_existing_tags(self):
        """Test creating a recipe with existing tag."""
        tag_nepali = Tag.objects.create(user=self.user, name='Nepali')
        payload = {
            'title': 'New sample title',
            'link': 'http://example.com/newrecipe.png',
            'description': 'New sample recipe description',
            'time_minutes': 13,
            'price': Decimal('12.32'),
            'tags': [{'name': 'Nepali'}, {'name': 'Chinese'}]
        }
        res = self.client.post(RECIPE_URL, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        recipes = Recipe.objects.filter(user=self.user)
        self.assertEqual(recipes.count(), 1)
        recipe = recipes[0]
        self.assertEqual(recipe.tags.count(), 2)
        self.assertIn(tag_nepali, recipe.tags.all())
        for tag in payload['tags']:
            exists = recipe.tags.filter(
                name=tag['name'],
                user=self.user,
            ).exists()
            self.assertTrue(exists)
    
    def test_create_tag_on_update(self):
        """ test creating tag when updating recipe """
        recipe = create_recipe(user=self.user)

        payload = {'tags': [{'name': 'Lunch'}]}
        url = detail_url(recipe.id)
        res = self.client.patch(url, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        new_tag = Tag.objects.get(user=self.user, name='Lunch')
        self.assertIn(new_tag, recipe.tags.all())

    def test_update_recipe_assign_tag(self):
        """ test assigning an existing tag when updating a recipe """
        tag_breakfast = Tag.objects.create(user=self.user, name='Breakfast')
        recipe = create_recipe(user=self.user)
        recipe.tags.add(tag_breakfast)

        tag_lunch = Tag.objects.create(user=self.user, name='Lunch')
        payload = {'tags': [{'name': 'Lunch'}]}
        url = detail_url(recipe.id)
        res = self.client.patch(url, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn(tag_lunch, recipe.tags.all())
        self.assertNotIn(tag_breakfast, recipe.tags.all())

    def test_clear_recipe_tags(self):
        """ test clearing a recipe tags """
        tag = Tag.objects.create(user=self.user, name='Dinner')
        recipe = create_recipe(user=self.user)
        recipe.tags.add(tag)

        payload = {'tags': []}
        url = detail_url(recipe.id)
        res = self.client.patch(url, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(recipe.tags.count(), 0)
    
    def test_create_recipe_with_new_ingredient(self):
        """ test creating recipe new ingredients """
        payload = {
            'title': 'New sample title',
            'link': 'http://example.com/newrecipe.png',
            'description': 'New sample recipe description',
            'time_minutes': 13,
            'price': Decimal('12.32'),
            'tags': [{'name': 'Nepali'}, {'name': 'Chinese'}],
            'ingredients': [
                {'name': 'Cauli', 'quantity': 1, 'scale': 'gm'},
                {'name': 'Noun', 'quantity': 1, 'scale': 'gm'}
            ],
        }
        res = self.client.post(RECIPE_URL, payload, format='json')
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        recipes = Recipe.objects.filter(user=self.user)
        self.assertEqual(recipes.count(), 1)
        recipe = recipes[0]
        self.assertEqual(recipe.ingredients.count(), 2)
        for ingredient in payload['ingredients']:
            exists = recipe.ingredients.filter(
                name=ingredient['name'],
                user=self.user,
            ).exists()
            self.assertTrue(exists)
    
    def test_create_recipe_with_existing_ingredients(self):
        """ Test creating a recipe with existing ingredients """
        ingre_salt = Ingredient.objects.create(user=self.user, name='Noon', quantity=1, scale='gm')
        payload = {
            'title': 'New sample title',
            'link': 'http://example.com/newrecipe.png',
            'description': 'New sample recipe description',
            'time_minutes': 13,
            'price': Decimal('12.32'),
            'tags': [{'name': 'Nepali'}, {'name': 'Chinese'}],
            'ingredients': [
                {'name': 'Cauli', 'quantity': 1, 'scale': 'gm'},
                {'name': 'Noon', 'quantity': 1, 'scale': 'gm'}
            ],
        }
        res = self.client.post(RECIPE_URL, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        recipes = Recipe.objects.filter(user=self.user)
        self.assertEqual(recipes.count(), 1)
        recipe = recipes[0]
        self.assertEqual(recipe.ingredients.count(), 2)
        self.assertIn(ingre_salt, recipe.ingredients.all())
        for ingredient in payload['ingredients']:
            exists = recipe.ingredients.filter(
                name=ingredient['name'],
                user=self.user,
            ).exists()
            self.assertTrue(exists)

    def test_create_ingredient_on_update(self):
        """ Test creating an ingredient when updating a recipe. """
        recipe = create_recipe(user=self.user)

        payload = {'ingredients': [{'name': 'Limes', 'quantity': 1, 'scale': 'ball'}]}
        url = detail_url(recipe.id)
        res = self.client.patch(url, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        new_ingredient = Ingredient.objects.get(user=self.user, name='Limes')
        self.assertIn(new_ingredient, recipe.ingredients.all())

    def test_update_recipe_assign_ingredient(self):
        """ Test assigning an existing ingredient when updating a recipe. """
        ingredient1 = Ingredient.objects.create(user=self.user, name='Pepper', quantity=15, scale='gm')
        recipe = create_recipe(user=self.user)
        recipe.ingredients.add(ingredient1)

        ingredient2 = Ingredient.objects.create(user=self.user, name='Chili', quantity=15, scale='gm')
        payload = {'ingredients': [{'name': 'Chili', 'quantity': 15, 'scale': 'gm'}]}
        url = detail_url(recipe.id)
        res = self.client.patch(url, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn(ingredient2, recipe.ingredients.all())
        self.assertNotIn(ingredient1, recipe.ingredients.all())

    def test_clear_recipe_ingredients(self):
        """ Test clearing a recipes ingredients. """
        ingredient = Ingredient.objects.create(user=self.user, name='Garlic', quantity=15, scale='gm')
        recipe = create_recipe(user=self.user)
        recipe.ingredients.add(ingredient)

        payload = {'ingredients': []}
        url = detail_url(recipe.id)
        res = self.client.patch(url, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(recipe.ingredients.count(), 0)

class ImageUploadTest(TestCase):
    """ test for image upload api """

    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            'user@example.com',
            'password123',
        )
        self.client.force_authenticate(self.user)
        self.recipe = create_recipe(user=self.user)

    def tearDown(self):
        self.recipe.image.delete()

    def test_upload_image(self):
        """Test uploading an image to a recipe."""
        url = image_upload_url(self.recipe.id)
        with tempfile.NamedTemporaryFile(suffix='.jpg') as image_file:
            img = Image.new('RGB', (10, 10))
            img.save(image_file, format='JPEG')
            image_file.seek(0)
            payload = {'image': image_file}
            res = self.client.post(url, payload, format='multipart')

        self.recipe.refresh_from_db()
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn('image', res.data)
        self.assertTrue(os.path.exists(self.recipe.image.path))

    def test_upload_image_bad_request(self):
        """Test uploading an invalid image."""
        url = image_upload_url(self.recipe.id)
        payload = {'image': 'notanimage'}
        res = self.client.post(url, payload, format='multipart')

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        