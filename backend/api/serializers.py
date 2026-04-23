from django.contrib.auth.models import User
from rest_framework import serializers
from .models import Category, Transaction, Budget


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'password')

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'username', 'email')


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ('id', 'name', 'type', 'color')

    def create(self, validated_data):
        # automatically attach the logged-in user
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)


class TransactionSerializer(serializers.ModelSerializer):
    category_detail = CategorySerializer(source='category', read_only=True)

    class Meta:
        model = Transaction
        fields = ('id', 'category', 'category_detail', 'type', 'amount', 'note', 'date', 'created_at')
        read_only_fields = ('created_at',)

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)
    
class BudgetSerializer(serializers.ModelSerializer):
    category_detail = CategorySerializer(source='category', read_only=True)
 
    class Meta:
        model  = Budget
        fields = ('id', 'category', 'category_detail', 'limit', 'month')
 
    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)
 
    def update(self, instance, validated_data):
        # Allow upsert-style update of limit
        instance.limit = validated_data.get('limit', instance.limit)
        instance.save()
        return instance