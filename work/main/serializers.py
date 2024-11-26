from django.contrib.auth import authenticate
from rest_framework.generics import ListAPIView

from .models import Task, UserAPI, Comment, ProjectParticipant
from django.contrib.auth import get_user_model
from rest_framework import serializers
from .models import Project


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserAPI
        fields = ['name']


class ProjectSerializer(serializers.ModelSerializer):
    participants = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=UserAPI.objects.all()
    )
    owner = serializers.PrimaryKeyRelatedField(
        queryset=UserAPI.objects.all()
    )

    class Meta:
        model = Project
        fields = ['id', 'title', 'content', 'status', 'participants', 'owner', 'time_created', 'time_updated']


class ProjectParticipantSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProjectParticipant
        fields = ['user', 'role']


class ProfileView(serializers.ModelSerializer):
    active_projects = serializers.SerializerMethodField()
    completed_projects = serializers.SerializerMethodField()

    class Meta:
        model = UserAPI
        fields = ['name', 'surname', 'avatar', 'role', 'active_projects', 'completed_projects']

    def get_active_projects(self, obj):
        active_projects = Project.objects.filter(owner=obj, status='Active')
        return [project.title for project in active_projects]

    def get_completed_projects(self, obj):
        completed_projects = Project.objects.filter(owner=obj, status='Archive')
        return [project.title for project in completed_projects]

    def update(self, instance, validated_data):
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance


class ProfileUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserAPI
        fields = ['name', 'surname', 'avatar', 'role']


class TaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = Task
        fields = ['id', 'title', 'content', 'project', 'assigned_to', 'status', 'priority', 'created_at',
                  'updated_at', 'deadline', 'testing_responsible', ]




class CommentSerializer(serializers.ModelSerializer):
    task = serializers.PrimaryKeyRelatedField(queryset=Task.objects.all(), write_only=True)
    author = serializers.SerializerMethodField()

    class Meta:
        model = Comment
        fields = ['id', 'task', 'content', 'author', 'created_at']

    def get_author(self, obj):
        return f"{obj.author.name} {obj.author.surname}"


class AssignUserToTaskSerializer(serializers.Serializer):
    user_id = serializers.IntegerField()


class LogSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        email = attrs.get('email')
        password = attrs.get('password')

        if email and password:
            user = authenticate(
                request=self.context.get('request'),
                email=email,
                password=password
            )
            if not user:
                raise serializers.ValidationError(
                    {"detail": "Invalid credentials"}
                )
        else:
            raise serializers.ValidationError(
                {"detail": "Email and password are required"}
            )

        attrs['user'] = user
        return attrs


from rest_framework import serializers
from .models import UserAPI


class RegSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True,
        min_length=12,
        error_messages={
            "min_length": "Password must be at least 12 characters long."
        },
    )

    class Meta:
        model = UserAPI
        fields = ['email', 'password', 'name', 'surname', 'role', 'avatar']

    def create(self, validated_data):
        avatar = validated_data.pop('avatar', None)
        user = UserAPI(
            email=validated_data['email'],
            name=validated_data['name'],
            surname=validated_data['surname'],
            role=validated_data['role']
        )
        user.set_password(validated_data['password'])
        if avatar:
            user.avatar = avatar
        user.save()
        return user



from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters


class TaskFilterView(ListAPIView):
    queryset = Task.objects.all()
    serializer_class = TaskSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    ordering_fields = ['title']
    ordering = ['title']
