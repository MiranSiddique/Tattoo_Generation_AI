from rest_framework import serializers
from .models import User, TattooStyle, TattooDesign, UserFavorite, Subscription

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'password', 'profile_picture', 'is_pro']
        read_only_fields = ['is_pro']
        extra_kwargs = {
            'password': {'write_only': True}
        }
    
    def create(self, validated_data):
        """
        This method is called when a new user is created.
        It uses Django's `create_user` method to ensure the password is
        hashed correctly and the user is set to active.
        """
        password = validated_data.pop('password', None)
    
        instance = self.Meta.model(**validated_data)
        
        if password is not None:
            # Using set_password() to hash the password
            instance.set_password(password)
        
        # Saving the user instance to the database
        instance.save()
        
        return instance

class TattooStyleSerializer(serializers.ModelSerializer):
    class Meta:
        model = TattooStyle
        fields = ['id', 'name', 'display_name',  'description']

class TattooDesignCreateSerializer(serializers.Serializer):
    """Serializer for creating a new design. Captures all customization options."""
    prompt = serializers.CharField(max_length=1500)
    style = serializers.PrimaryKeyRelatedField(queryset=TattooStyle.objects.filter(is_active=True))

    # Optional fields from the "Customize" screen
    output_format = serializers.CharField(required=False) # e.g., "on arm", "on leg", "white background"
    aspect_ratio = serializers.CharField(required=False) # e.g., "1:1 Square", "9:16 Portrait"
    gender = serializers.CharField(required=False) # e.g., "Male", "Female"

    def create(self, validated_data):
      # The view will handle the actual object creation
      return validated_data

class TattooDesignSerializer(serializers.ModelSerializer):
    style = TattooStyleSerializer(read_only=True)
    is_user_favorite = serializers.SerializerMethodField()

    class Meta:
        model = TattooDesign
        fields = [
            'id', 'prompt', 'style', 'source_image', 'generated_image',
            'status', 'is_public', 'created_at', 'is_user_favorite'
        ]

    def get_is_user_favorite(self, obj):
        user = self.context['request'].user
        if user.is_authenticated:
            return UserFavorite.objects.filter(user=user, design=obj).exists()
        return False

class GalleryDesignSerializer(serializers.ModelSerializer):
    """Serializer for the public gallery and search results."""
    style_name = serializers.CharField(source='style.display_name')
    user = serializers.CharField(source='user.username')

    class Meta:
        model = TattooDesign
        fields = ['id', 'prompt', 'generated_image', 'style_name', 'user']

class SubscriptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subscription
        fields = ['plan', 'end_date', 'is_active']