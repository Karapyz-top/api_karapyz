from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.models import PermissionsMixin
from django.db import models
from django.conf import settings


class Project(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "AC", 'Active'
        ARCHIVE = 'AR', "Archive"

    title = models.CharField(max_length=255)
    content = models.TextField()
    time_created = models.DateTimeField(auto_now_add=True)
    time_updated = models.DateTimeField(auto_now=True)
    status = models.CharField(max_length=2, choices=Status.choices, default=Status.ACTIVE)
    participants = models.ManyToManyField(settings.AUTH_USER_MODEL, through="main.ProjectParticipant",
                                          related_name='projects')
    owner = models.ForeignKey("main.UserAPI", on_delete=models.CASCADE, related_name="owned_projects")

    def __str__(self):
        return self.title


class ProjectParticipant(models.Model):
    ROLE_CHOICES = [
        ('owner', 'Owner'),
        ('developer', 'Developer'),
        ('Backend', 'Backend'),
        ('Frontend', 'Frontend'),
        ('Fullstack', 'Fullstack'),
        ('Designer', 'Designer'),
        ('Tester', 'Tester'),
        ('Analyst', 'Analyst'),
        ('Product Manager', 'Product Manager')
    ]
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='project_participations')
    project = models.ForeignKey('Project', on_delete=models.CASCADE, related_name='participants_project')
    role = models.CharField(max_length=50, choices=ROLE_CHOICES, default='developer')

    class Meta:
        unique_together = ('user', 'project')


class Task(models.Model):
    title = models.CharField(max_length=255)
    content = models.TextField()
    project = models.ForeignKey('Project', on_delete=models.CASCADE, related_name='tasks')
    assigned_to = models.ForeignKeyassigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_tasks"
    )
    status = models.CharField(max_length=50, choices=[
        ('Grooming', 'Grooming'),
        ('In Progress', 'In Progress'),
        ('Dev', 'Development'),
        ('Done', 'Done')
    ])
    priority = models.CharField(max_length=50, choices=[
        ('Low', 'Low'),
        ('Medium', 'Medium'),
        ('High', 'High')
    ])
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deadline = models.DateTimeField(null=True, blank=True)
    testing_responsible = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='testing_tasks',
        verbose_name='Ответственный за тестирование'
    )

    def __str__(self):
        return self.title


class Comment(models.Model):
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='comments')
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='comments')
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Comment by {self.author} on {self.task}"


class UserManager(BaseUserManager):
    def create_user(self, email, name, surname, password=None, **extra_fields):
        if not email:
            raise ValueError("The Email field must be set")
        email = self.normalize_email(email)
        user = self.model(email=email, name=name, surname=surname, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, name, surname, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get('is_superuser') is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self.create_user(email, name, surname, password, **extra_fields)

    def get_by_natural_key(self, email):
        return self.get(email=email)


class UserAPI(AbstractBaseUser, PermissionsMixin):
    ROLE_CHOICES = [
        ('Backend', 'Backend'),
        ('Frontend', 'Frontend'),
        ('Fullstack', 'Fullstack'),
        ('Designer', 'Designer'),
        ('Tester', 'Tester'),
        ('Analyst', 'Analyst'),
        ('Product Manager', 'Product Manager')

    ]

    email = models.EmailField(unique=True)
    name = models.CharField(max_length=255)
    surname = models.CharField(max_length=255)
    role = models.CharField(max_length=50, choices=ROLE_CHOICES, default='Backend')
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    avatar = models.ImageField(upload_to='avatars/', default='avatars/default.jpg', blank=True)

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['name', 'surname']

    def __str__(self):
        return f"{self.name} {self.surname} ({self.role})"

    def natural_key(self):
        return (self.email,)
