from rest_framework import serializers
from .models import Business, User


class BusinessSerializer(serializers.ModelSerializer):
    """
    **business serializer is handling json data for business model**
    user: [UserRegisterSerializer] handles the user registration and user fields.
    fields: [label, user] as slug and registration_date are auto-generating field,
    only label and user fields are needed in serializer.
    """
    class UserRegisterSerializer(serializers.ModelSerializer):
        """
            **user serializer is handling json data for user model and is a nested serializer.
            whenever we are aiming to create a business, a user is created as the same time
            so user fields need to be considered in business serializer**
        """
        class Meta:
            model = User
            fields = ['username', 'email', 'password']

        def validate(self, attrs):
            """
                username & email have to be unique.
                password's length has to be more than 8 characters.
            """
            if User.objects.filter(username=attrs.get('username')).exists():
                raise serializers.ValidationError('username already exists')

            if User.objects.filter(email=attrs.get('email')).exists():
                raise serializers.ValidationError('email already exists')

            if len(attrs.get('password')) < 8:
                raise serializers.ValidationError('password length has to contain more than 8 characters')

            return attrs

    user = UserRegisterSerializer()

    class Meta:
        model = Business
        fields = ['user', 'label']

    def validate(self, attrs):
        """
            user object has to be valid(due to UserRegisterSerializer standards).
            business label has to unique as well.
        """
        if not self.UserRegisterSerializer(data=attrs.get('user')).is_valid():
            raise serializers.ValidationError('user is not valid')

        if Business.objects.filter(label__exact=attrs.get('label')).exists():
            raise serializers.ValidationError('business with this label already exists')

        return attrs

