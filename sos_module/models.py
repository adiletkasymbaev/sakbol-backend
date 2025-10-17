import random
from django.db import models
from django.contrib.auth.models import AbstractUser

class User(AbstractUser):
    ROLE_CHOICES = [
        ('user', 'user'),
        ('parent', 'parent'),
        ('child', 'child'),
        ('admin', 'admin'),
    ]
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='user', verbose_name='Роль')
    phone_number = models.CharField(max_length=20, unique=True, verbose_name='Номер телефона')
    is_online = models.BooleanField(default=False, verbose_name='Онлайн статус')
    last_seen = models.DateTimeField(null=True, blank=True, verbose_name='Последний раз в сети')
    identifier = models.CharField(max_length=6, unique=True, blank=True, null=True, verbose_name='Идентификатор')
    email = models.EmailField(unique=True)
    avatar = models.ImageField(null=True, blank=True, upload_to="avatars/", verbose_name='Миниатюра')
    
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    def save(self, *args, **kwargs):
        if not self.identifier and self.first_name and self.last_name:
            digits = f"{random.randint(0, 9)}{random.randint(0, 9)}"
            first_letters = (self.first_name[:2]).upper().ljust(2, 'X')
            last_letters = (self.last_name[:2]).upper().ljust(2, 'X')
            self.identifier = f"{digits}{first_letters}{last_letters}"
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'

    def __str__(self):
        return f"{self.email} ({self.role}) - {self.phone_number}"

class Contact(models.Model):
    from_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_requests', verbose_name='От пользователя')
    to_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_requests', verbose_name='К пользователю')
    is_accepted = models.BooleanField(default=False, verbose_name='Принята')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')

    class Meta:
        verbose_name = 'Контакт'
        verbose_name_plural = 'Контакты'

    def __str__(self):
        return f"Заявка на добавление в контакты от {self.from_user.email} для {self.to_user.email} ({self.created_at})"
    
class Location(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, verbose_name='Пользователь')
    latitude = models.FloatField(verbose_name='Широта')
    longitude = models.FloatField(verbose_name='Долгота')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Дата обновления')

    class Meta:
        verbose_name = 'Местоположение'
        verbose_name_plural = 'Местоположения'

    def __str__(self):
        return f"{self.user.email} (широта: {self.latitude}, долгота: {self.longitude}) - {self.updated_at}"

class SosSignal(models.Model):
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_sos', verbose_name='Отправитель')
    latitude = models.FloatField(verbose_name='Широта')
    longitude = models.FloatField(verbose_name='Долгота')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    is_active = models.BooleanField(default=True, verbose_name='Активен')

    class Meta:
        verbose_name = 'SOS сигнал'
        verbose_name_plural = 'SOS сигналы'

    def __str__(self):
        return f"{self.sender.email} (широта: {self.latitude}, долгота: {self.longitude}) - {self.created_at}"
    
class FavoriteContact(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='favorites', verbose_name='Пользователь')
    contact = models.ForeignKey(User, on_delete=models.CASCADE, related_name='favorited_by', verbose_name='Контакт')

    class Meta:
        unique_together = ("user", "contact")
        verbose_name = 'Избранный контакт'
        verbose_name_plural = 'Избранные контакты'

    def __str__(self):
        return f"{self.contact.email} в избранных у {self.user.email}"
    
class Keyword(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='keywords', verbose_name='Пользователь')
    word = models.CharField(max_length=255)

    class Meta:
        verbose_name = 'Ключевое слово'
        verbose_name_plural = 'Ключевые слова'

    def __str__(self):
        return f"{self.user.email} ({self.word})"