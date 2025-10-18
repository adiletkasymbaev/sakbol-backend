from django.db import models
from django.utils import timezone
from rest_framework import generics, permissions, status, viewsets
from rest_framework.response import Response
from rest_framework.decorators import action
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework.response import Response
from .models import Contact, Keyword, Location, FavoriteContact, SosSignal
from .serializers import (
    KeywordSerializer,
    RegisterSerializer,
    UserSerializer,
    ContactSerializer,
    CreateContactSerializer,
    LocationSerializer,
    FavoriteContactSerializer,
    SosSignalSerializer,
)

User = get_user_model()

class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]

class MeView(generics.RetrieveAPIView):
    """
    GET /api/auth/me/
    """
    serializer_class = UserSerializer

    def get_object(self):
        return self.request.user

class ContactViewSet(viewsets.ModelViewSet):
    """
    /api/contacts/
    - GET: список подтверждённых контактов
    - POST: отправка заявки по identifier
    - POST /accept/{id}/ — принять заявку
    - POST /cancel/{id}/ — отменить исходящую заявку
    """
    queryset = Contact.objects.all()

    def get_queryset(self):
        user = self.request.user
        return Contact.objects.filter(
            models.Q(from_user=user),
            is_accepted=True
        )

    def get_serializer_class(self):
        if self.action == "create":
            return CreateContactSerializer
        return ContactSerializer

    def perform_create(self, serializer):
        serializer.save(from_user=self.request.user)

    @action(detail=True, methods=["post"])
    def accept(self, request, pk=None):
        """
        Принять входящую заявку
        """
        contact = get_object_or_404(Contact, pk=pk, to_user=request.user)
        if contact.is_accepted:
            return Response({"detail": "Уже подтверждено."}, status=400)
        contact.is_accepted = True
        contact.save()
        return Response(ContactSerializer(contact, context={"request": request}).data)

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        """
        Отменить исходящую заявку (если она ещё не принята)
        """
        contact = get_object_or_404(Contact, pk=pk, from_user=request.user)
        if contact.is_accepted:
            return Response({"detail": "Нельзя отменить — уже принято."}, status=400)
        contact.delete()
        return Response({"detail": "Заявка отменена."}, status=204)

class IncomingRequestsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        qs = Contact.objects.filter(to_user=user, is_accepted=False)
        serializer = ContactSerializer(qs, many=True, context={"request": request})
        return Response(serializer.data)


class OutgoingRequestsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        qs = Contact.objects.filter(from_user=user, is_accepted=False)
        serializer = ContactSerializer(qs, many=True, context={"request": request})
        return Response(serializer.data)

class LocationView(generics.CreateAPIView, generics.RetrieveAPIView):
    """
    POST /api/location/update/ — обновить местоположение
    GET  /api/location/me/ — получить своё
    """
    serializer_class = LocationSerializer

    def get_object(self):
        return Location.objects.filter(user=self.request.user).first()

    def perform_create(self, serializer):
        serializer.save()

class FavoriteContactViewSet(viewsets.ModelViewSet):
    """
    /api/favorites/
    - list (GET): список избранных
    - create (POST): добавить контакт
    - delete (DELETE): удалить контакт
    """
    serializer_class = FavoriteContactSerializer

    def get_queryset(self):
        return FavoriteContact.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save()

class SosSignalViewSet(viewsets.ModelViewSet):
    """
    /api/sos/
    - list (GET): список своих SOS-сигналов
    - create (POST): отправить новый сигнал
    """
    serializer_class = SosSignalSerializer

    def get_queryset(self):
        return SosSignal.objects.filter(sender=self.request.user)

    def perform_create(self, serializer):
        sos = serializer.save()
        # TODO: запустить Celery-задачу для рассылки уведомлений избранным
        return sos

class KeywordViewSet(viewsets.ModelViewSet):
    serializer_class = KeywordSerializer

    def get_queryset(self):
        return Keyword.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

class UpdateLocationView(APIView):
    def post(self, request):
        user = request.user
        lat = request.data.get("latitude")
        lon = request.data.get("longitude")

        if lat is None or lon is None:
            return Response({"error": "Отсутствуют координаты"}, status=status.HTTP_400_BAD_REQUEST)

        location, _ = Location.objects.get_or_create(user=user)
        location.latitude = lat
        location.longitude = lon
        location.save()

        return Response({"message": "Геолокация успешно обновлена"})
    
class UpdateOnlineStatusView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        status_value = request.data.get("is_online", None)

        if status_value is None:
            return Response({"error": "Missing is_online field"}, status=status.HTTP_400_BAD_REQUEST)

        user.is_online = bool(status_value)
        user.last_seen = timezone.now()
        user.save(update_fields=["is_online", "last_seen"])

        return Response({
            "message": "Status updated",
            "is_online": user.is_online,
            "last_seen": user.last_seen,
        })