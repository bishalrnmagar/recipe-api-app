"""
Serializer for Recipe API
"""
from rest_framework import serializers
from core.models import Recipe, Tag

class TagSerializer(serializers.ModelSerializer):
    """ Serializer for tags """
    class Meta:
        model = Tag
        fields = ['id', 'name']
        read_only_fields = ['id']

class RecipeSerializer(serializers.ModelSerializer):
    """ Serializer for recipe """
    tags = TagSerializer(many=True, required=False)
    class Meta:
        model = Recipe
        fields = ['id', 'title', 'time_minutes', 'price', 'link', 'tags']
        read_only_fields = ['id']

    def _get_or_create_tags(self, tags, recipe):
        """ get or create tags """
        auth_user = self.context['request'].user
        for tag in tags:
            tag_obj, created = Tag.objects.get_or_create(user=auth_user, **tag)
            recipe.tags.add(tag_obj)

    def create(self, validated_data):
        """ create recipe """
        tags = validated_data.pop('tags', [])
        recipe = Recipe.objects.create(**validated_data)
        self._get_or_create_tags(tags, recipe)  
        return recipe

    def update(self, instance, validated_data):
        """ update recipe """
        tags = validated_data.pop('tags', None)
        if tags is not None:
            instance.tags.clear()
            self._get_or_create_tags(tags, instance)

        for attr, val in validated_data.items():
            setattr(instance, attr, val)
        
        instance.save()
        return instance

class RecipeDetailSerializer(RecipeSerializer):
    """ Serializer for recipe detail """
    class Meta(RecipeSerializer.Meta):
        fields = RecipeSerializer.Meta.fields + ['description']