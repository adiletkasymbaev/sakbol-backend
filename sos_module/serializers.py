from django.db.models import Q
from django.utils import timezone
from datetime import timedelta
from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Contact, Keyword, Location, FavoriteContact, SosSignal

User = get_user_model()

class UserSerializer(serializers.ModelSerializer):
    last_seen_display = serializers.SerializerMethodField()
    location = serializers.SerializerMethodField()  # 👈 Добавляем поле для геолокации

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "phone_number",
            "role",
            "is_online",
            "last_seen",
            "avatar",
            "last_seen_display",
            "location",  # 👈 Добавляем сюда
        ]

    def get_last_seen_display(self, obj):
        if not obj.last_seen:
            return "никогда"

        now = timezone.now()
        diff = now - obj.last_seen

        if diff < timedelta(minutes=1):
            return "только что"
        elif diff < timedelta(hours=1):
            minutes = int(diff.total_seconds() // 60)
            return f"{minutes} мин"
        elif diff < timedelta(days=1):
            hours = int(diff.total_seconds() // 3600)
            return f"{hours} ч"
        elif diff < timedelta(days=30):
            days = diff.days
            return f"{days} дн"
        else:
            return obj.last_seen.strftime("%d.%m.%Y")

    def get_location(self, obj):
        """Возвращает последнюю геолокацию пользователя (если есть)."""
        from .models import Location  # избегаем циклического импорта

        location = Location.objects.filter(user=obj).order_by("-updated_at").first()
        if location:
            return {
                "latitude": location.latitude,
                "longitude": location.longitude,
                "updated_at": location.updated_at,
            }
        return None

class KeywordSerializer(serializers.ModelSerializer):
    class Meta:
        model = Keyword
        fields = ["id", "word"]

class ContactSerializer(serializers.ModelSerializer):
    """Сериализатор для отображения контактов (подтверждённых)."""

    from_user = UserSerializer(read_only=True)
    to_user = UserSerializer(read_only=True)
    is_favorite = serializers.SerializerMethodField()

    class Meta:
        model = Contact
        fields = ["id", "from_user", "to_user", "is_accepted", "created_at", "is_favorite"]

    def get_is_favorite(self, obj):
        """Проверяет, добавлен ли другой пользователь в избранное текущего."""
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return False

        current_user = request.user
        # определяем, кто является "контактным пользователем" относительно текущего юзера
        contact_user = obj.to_user if obj.from_user == current_user else obj.from_user

        return FavoriteContact.objects.filter(
            user=current_user, contact=contact_user
        ).exists()

class CreateContactSerializer(serializers.ModelSerializer):
    """Сериализатор для отправки заявки по идентификатору."""

    identifier = serializers.CharField(write_only=True)

    class Meta:
        model = Contact
        fields = ["identifier"]

    def validate_identifier(self, value):
        request = self.context["request"]
        user = request.user

        try:
            to_user = User.objects.get(identifier=value)
        except User.DoesNotExist:
            raise serializers.ValidationError("Пользователь с таким идентификатором не найден.")

        if user == to_user:
            raise serializers.ValidationError("Нельзя добавить самого себя.")

        # Проверяем все возможные состояния заявок между пользователями
        if Contact.objects.filter(
            Q(from_user=user, to_user=to_user) | Q(from_user=to_user, to_user=user)
        ).exists():
            raise serializers.ValidationError("Контакт уже существует или заявка уже отправлена.")

        return value

    def create(self, validated_data):
        user = self.context["request"].user
        identifier = validated_data["identifier"]
        to_user = User.objects.get(identifier=identifier)
        return Contact.objects.create(from_user=user, to_user=to_user)

class LocationSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)

    class Meta:
        model = Location
        fields = ["user", "latitude", "longitude", "updated_at"]

    def create(self, validated_data):
        user = self.context["request"].user
        location, _ = Location.objects.update_or_create(
            user=user, defaults=validated_data
        )
        return location

class FavoriteContactSerializer(serializers.ModelSerializer):
    contact = UserSerializer(read_only=True)
    contact_id = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(),
        source="contact",
        write_only=True
    )
    location = serializers.SerializerMethodField()
    is_favorite = serializers.SerializerMethodField()

    class Meta:
        model = FavoriteContact
        fields = ["id", "contact", "contact_id", "location", "is_favorite"]

    def get_location(self, obj):
        location = Location.objects.filter(user=obj.contact).order_by("-updated_at").first()
        if location:
            return LocationSerializer(location).data
        return None

    def get_is_favorite(self, obj):
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return False
        return FavoriteContact.objects.filter(user=request.user, contact=obj.contact).exists()

    def validate(self, attrs):
        user = self.context["request"].user
        contact = attrs.get("contact")
        if user == contact:
            raise serializers.ValidationError({"detail": "Нельзя добавить самого себя в избранное."})
        if FavoriteContact.objects.filter(user=user, contact=contact).exists():
            raise serializers.ValidationError({"detail": "Этот пользователь уже добавлен в избранное."})
        return attrs

    def create(self, validated_data):
        user = self.context["request"].user
        return FavoriteContact.objects.create(user=user, **validated_data)

class SosSignalSerializer(serializers.ModelSerializer):
    sender = UserSerializer(read_only=True)

    class Meta:
        model = SosSignal
        fields = ["id", "sender", "latitude", "longitude", "created_at", "is_active"]

    def create(self, validated_data):
        user = self.context["request"].user
        sos = SosSignal.objects.create(sender=user, **validated_data)
        # Здесь можно триггерить задачу Celery для уведомлений
        return sos
    
class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    password2 = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ('first_name', 'email', 'last_name', 'password', 'password2', 'role')
        extra_kwargs = {'role': {'default': 'user'}}

    def validate(self, attrs):
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({"password": "Пароли не совпадают"})
        return attrs

    def create(self, validated_data):
        validated_data.pop('password2')
        password = validated_data.pop('password')
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user