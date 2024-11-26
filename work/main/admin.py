from django.contrib import admin
from .models import Project, Task

@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ['title', 'status', 'time_created']

    def formfield_for_many_to_many(self, db_field, request, **kwargs):
        if db_field.name == 'participants':

            kwargs['queryset'] = self.get_queryset_for_participants(request)
        return super().formfield_for_many_to_many(db_field, request, **kwargs)

    def get_queryset_for_participants(self, request):

        from django.contrib.auth import get_user_model
        User = get_user_model()
        return User.objects.filter(is_active=True)


admin.site.register(Task)
