from django.urls import path

from .notifications.consumers import NotificationsConsumer
from .views import *




urlpatterns = [
    path('projects/', project_list_create, name='project-list-create'),
    path('my-projects/', my_projects, name='my-projects'),
    path('projects/<int:pk>/', project_retrieve, name='project-retrieve'),
    path('projects/update/<int:pk>/', project_update, name='project-update'),
    path('projects/delete/<int:pk>/', project_destroy, name='project-destroy'),
    path('project/<int:pk>/tasks/', ProjectTaskListView.as_view(), name='project-tasks'),


    path('projects/<int:project_id>/add-participant/', add_participant, name='add-participant'),
    path('projects/<int:project_id>/remove-participant/<int:user_id>/', remove_participant, name='remove-participant'),
    path('projects/<int:project_id>/update-role/<int:user_id>/', update_participant_role, name='update-participant-role'),


    path('task/', task_list_create, name='task-list-create'),
    path('my-tasks/', my_tasks, name='my-tasks'),
    path('task/<int:pk>/', task_retrieve, name='task-retrieve'),
    path('task/update/<int:pk>/', task_update, name='task-update'),
    path('task/delete/<int:pk>/', task_destroy, name='task-destroy'),
    path('tasks/<int:task_id>/assign/', assign_user_to_task, name='assign_user_to_task'),
    path('tasks/<int:pk>/unassign/', unassign_user_from_task, name='unassign_user_from_task'),
    path('task/filter/', TaskFilterView.as_view(), name='task-filter'),


    path('signup/', sign_up_user, name='sign-up-user'),
    path('login/', log_in_user, name='log-in-user'),
    path('logout/', log_out_user, name='log-out-user'),
    path('profile/', profile_view, name='profile-view'),


    path('comments/<int:task_id>/', comment_list_create, name='comment-list-create'),
    path('comments/<int:task_id>/<int:pk>/', comment_detail, name='comment-detail'),


    path('projects/filter/symbol/', ProjectSymbolFilterView.as_view(), name='filter-symbol'),
    path('projects/<int:project_id>/tasks/filter/', ProjectTaskFilterView.as_view(), name='project-task-filter'),
    path('projects/filter/date/', ProjectDateRangeFilterView.as_view(), name='project-date-sort'),


    path('ws/notifications/', NotificationsConsumer.as_asgi(), name='ws-notifications'),
]
from django.conf import settings
from django.conf.urls.static import static

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)