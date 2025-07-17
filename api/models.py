from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import FileExtensionValidator
import uuid

class User(AbstractUser):
    """Custom user model"""
    profile_picture = models.ImageField(
        upload_to='profile_pics/', 
        null=True, 
        blank=True,
        validators=[FileExtensionValidator(allowed_extensions=['jpg', 'jpeg', 'png'])]
    )
    is_pro = models.BooleanField(default=False)
    pro_subscription_date = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class TattooStyle(models.Model):
    """Tattoo styles available in the app"""
    STYLE_CHOICES = [
        ('traditional', 'Traditional'),
        ('gothic_text', 'Gothic Text'),
        ('pop_art', 'Pop Art'),
        ('victorian', 'Victorian'),
        ('creepy', 'Creepy'),
        ('abstract', 'Abstract'),
        ('mascot', 'Mascot'),
        ('retro', 'Retro'),
        ('3d', '3D'),
    ]
    
    name = models.CharField(max_length=50, choices=STYLE_CHOICES, unique=True)
    display_name = models.CharField(max_length=100)
    #thumbnail = models.ImageField(upload_to='style_thumbnails/')
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    #created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.display_name

class TattooDesign(models.Model):
    """Generated tattoo designs"""
    STATUS_CHOICES = [
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='tattoo_designs')
    prompt = models.TextField(max_length=1500)
    style = models.ForeignKey(TattooStyle, on_delete=models.CASCADE)
    
    source_image = models.ImageField(
        upload_to='source_images/', 
        null=True, 
        blank=True,
        validators=[FileExtensionValidator(allowed_extensions=['jpg', 'jpeg', 'png'])]
    )
    
    # Generated results
    generated_image = models.ImageField(upload_to='generated_tattoos/', null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='processing')
    
    # AI processing details
    ai_model_used = models.CharField(max_length=100, blank=True)
    processing_time = models.FloatField(null=True, blank=True)  
    
    # User interaction
    is_favorite = models.BooleanField(default=False)
    is_public = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} - {self.style.display_name} - {self.created_at}"

class Gallery(models.Model):
    """Public gallery of tattoo designs"""
    design = models.OneToOneField(TattooDesign, on_delete=models.CASCADE)
    featured = models.BooleanField(default=False)
    views_count = models.PositiveIntegerField(default=0)
    likes_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-featured', '-likes_count', '-created_at']
        verbose_name_plural = "Galleries" 

class UserFavorite(models.Model):
    """User's favorite designs"""
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    design = models.ForeignKey(TattooDesign, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['user', 'design']

class APIUsage(models.Model):
    """Track API usage for rate limiting"""
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    endpoint = models.CharField(max_length=100)
    requests_count = models.PositiveIntegerField(default=0)
    date = models.DateField(auto_now_add=True)

    class Meta:
        unique_together = ['user', 'endpoint', 'date']

class Subscription(models.Model):
    """Pro subscription management"""
    PLAN_CHOICES = [
        ('free', 'Free'),
        ('pro_monthly', 'Pro Monthly'),
        ('pro_yearly', 'Pro Yearly'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    plan = models.CharField(max_length=20, choices=PLAN_CHOICES, default='free')
    start_date = models.DateTimeField(null=True, blank=True)
    end_date = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=False)
    stripe_subscription_id = models.CharField(max_length=200, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username} - {self.plan}"
