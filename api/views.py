from rest_framework import generics, viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.decorators import action
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters
import threading

from .models import User, TattooStyle, TattooDesign, UserFavorite, APIUsage, Gallery
from .serializers import (
    UserSerializer, TattooStyleSerializer, TattooDesignSerializer,
    TattooDesignCreateSerializer, GalleryDesignSerializer
)
from .permissions import HasCreationQuota
from .tasks import generate_tattoo_from_prompt
import datetime

class UserRegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [AllowAny] # Anyone can register

class UserProfileView(generics.RetrieveUpdateAPIView):
    """
    GET /api/users/me/ -> Get current user's profile.
    PATCH /api/users/me/ -> Update current user's profile (e.g., profile_picture).
    """
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user

class TattooStyleListView(generics.ListAPIView):
    """
    GET /api/styles/ -> List all active tattoo styles.
    Used for the style selection section on the prompt screen.
    """
    queryset = TattooStyle.objects.filter(is_active=True)
    serializer_class = TattooStyleSerializer
    permission_classes = [AllowAny]

class TattooDesignViewSet(viewsets.ModelViewSet):
    """
    ViewSet for creating and managing tattoo designs.
    """
    queryset = TattooDesign.objects.all()
    serializer_class = TattooDesignSerializer

    def get_permissions(self):
        if self.action == 'create':
            permission_classes = [IsAuthenticated, HasCreationQuota]
        else:
            permission_classes = [IsAuthenticated]
        return [permission() for permission in permission_classes]

    def get_queryset(self):
        # Only return designs for the currently authenticated user.
        return TattooDesign.objects.filter(user=self.request.user)

    def get_serializer_class(self):
        if self.action == 'create':
            return TattooDesignCreateSerializer
        return TattooDesignSerializer

    def perform_create(self, serializer):
        """
        Overrides the default create behavior to construct the prompt and
        trigger the async task for tattoo generation.
        """
        data = serializer.validated_data
        style = data['style']

        # 1. Construct the final prompt
        base_prompt = data['prompt']
        customizations = []
        if data.get('gender'):
            customizations.append(f"for a {data['gender'].lower()} person")
        if data.get('output_format'):
            customizations.append(f"on a {data['output_format'].lower()}")

        # Example Final Prompt Construction: "Gothic Text style tattoo, a dragon breathing fire, for a male person, on an arm."
        final_prompt = f"{style.display_name} style tattoo, {base_prompt}"
        if customizations:
            final_prompt += ", " + ", ".join(customizations)

        # 2. Create the TattooDesign object
        design = TattooDesign.objects.create(
            user=self.request.user,
            prompt=base_prompt, # Store original prompt
            style=style,
            status='processing'
        )

        # 3. Trigger the async task for tattoo generation
        task_thread = threading.Thread(
            target=generate_tattoo_from_prompt,
            args=(design.id, final_prompt)
        )
        task_thread.start()

        # 4. Update API usage for free users
        if not self.request.user.is_pro:
            usage, _ = APIUsage.objects.get_or_create(
                user=self.request.user,
                endpoint='/api/designs/',
                date=datetime.date.today()
            )
            usage.requests_count += 1
            usage.save()
        
        # Set the instance on the serializer to return the created object
        self.instance = design

    def create(self, request, *args, **kwargs):
        """
        Customize the response for the create action.
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        
        # Return the full design object using the detail serializer
        response_serializer = TattooDesignSerializer(self.instance, context={'request': request})
        headers = self.get_success_headers(response_serializer.data)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    @action(detail=True, methods=['post'], url_path='favorite')
    def favorite(self, request, pk=None):
        """
        POST /api/designs/{id}/favorite/ -> Add a design to user's favorites.
        """
        design = self.get_object()
        UserFavorite.objects.get_or_create(user=request.user, design=design)
        return Response({'status': 'favorited'}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['delete'], url_path='unfavorite')
    def unfavorite(self, request, pk=None):
        """
        DELETE /api/designs/{id}/favorite/ -> Remove a design from user's favorites.
        """
        design = self.get_object()
        UserFavorite.objects.filter(user=request.user, design=design).delete()
        return Response({'status': 'unfavorited'}, status=status.HTTP_204_NO_CONTENT)

class GalleryListView(generics.ListAPIView):
    """
    GET /api/gallery/ -> Returns public completed designs for the home screen grid and search page.
    Supports filtering by style and searching by prompt text.
    e.g. /api/gallery/?style__name=traditional&search=dragon
    """
    queryset = TattooDesign.objects.filter(is_public=True, status='completed')
    serializer_class = GalleryDesignSerializer
    permission_classes = [AllowAny]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['style__name'] # Allows ?style__name=gothic_text
    search_fields = ['prompt'] # Allows ?search=dragon

class FavoriteListView(generics.ListAPIView):
    """
    GET /api/favorites/ -> Gets all designs favorited by the current user.
    """
    serializer_class = TattooDesignSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return TattooDesign.objects.filter(userfavorite__user=self.request.user)

# Placeholder for subscription verification
class VerifyMobilePurchaseView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        """
        Receives a purchase token from the mobile app (Apple/Google).
        This requires a library like `google-play-billing` or `itunes-iap`
        to verify the receipt with the respective store.
        """
        # receipt_token = request.data.get('token')
        # plan_type = request.data.get('plan') # e.g., 'pro_yearly'
        #
        # is_valid = verify_with_app_store(receipt_token) # Your verification logic here
        #
        # if is_valid:
        #   update_user_subscription(request.user, plan_type)
        #   return Response({'status': 'success', 'is_pro': True})
        #
        # return Response({'status': 'failed'}, status=400)
        
        # This is a complex feature, so for I am just simulating success payment scenario
        user = request.user
        user.is_pro = True
        user.save()
        
        
        return Response({'status': 'Subscription activated successfully.'})