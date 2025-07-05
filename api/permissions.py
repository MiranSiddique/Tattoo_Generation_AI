from rest_framework import permissions
from .models import APIUsage
import datetime

# A simple rule for now: Free users get 5 creations per day.
FREE_TIER_LIMIT = 5

class IsProUser(permissions.BasePermission):
    """
    Allows access only to Pro users.
    """
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.is_pro

class HasCreationQuota(permissions.BasePermission):
    """
    Allows access if the user is Pro OR if they are a free user
    who has not exceeded their daily quota.
    """
    message = 'You have exceeded your daily creation limit. Upgrade to Pro for unlimited creations.'

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        # Pro users always have access
        if request.user.is_pro:
            return True

        # Check usage for free users
        today = datetime.date.today()
        usage, created = APIUsage.objects.get_or_create(
            user=request.user,
            endpoint='/api/designs/',
            date=today
        )
        return usage.requests_count < FREE_TIER_LIMIT