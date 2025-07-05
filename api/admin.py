from django.contrib import admin

# Register your models here.
from .models import User, TattooStyle, TattooDesign, Subscription, APIUsage, UserFavorite

# We can create a more descriptive admin view for TattooStyle
class TattooStyleAdmin(admin.ModelAdmin):
    list_display = ('display_name', 'name', 'is_active', 'created_at')
    list_filter = ('is_active',)

# Register your models here
admin.site.register(User)
admin.site.register(TattooStyle, TattooStyleAdmin) # Use the custom admin class
admin.site.register(TattooDesign)
admin.site.register(Subscription)
admin.site.register(APIUsage)
admin.site.register(UserFavorite)
