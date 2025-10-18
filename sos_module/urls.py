from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    IncomingRequestsView,
    KeywordViewSet,
    MeView,
    ContactViewSet,
    LocationView,
    FavoriteContactViewSet,
    OutgoingRequestsView,
    RegisterView,
    SosSignalViewSet,
    UpdateLocationView,
    UpdateOnlineStatusView,
)
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from django.conf import settings
from django.conf.urls.static import static

router = DefaultRouter()
router.register("contacts", ContactViewSet, basename="contacts")
router.register("favorites", FavoriteContactViewSet, basename="favorites")
router.register("sos", SosSignalViewSet, basename="sos")
router.register(r"keywords", KeywordViewSet, basename="keywords")

urlpatterns = [
    # Auth & Profile
    path("auth/me/", MeView.as_view(), name="me"),
    path("auth/update-status/", UpdateOnlineStatusView.as_view(), name="update-status"),
    path('token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),  # login
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'), # refresh
    path('register/', RegisterView.as_view(), name='register'),

    # Contacts requests
    path("contacts/outgoing-requests/", OutgoingRequestsView.as_view(), name="outgoing-requests"),
    path("contacts/incoming-requests/", IncomingRequestsView.as_view(), name="incoming-requests"),

    # Location
    path("location/update/", UpdateLocationView.as_view(), name="location-update"),
    path("location/me/", LocationView.as_view(), name="location-me"),

    # Routers (contacts, favorites, sos)
    path("", include(router.urls)),
]