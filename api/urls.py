from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

from .views import (
    UserRegisterView,
    UserProfileView,
    TattooStyleListView,
    TattooDesignViewSet,
    GalleryListView,
    FavoriteListView,
    VerifyMobilePurchaseView,
)

router = DefaultRouter()
router.register(r'designs', TattooDesignViewSet, basename='design')

urlpatterns = [
    # Main ViewSet for designs
    path('', include(router.urls)),

    # Authentication
    path('auth/register/', UserRegisterView.as_view(), name='user-register'),
    path('auth/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),

    # User Profile
    path('users/me/', UserProfileView.as_view(), name='user-profile'),

    # Tattoo Styles
    path('styles/', TattooStyleListView.as_view(), name='style-list'),

    # Gallery and Favorites
    path('gallery/', GalleryListView.as_view(), name='gallery-list'),
    path('favorites/', FavoriteListView.as_view(), name='favorite-list'),

    # Subscription
    path('subscriptions/verify-purchase/', VerifyMobilePurchaseView.as_view(), name='verify-purchase'),
]

