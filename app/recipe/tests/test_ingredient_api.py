"""
test for ingredients apis
"""
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.urls import reverse
from django.test import TestCase

from rest_framework import status
from rest_framework.test import APIClient

from core.models import Ingredient, Recipe
from recipe.serializers import IngredientSerializer

INGREDIENT_URL = reverse('recipe:ingredient-list')

def detail_url(ingre_id):
    """ Create and return tag detail URL """
    return reverse('recipe:ingredient-detail', args=[ingre_id])

def create_user(email="test@example.com", password="testpass123"):
    """ Create and return a user """
    return get_user_model().objects.create_user(email, password)

def create_ingredients(user, **params):
    """ Create and return a sample recipe """
    defaults = {
        'name': 'Pitho',
        'quantity': 50,
        'scale': 'gm'
    }
    defaults.update(params)

    ingredient = Ingredient.objects.create(user=user, **defaults)
    return ingredient

class PublicIngredientAPITest(TestCase):
    """ test unauthorized api calls """

    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        """ test to check unauthorized user """
        res = self.client.get(INGREDIENT_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

class PrivateIngredientAPITest(TestCase):
    """ test authorized api calls """

    def setUp(self):
        self.client = APIClient()
        self.user = create_user()
        self.client.force_authenticate(self.user)

    def test_retrieve_ingredients(self):
        """ test retrieving list of ingredients """
        create_ingredients(self.user)
        create_ingredients(self.user, name="Vanilla")

        res = self.client.get(INGREDIENT_URL)

        ingredients = Ingredient.objects.all().order_by('-id')
        serializer = IngredientSerializer(ingredients, many=True)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_ingredients_limited_to_user(self):
        """ test list of ingredients to limited user """
        user2 = create_user(email="user2@example.com")
        create_ingredients(user2, name='Salt')
        ingredient = create_ingredients(self.user, name='Pepper')

        res = self.client.get(INGREDIENT_URL)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]['name'], ingredient.name)
        self.assertEqual(res.data[0]['id'], ingredient.id)
        self.assertEqual(res.data[0]['quantity'], ingredient.quantity)
        self.assertEqual(res.data[0]['scale'], ingredient.scale)

    def test_update_ingredient(self):
        """ test updating an ingredient """
        ingredient = create_ingredients(self.user, name="Maida")
        payload = {'name': 'Suzhi'}
        
        url = detail_url(ingredient.id)
        res = self.client.patch(url, payload)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        ingredient.refresh_from_db()
        self.assertEqual(ingredient.name, payload['name'])

    def test_delete_ingredient(self):
        """ test deleting ingredients """
        ingredient = create_ingredients(user=self.user)

        url = detail_url(ingredient.id)
        res = self.client.delete(url)

        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Ingredient.objects.filter(id=ingredient.id).exists())
    
    def test_filter_ingredients_assigned_to_recipes(self):
        """Test listing ingedients to those assigned to recipes."""
        in1 = Ingredient.objects.create(user=self.user, name='Apples', quantity=1, scale='piece')
        in2 = Ingredient.objects.create(user=self.user, name='Turkey', quantity=1, scale='kg')
        recipe = Recipe.objects.create(
            title='Apple Crumble',
            time_minutes=5,
            price=Decimal('4.50'),
            user=self.user,
        )
        recipe.ingredients.add(in1)

        res = self.client.get(INGREDIENT_URL, {'assigned_only': 1})

        s1 = IngredientSerializer(in1)
        s2 = IngredientSerializer(in2)
        self.assertIn(s1.data, res.data)
        self.assertNotIn(s2.data, res.data)

    def test_filtered_ingredients_unique(self):
        """Test filtered ingredients returns a unique list."""
        ing = Ingredient.objects.create(user=self.user, name='Eggs', quantity=3, scale='piece')
        Ingredient.objects.create(user=self.user, name='Lentils', quantity=300, scale='gm')
        recipe1 = Recipe.objects.create(
            title='Eggs Benedict',
            time_minutes=60,
            price=Decimal('7.00'),
            user=self.user,
        )
        recipe2 = Recipe.objects.create(
            title='Herb Eggs',
            time_minutes=20,
            price=Decimal('4.00'),
            user=self.user,
        )
        recipe1.ingredients.add(ing)
        recipe2.ingredients.add(ing)

        res = self.client.get(INGREDIENT_URL, {'assigned_only': 1})

        self.assertEqual(len(res.data), 1)