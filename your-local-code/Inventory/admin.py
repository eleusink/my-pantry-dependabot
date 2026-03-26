from django.contrib import admin
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin
from .models import Ingredient

class IngredientInline(admin.TabularInline):
    model = Ingredient
    extra = 0
    feilds = (
            "name", 
            "quantity",
            "unit_measurement",
            "food_group",
            "date_obtained",
            "date_expired",
    )
    can_delete = True


# Re-register User to customize if needed
admin.site.unregister(User)

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    def ingredient_count(self,obj):
        return obj.ingredients.count()
    ingredient_count.short_description = "Items"

    inlines = [IngredientInline]
    list_display = ("username", "first_name", "last_name", "email", "ingredient_count", "is_staff", "is_superuser", "is_active")
    search_fields = ("username", "first_name", "last_name", "email")
    list_filter = ("is_staff", "is_superuser", "is_active")

admin.site.site_header = "MyPantry Admin"
admin.site.site_title = "MyPantry Admin Portal"
admin.site.index_title = "Welcome to MyPantry Administration"
