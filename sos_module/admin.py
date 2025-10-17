from django.contrib import admin
from .models import *

admin.site.register(User)
admin.site.register(Contact)
admin.site.register(Location)
admin.site.register(SosSignal)
admin.site.register(FavoriteContact)