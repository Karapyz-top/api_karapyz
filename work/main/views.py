from datetime import datetime
from django.db.models.functions import Lower
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.generics import get_object_or_404
from rest_framework_simplejwt.tokens import RefreshToken
from .permissions import IsOwnerOrReadOnly
from .serializers import *
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, generics
from django.shortcuts import get_object_or_404
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from .models import Task, UserAPI
from rest_framework.filters import OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend
from .serializers import TaskSerializer
from django.db.models import Q

@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def project_list_create(request):
    """
    Получение списка проектов или создание нового проекта.

    GET:
    Возвращает список всех проектов.

    POST:
    Создает новый проект.
    Пример тела запроса:
    {
        "title": "Название проекта",
        "description": "Описание проекта"
    }
    """

    if request.method == 'GET':
        projects = Project.objects.all()
        serializer = ProjectSerializer(projects, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    if request.method == 'POST':
        data = request.data.copy()
        data['owner'] = request.user.id
        data['participants'] = [request.user.id]

        serializer = ProjectSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def my_projects(request):
    """
    Получение списка проектов, в которых участвует пользователь.

    GET:
    Возвращает список проектов текущего пользователя.
    """

    projects = Project.objects.filter(participants=request.user)
    serializer = ProjectSerializer(projects, many=True)
    return Response(serializer.data)


class ProjectTaskListView(APIView):
    """
       Фильтрация задач проекта по дате создания, обновления или дедлайну.
       """

    def get(self, request, pk, *args, **kwargs):
        """
            GET:
            Параметры:
            - project_id (int): ID проекта.
            - filter_by (str): Поле для фильтрации ("created", "updated" или "deadline"). По умолчанию "created".
            - start_date (str): Начальная дата фильтрации в формате YYYY-MM-DD.
            - end_date (str): Конечная дата фильтрации в формате YYYY-MM-DD.

            Ответы:
            - 200: Список задач, соответствующих критериям фильтрации.
            - 400: Ошибка в параметрах запроса (например, некорректный формат даты).
        """
        tasks = Task.objects.filter(project_id=pk)

        if not tasks.exists():
            return Response({"message": "No tasks found for this project."}, status=status.HTTP_200_OK)

        serializer = TaskSerializer(tasks, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def project_retrieve(request, pk):
    """
    Получение информации о проекте по его ID.

    GET:
    Параметры:
    - pk (int): ID проекта.

    Ответы:
    - 200: Детали проекта.
    - 404: Проект не найден.
    """

    project = get_object_or_404(Project, pk=pk)
    serializer = ProjectSerializer(project)
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(['PUT', 'PATCH'])
@permission_classes([IsOwnerOrReadOnly])
def project_update(request, pk):
    """
    Обновление информации о проекте.

    PUT или PATCH:
    Параметры:
    - pk (int): ID проекта для обновления.
    Пример тела запроса:
    {
        "title": "Новое название",
        "description": "Новое описание"
    }

    Ответы:
    - 200: Проект успешно обновлен.
    - 400: Ошибка валидации.
    """

    try:
        project = Project.objects.get(pk=pk)
    except Project.DoesNotExist:
        return Response({'detail': 'Project not found'}, status=status.HTTP_404_NOT_FOUND)
    data = request.data

    if 'owner' in data:
        del data['owner']
    serializer = ProjectSerializer(project, data=data, partial=True)

    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data)
    else:
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['DELETE'])
@permission_classes([IsOwnerOrReadOnly])
def project_destroy(request, pk):
    """
    Удаление проекта.

    DELETE:
    Параметры:
    - pk (int): ID проекта для удаления.

    Ответы:
    - 204: Проект успешно удален.
    - 404: Проект не найден.
    """

    project = get_object_or_404(Project, pk=pk)
    project.delete()
    return Response({'detail': 'Project deleted successfully'}, status=status.HTTP_204_NO_CONTENT)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def add_participant(request, project_id):
    """
    Добавление участника в проект.

    POST:
    Параметры:
    - project_id (int): ID проекта, в который добавляется участник.
    Пример тела запроса:
    {
        "user": 1,  # ID пользователя
        "role": "Developer"
    }

    Ответы:
    - 201: Участник успешно добавлен.
    - 403: Только владелец может добавлять участников.
    """

    try:
        project = Project.objects.get(id=project_id)
    except Project.DoesNotExist:
        return Response({'error': 'Project does not exist.'}, status=status.HTTP_404_NOT_FOUND)

    if request.user != project.owner:
        return Response({'error': 'Only the owner can add participants.'}, status=status.HTTP_403_FORBIDDEN)

    serializer = ProjectParticipantSerializer(data=request.data)
    if serializer.is_valid():
        participant = serializer.save(project=project)
        print(f"Добавление участника с user_id={participant.user.id}")

        send_websocket_notification(
            user_id=participant.user.id,
            message=f"Вы были добавлены в проект '{project.title}'."
        )

        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)



@api_view(['PATCH'])
def assign_user_to_task(request, task_id):
    """
    Назначение пользователя ответственным за задачу.
    """
    task = get_object_or_404(Task, id=task_id)
    user_id = request.data.get("user_id")

    if not user_id:
        return Response({"error": "user_id is required"}, status=status.HTTP_400_BAD_REQUEST)

    user = get_object_or_404(UserAPI, id=user_id)
    task.assigned_to = user
    task.save()


    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f"user_{user_id}",
        {
            "type": "send_notification",
            "message": f"Вы назначены ответственным за задачу '{task.title}'."
        }
    )

    serializer = TaskSerializer(task)
    return Response(serializer.data, status=status.HTTP_200_OK)

@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def remove_participant(request, project_id, user_id):
    """
    Удаление участника из проекта.

    DELETE:
    Параметры:
    - project_id (int): ID проекта.
    - user_id (int): ID участника для удаления.

    Ответы:
    - 204: Участник успешно удален.
    - 404: Проект или участник не найдены.
    """

    try:
        project = Project.objects.get(id=project_id)
    except Project.DoesNotExist:
        return Response({'error': 'Project does not exist.'}, status=status.HTTP_404_NOT_FOUND)

    if request.user != project.owner:
        return Response({'error': 'Only the owner can remove participants.'}, status=status.HTTP_403_FORBIDDEN)

    try:
        participant = ProjectParticipant.objects.get(project=project, user_id=user_id)
        participant.delete()
        return Response({'message': 'Participant removed.'}, status=status.HTTP_204_NO_CONTENT)
    except ProjectParticipant.DoesNotExist:
        return Response({'error': 'Participant not found.'}, status=status.HTTP_404_NOT_FOUND)


@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def update_participant_role(request, project_id, user_id):
    """
    Обновление роли участника в проекте.

    PATCH:
    Параметры:
    - project_id (int): ID проекта.
    - user_id (int): ID пользователя для изменения роли.
    Пример тела запроса:
    {
        "role": "Manager"
    }

    Ответы:
    - 200: Роль участника успешно обновлена.
    - 404: Проект или участник не найдены.
    """

    try:
        project = Project.objects.get(id=project_id)
    except Project.DoesNotExist:
        return Response({'error': 'Project does not exist.'}, status=status.HTTP_404_NOT_FOUND)

    if request.user != project.owner:
        return Response({'error': 'Only the owner can update roles.'}, status=status.HTTP_403_FORBIDDEN)

    try:
        participant = ProjectParticipant.objects.get(project=project, user_id=user_id)
    except ProjectParticipant.DoesNotExist:
        return Response({'error': 'Participant not found.'}, status=status.HTTP_404_NOT_FOUND)

    serializer = ProjectParticipantSerializer(participant, data=request.data, partial=True)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def task_list_create(request):
    """
    Получение списка задач или создание новой задачи.

    GET:
    Возвращает список всех задач.

    POST:
    Создает новую задачу.
    Пример тела запроса:
    {
        "title": "Название задачи",
        "description": "Описание задачи",
        "project": 1,  # ID проекта
        "status": "In Progress"
    }

    Ответы:
    - 201: Задача успешно создана.
    - 403: Пользователь не является участником проекта.
    """

    if request.method == 'GET':
        tasks = Task.objects.all()
        serializer = TaskSerializer(tasks, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    if request.method == 'POST':
        project_id = request.data.get('project')
        if not project_id:
            return Response({"error": "Project ID is required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            project = Project.objects.get(id=project_id)
        except Project.DoesNotExist:
            return Response({"error": "Project does not exist."}, status=status.HTTP_404_NOT_FOUND)

        if request.user not in project.participants.all():
            return Response({"error": "You are not a participant of this project."}, status=status.HTTP_403_FORBIDDEN)

        serializer = TaskSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def my_tasks(request):
    """
    Получение списка задач, в которых участвует пользователь.

    GET:
    Возвращает список задач для текущего пользователя.
    """

    tasks = Task.objects.filter(project__participants=request.user).distinct()
    serializer = TaskSerializer(tasks, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def task_retrieve(request, pk):
    """
    Получение информации о задаче по ее ID.

    GET:
    Параметры:
    - pk (int): ID задачи.

    Ответы:
    - 200: Детали задачи.
    - 404: Задача не найдена.
    """

    task = get_object_or_404(Task, pk=pk)
    serializer = TaskSerializer(task)
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(['PUT', 'PATCH'])
@permission_classes([IsOwnerOrReadOnly])
def task_update(request, pk):
    """
    Обновление информации о задаче.

    PUT или PATCH:
    Параметры:
    - pk (int): ID задачи для обновления.
    Пример тела запроса:
    {
        "title": "Новое название задачи",
        "content": "Новое описание задачи",
        "status": "Done"
    }

    Ответы:
    - 200: Задача успешно обновлена.
    - 400: Ошибка валидации.
    """

    task = get_object_or_404(Task, pk=pk)
    if request.method in ['PUT', 'PATCH']:
        serializer = TaskSerializer(task, data=request.data, partial=(request.method == 'PATCH'))
        if serializer.is_valid():
            updated_task = serializer.save()

            send_websocket_notification(
                user_id=updated_task.assigned_to,
                message=f"Статус задачи '{updated_task.title}' был изменен на '{updated_task.status}'."
            )

            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['DELETE'])
@permission_classes([IsOwnerOrReadOnly])
def task_destroy(request, pk):
    """
    Удаление задачи.

    DELETE:
    Параметры:
    - pk (int): ID задачи для удаления.

    Ответы:
    - 204: Задача успешно удалена.
    - 404: Задача не найдена.
    """

    task = get_object_or_404(Task, pk=pk)
    task.delete()
    return Response({'detail': 'Task deleted successfully'}, status=status.HTTP_204_NO_CONTENT)


@api_view(['GET', 'PUT'])
@permission_classes([IsAuthenticated])
def profile_view(request):
    """
    Получение или обновление профиля пользователя.

    GET:
    Возвращает данные профиля пользователя, включая активные и архивные проекты.

    PUT:
    Обновляет данные профиля пользователя.
    Пример тела запроса:
    {
        "name": "Новое имя",
        "avatar": "/path/to/avatar.jpg"
    }

    Ответы:
    - 200: Профиль успешно обновлен.
    """

    user = request.user

    if request.method == 'GET':
        active_projects = Project.objects.filter(participants=user, status=Project.Status.ACTIVE)
        archive_projects = Project.objects.filter(participants=user, status=Project.Status.ARCHIVE)

        active_projects_serializer = ProjectSerializer(active_projects, many=True)
        archive_projects_serializer = ProjectSerializer(archive_projects, many=True)

        return Response({
            'id': user.id,
            'name': user.name,
            'surname': user.surname,
            'avatar': user.avatar.url if user.avatar else None,
            'role': user.role,
            'active_projects': active_projects_serializer.data,
            'archive_projects': archive_projects_serializer.data,
        }, status=status.HTTP_200_OK)

    if request.method == 'PUT':
        serializer = ProfileUpdateSerializer(user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([AllowAny])
def log_in_user(request):
    """
    Авторизация пользователя и выдача токенов.

    POST:
    Пример тела запроса:
    {
        "email": "user@example.com",
        "password": "password123"
    }

    Ответы:
    - 200: Авторизация успешна, возвращены токены доступа и обновления.
    - 401: Ошибка авторизации.
    """

    serializer = LogSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    username = serializer.validated_data['email']
    password = serializer.validated_data['password']

    user = authenticate(username=username, password=password)

    if user is None:
        return Response(
            {"error": {"code": status.HTTP_401_UNAUTHORIZED,
                       "message": "Authentication failed"}},
            status=status.HTTP_401_UNAUTHORIZED
        )

    refresh = RefreshToken.for_user(user)
    return Response(
        {'data': {
            "refresh": str(refresh),
            "access": str(refresh.access_token)
        }},
        status=status.HTTP_200_OK
    )


@api_view(['POST'])
@permission_classes([AllowAny])
def sign_up_user(request):
    """
    Регистрация нового пользователя.

    POST:
    Пример тела запроса:
    {
        "name": "Имя",
        "surname": "Фамилия",
        "email": "user@example.com",
        "password": "password123",
        "role":"Backend"
    }

    Ответы:
    - 201: Пользователь успешно зарегистрирован, возвращены токены.
    """

    serializer = RegSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    user = serializer.save()
    refresh = RefreshToken.for_user(user)

    return Response(
        {'data': {
            "refresh": str(refresh),
            "access": str(refresh.access_token)
        }},
        status=status.HTTP_201_CREATED
    )


@api_view(['POST'])
def log_out_user(request):
    """
    Выход пользователя из системы путем аннулирования токена обновления.

    POST:
    Пример тела запроса:
    {
        "refresh": "строка токена обновления"
    }

    Ответы:
    - 200: Выход выполнен успешно.
    - 400: Неверный токен.
    """

    try:
        refresh_token = request.data["refresh"]
        token = RefreshToken(refresh_token)
        token.blacklist()
        return Response(
            {"data": {"message": "Logout successful"}},
            status=status.HTTP_200_OK
        )
    except Exception as e:
        return Response(
            {"error": {"code": status.HTTP_400_BAD_REQUEST,
                       "message": "Invalid token"}},
            status=status.HTTP_400_BAD_REQUEST
        )

@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def comment_list_create(request, task_id):
    """
    Получение списка комментариев или создание нового комментария.

    GET:
    Описание:
    - Получение всех комментариев, связанных с указанной задачей.

    POST:
    Описание:
    - Создание нового комментария к задаче.

    Параметры:
    - task_id (int): ID задачи (обязательно).

    Ответы:
    - 200: Успешное получение списка комментариев.
    - 201: Успешное создание комментария.
    - 400: Ошибка валидации данных.
    - 404: Указанная задача не найдена.
    """
    try:
        task = Task.objects.get(id=task_id)
    except Task.DoesNotExist:
        return Response({'error': 'Task not found'}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'POST':
        data = request.data
        data['task'] = task_id
        serializer = CommentSerializer(data=data, context={'request': request})
        if serializer.is_valid():
            comment = serializer.save(author=request.user)

            if task.assigned_to:
                send_websocket_notification(
                    user_id=task.assigned_to.id,
                    message=f"Комментарий добавлен к задаче '{task.title}': {comment.content}"
                )


            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    elif request.method == 'GET':
        comments = Comment.objects.filter(task=task)
        serializer = CommentSerializer(comments, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)



@api_view(['DELETE'])
def unassign_user_from_task(request, pk):
    """
    Удаление пользователя из задачи.
    """

    task = get_object_or_404(Task, pk=pk)


    if not task.assigned_to:
        return Response(
            {"error": "У задачи нет назначенного пользователя."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    user_id = task.assigned_to.id


    task.assigned_to = None
    task.save()


    send_websocket_notification(
        user_id=user_id,
        message=f"Вы больше не являетесь ответственным за задачу '{task.title}'."
    )
    print(f"WebSocket уведомление отправлено для user_id={user_id}: Пользователь удалён из задачи '{task.title}'.")


    serializer = TaskSerializer(task)
    return Response(serializer.data, status=status.HTTP_200_OK)

@api_view(['PUT', 'DELETE'])
@permission_classes([IsAuthenticated])
def comment_detail(request, task_id, pk):
    """
    Обновление или удаление конкретного комментария.

    PUT:
    Обновляет комментарий.
    Пример тела запроса:
    {
        "text": "Обновленный текст комментария."
    }

    DELETE:
    Удаляет комментарий.

    Ответы:
    - 200: Комментарий успешно обновлен.
    - 204: Комментарий успешно удален.
    """

    try:

        comment = Comment.objects.get(pk=pk, task_id=task_id)
    except Comment.DoesNotExist:
        return Response({'error': 'Comment not found'}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'PUT':
        if comment.author != request.user:
            return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)
        serializer = CommentSerializer(comment, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    if request.method == 'DELETE':
        if comment.author != request.user:
            return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)
        comment.delete()
        return Response({'message': 'Comment deleted successfully'}, status=status.HTTP_204_NO_CONTENT)


class ProjectSymbolFilterView(APIView):
    """
    Сортировка проектов от А до Я, от Я до А

    GET:
    Параметры:
    - sort_by (str): Поле для сортировки.
    - order (str): Направление сортировки ("asc" или "desc").

    Ответы:
    - 200: Список отсортированных проектов.
    - 400: Ошибка в параметрах запроса.
    """

    def get(self, request, *args, **kwargs):
        order = request.query_params.get('order')
        sort_by = request.query_params.get('sort_by')

        projects = Project.objects.all()

        if sort_by:
            if order == "desc":
                sort_by = f"-{sort_by}"
            projects = projects.order_by(sort_by)
        else:
            return Response({"error": "Missing sort_by parameter"}, status=status.HTTP_400_BAD_REQUEST)

        serializer = ProjectSerializer(projects, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)



class ProjectTaskFilterView(APIView):
    """
    Фильтрация задач проекта по дате создания, обновления или дедлайну с сортировкой.

    GET:
    Параметры:
    - project_id (int): ID проекта.
    - filter_by (str): Поле для фильтрации ("created", "updated" или "deadline"). По умолчанию "created".
    - start_date (str): Начальная дата фильтрации в формате YYYY-MM-DD.
    - end_date (str): Конечная дата фильтрации в формате YYYY-MM-DD.
    - order (str): Направление сортировки ("asc" или "desc"). По умолчанию "asc".

    Ответы:
    - 200: Список задач, соответствующих критериям фильтрации.
    - 400: Ошибка в параметрах запроса (например, некорректный формат даты).
    """

    def get(self, request, project_id, *args, **kwargs):
        # Получение параметров фильтрации
        filter_by = request.query_params.get('filter_by', 'created')
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        order = request.query_params.get('order', 'asc')

        # Проверка корректности параметров
        if filter_by not in ['created', 'updated', 'deadline']:
            return Response(
                {"error": "Invalid filter_by parameter. Use 'created', 'updated', or 'deadline'."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not (start_date and end_date):
            return Response(
                {"error": "Both start_date and end_date parameters are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if order not in ['asc', 'desc']:
            return Response(
                {"error": "Invalid order parameter. Use 'asc' or 'desc'."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Преобразование дат в объект datetime
        try:
            start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
            end_date = datetime.strptime(end_date, "%Y-%m-%d").date()
        except ValueError:
            return Response(
                {"error": "Invalid date format. Use YYYY-MM-DD."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Карта для полей сортировки
        field_map = {
            'created': 'created_at',
            'updated': 'updated_at',
            'deadline': 'deadline',
        }
        filter_field = field_map.get(filter_by)

        # Направление сортировки
        sort_order = '' if order == 'asc' else '-'

        # Фильтрация задач по проекту, дате и сортировке
        tasks = Task.objects.filter(
            Q(project_id=project_id) & Q(**{f"{filter_field}__range": (start_date, end_date)})
        ).order_by(f"{sort_order}{filter_field}")

        # Сериализация и отправка ответа
        serializer = TaskSerializer(tasks, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)




class ProjectDateRangeFilterView(APIView):
    """
    Фильтрация проектов по дате создания в указанном диапазоне.

    GET:
    Параметры:
    - start_date (str): Начальная дата в формате YYYY-MM-DD.
    - end_date (str): Конечная дата в формате YYYY-MM-DD.

    Ответы:
    - 200: Список проектов, соответствующих диапазону дат.
    - 400: Ошибка в параметрах запроса (например, некорректный формат даты).
    """

    def get(self, request, *args, **kwargs):
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')



        if not start_date or not end_date:
            return Response({"error": "Both start_date and end_date parameters are required."},
                            status=status.HTTP_400_BAD_REQUEST)

        try:
            start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
            end_date = datetime.strptime(end_date, "%Y-%m-%d").date()
        except ValueError:
            return Response({"error": "Invalid date format. Use YYYY-MM-DD."},
                            status=status.HTTP_400_BAD_REQUEST)


        projects = Project.objects.filter(time_created__range=(start_date, end_date))

        serializer = ProjectSerializer(projects, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


from django_filters import FilterSet


class TaskFilter(FilterSet):
    """
    Фильтрация задач по различным полям.

    Поля для фильтрации:
    - status: Фильтрация по статусу задачи.
    - priority: Фильтрация по приоритету задачи.
    - assigned_to: Фильтрация по ответственному за задачу.
    - created_at: Фильтрация по дате создания (можно использовать диапазон).
    - updated_at: Фильтрация по дате обновления (можно использовать диапазон).
    - title: Поиск по названию задачи (регистронезависимый поиск).
    """

    class Meta:
        model = Task
        fields = {
            'status': ['exact'],
            'priority': ['exact'],
            'assigned_to': ['exact'],
            'created_at': ['gte', 'lte'],
            'updated_at': ['gte', 'lte'],
            'title': ['icontains'],
        }


from django.db.models import Func, F


class TaskFilterView(generics.ListAPIView):
    """
    Фильтрация и сортировка задач.

    GET:
    Параметры:
    - ordering (str): Поле для сортировки ("title" для сортировки по названию).
      Возможны значения "title", "-title" и другие доступные поля.

    Ответы:
    - 200: Список отсортированных задач.
    """

    queryset = Task.objects.annotate(lower_title=Lower('title')).order_by('lower_title')
    serializer_class = TaskSerializer
    filter_backends = (DjangoFilterBackend, OrderingFilter)
    filterset_class = TaskFilter
    ordering_fields = ['title', 'created_at', 'updated_at', 'status', 'priority']
    ordering = ['created_at']


from .notifications.websocket_notifications import send_websocket_notification


def assign_to_project(user_id, project_id):
    """
    Назначение пользователя в проект.

    Функция отправляет уведомление пользователю о том, что он был назначен в проект.

    Параметры:
    - user_id (int): ID пользователя.
    - project_id (int): ID проекта.
    """

    send_websocket_notification(
        user_id=user_id,
        message=f"Вы были назначены в проект с ID {project_id}"
    )


def assign_task(user_id, task_id):
    send_websocket_notification(
        user_id=user_id,
        message=f"Вы назначены ответственным за задачу с ID {task_id}"
    )


def change_task_status(user_id, task_id, status):
    send_websocket_notification(
        user_id=user_id,
        message=f"Статус задачи с ID {task_id} был изменен на {status}"
    )


def add_comment(user_id, task_id, comment_text):
    send_websocket_notification(
        user_id=user_id,
        message=f"Комментарий к задаче с ID {task_id}: {comment_text}"
    )


from django.http import JsonResponse

