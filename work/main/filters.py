from django_filters import rest_framework as filters
from .models import Project, Task

class ProjectFilter(filters.FilterSet):
    title = filters.CharFilter(lookup_expr='icontains')
    time_created = filters.DateFromToRangeFilter()
    time_updated = filters.DateFromToRangeFilter()

    class Meta:
        model = Project
        fields = ['title', 'time_created', 'time_updated']

class TaskFilter(filters.FilterSet):
    status = filters.CharFilter(field_name='status', lookup_expr='exact')
    priority = filters.CharFilter(field_name='priority', lookup_expr='exact')
    assigned_to = filters.NumberFilter(field_name='assigned_to', lookup_expr='exact')
    title = filters.CharFilter(field_name='title', lookup_expr='icontains')
    created_at = filters.DateFromToRangeFilter(field_name='created_at')
    updated_at = filters.DateFromToRangeFilter(field_name='updated_at')

    class Meta:
        model = Task
        fields = ['status', 'priority', 'assigned_to', 'created_at', 'updated_at', 'title']

