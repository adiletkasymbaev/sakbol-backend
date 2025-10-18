from django.contrib import admin
from .models import *
from django.contrib.auth.admin import UserAdmin

admin.site.register(User)
admin.site.register(Contact)
admin.site.register(Location)
admin.site.register(SosSignal)
admin.site.register(FavoriteContact)