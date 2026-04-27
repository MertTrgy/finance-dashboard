from django.contrib.auth.models import User
from rest_framework import serializers
from .models import Category, Transaction, Budget, RecurringTransaction
from .currency_service import convert_to_gbp


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

    # New Feature Added currencies and recurring transactions
    # Write-only: what the user sends. Read-only fields below show what was stored.
    input_amount      = serializers.DecimalField(
        max_digits=12, decimal_places=2, write_only=True, required=False
    )
    input_currency    = serializers.CharField(max_length=3, write_only=True, required=False)


    class Meta:
        model = Transaction
        fields = (
            'id', 'category', 'category_detail', 'type',
            'amount',                          # GBP amount (always)
            'original_amount', 'original_currency', 'exchange_rate',
            'input_amount', 'input_currency',  # write-only helpers
            'note', 'date', 'created_at', 'recurring_source',
        )
        read_only_fields = ('created_at', 'amount', 'original_amount',
                            'exchange_rate', 'recurring_source')

    def _resolve_amount(self, validated_data):
        """
        If input_amount + input_currency are provided, convert to GBP.
        Otherwise fall through to the plain `amount` field.
        """
        input_amount   = validated_data.pop('input_amount',   None)
        input_currency = validated_data.pop('input_currency', 'GBP').upper()

        if input_amount is not None:
            gbp_amount, rate = convert_to_gbp(input_amount, input_currency)
            validated_data['amount']            = gbp_amount
            validated_data['original_amount']   = input_amount
            validated_data['original_currency'] = input_currency
            validated_data['exchange_rate']     = rate

        return validated_data

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        validated_data = self._resolve_amount(validated_data)
        return super().create(validated_data)

    def update(self, instance, validated_data):
        validated_data = self._resolve_amount(validated_data)
        return super().update(instance, validated_data)
    
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
class RecurringTransactionSerializer(serializers.ModelSerializer):
    category_detail = CategorySerializer(source='category', read_only=True)

    class Meta:
        model  = RecurringTransaction
        fields = (
            'id', 'category', 'category_detail', 'type',
            'amount', 'note', 'frequency', 'next_due',
            'active', 'original_currency', 'created_at',
        )
        read_only_fields = ('created_at',)

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)