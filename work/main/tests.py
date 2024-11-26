from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from .models import Project, Task, UserAPI, ProjectParticipant, Comment


class AuthTests(APITestCase):
    def setUp(self):
        self.user = UserAPI.objects.create_user(
            email='testuser@example.com',
            name='Test',
            surname='User',
            password='testpassword123'
        )

    def test_signup(self):
        signup_data = {
            'email': 'newuser@example.com',
            'password': 'newpassword123',
            'name': 'New',
            'surname': 'User',
            'role': 'Backend'
        }
        response = self.client.post(reverse('sign-up-user'), data=signup_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_login(self):
        login_data = {
            'email': 'testuser@example.com',
            'password': 'testpassword123'
        }
        response = self.client.post(reverse('log-in-user'), data=login_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data['data'])

class ProjectTests(APITestCase):
    def setUp(self):
        self.user = UserAPI.objects.create_user(
            email='testuser@example.com',
            name='Test',
            surname='User',
            password='testpassword123',
            role='Backend'
        )
        self.other_user = UserAPI.objects.create_user(
            email='otheruser@example.com',
            name='Other',
            surname='User',
            password='testpassword123',
            role='Frontend'
        )
        self.client.force_authenticate(self.user)
        self.project_data = {
            'title': 'Test Project',
            'content': 'Project description',
            'status': 'AC',
            'owner': self.user.id
        }

    def test_create_project(self):
        response = self.client.post(reverse('project-list-create'), data=self.project_data, format='json')

        if response.status_code != status.HTTP_201_CREATED:
            print("Response data:", response.data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['title'], self.project_data['title'])
        self.assertEqual(response.data['owner'], self.user.id)

    def test_add_participant(self):
        project = Project.objects.create(
            title='Test Project',
            content='Project description',
            owner=self.user
        )
        data = {'user': self.user.id, 'role': 'developer'}
        response = self.client.post(
            reverse('add-participant', kwargs={'project_id': project.id}),
            data=data, format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)


class TaskTests(APITestCase):
    def setUp(self):
        self.user = UserAPI.objects.create_user(
            email='testuser@example.com',
            name='Test',
            surname='User',
            password='testpassword123',
            role='Backend'
        )
        self.client.force_authenticate(self.user)
        self.project = Project.objects.create(
            title='Test Project',
            content='Project description',
            owner=self.user
        )
        self.project.participants.add(self.user)
        self.task_data = {
            'title': 'Test Task',
            'content': 'Task description',
            'project': self.project.id,
            'status': 'In Progress',
            'priority': 'Medium'
        }

    def test_create_task(self):
        response = self.client.post(reverse('task-list-create'), data=self.task_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['title'], self.task_data['title'])

    def test_update_task(self):
        # Создаем задачу
        task = Task.objects.create(
            project=self.project,
            title=self.task_data['title'],
            content=self.task_data['content'],
            status=self.task_data['status'],
            priority=self.task_data['priority']
        )
        # Обновляем задачу
        update_data = {'title': 'Updated Task'}
        response = self.client.patch(
            reverse('task-update', kwargs={'pk': task.id}),
            data=update_data, format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['title'], 'Updated Task')


class ParticipantTests(APITestCase):
    def setUp(self):
        self.owner = UserAPI.objects.create_user(
            email='owner@example.com',
            name='Owner',
            surname='User',
            password='ownerpassword123',
            role='Backend'
        )
        self.participant = UserAPI.objects.create_user(
            email='participant@example.com',
            name='Participant',
            surname='User',
            password='participantpassword123',
            role='Frontend'
        )
        self.client.force_authenticate(self.owner)
        self.project = Project.objects.create(
            title='Owner Project',
            content='Description of owner project',
            owner=self.owner,
            status='AC'
        )

    def test_add_participant(self):
        data = {
            'user': self.participant.id,
            'role': 'Frontend'
        }
        url = reverse('add-participant', kwargs={'project_id': self.project.id})
        response = self.client.post(url, data=data, format='json')
        if response.status_code != status.HTTP_201_CREATED:
            print("Response data:", response.data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['user'], self.participant.id)
        self.assertEqual(response.data['role'], 'Frontend')


class CommentTests(APITestCase):
    def setUp(self):
        self.user = UserAPI.objects.create_user(
            email='testuser@example.com',
            name='Test',
            surname='User',
            password='testpassword123',
            role='Backend'
        )
        self.client.force_authenticate(self.user)
        self.project = Project.objects.create(
            title='Test Project',
            content='Project description',
            owner=self.user
        )
        self.project.participants.add(self.user)
        self.task = Task.objects.create(
            title='Test Task',
            content='Task description',
            project=self.project,
            status='In Progress',
            priority='Medium'
        )
        self.comment_data = {
            'task': self.task.id,
            'content': 'Test Comment'
        }

    def test_create_comment(self):
        response = self.client.post(
            reverse('comment-list-create', kwargs={'task_id': self.task.id}),
            data=self.comment_data, format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['content'], self.comment_data['content'])

    def test_update_comment(self):
        # Создаем комментарий
        comment = Comment.objects.create(task=self.task, author=self.user, content='Original Comment')
        # Обновляем комментарий
        update_data = {'content': 'Updated Comment'}
        response = self.client.put(
            reverse('comment-detail', kwargs={'task_id': self.task.id, 'pk': comment.id}),
            data=update_data, format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['content'], 'Updated Comment')

