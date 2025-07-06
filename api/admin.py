from django.contrib import admin
from .models import User, TattooStyle, TattooDesign, Subscription, APIUsage, UserFavorite

class TattooStyleAdmin(admin.ModelAdmin):
    list_display = ('display_name', 'name', 'is_active', 'created_at')
    list_filter = ('is_active',)

admin.site.register(User)
admin.site.register(TattooStyle, TattooStyleAdmin) 
admin.site.register(TattooDesign)
admin.site.register(Subscription)
admin.site.register(APIUsage)
admin.site.register(UserFavorite)
