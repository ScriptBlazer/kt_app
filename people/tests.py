from django.test import TestCase
from django.urls import reverse
from django.test import Client
from django.contrib.auth.models import User
from .models import Agent
from .forms import AgentForm

class AgentFormTest(TestCase):

    def setUp(self):
        self.valid_data = {
            'name': 'Test Agent'
        }

    def test_agent_form_valid(self):
        form = AgentForm(data=self.valid_data)
        self.assertTrue(form.is_valid())

    def test_agent_form_missing_required_fields(self):
        invalid_data = {}
        form = AgentForm(data=invalid_data)
        self.assertFalse(form.is_valid())
        self.assertIn('name', form.errors)

class AgentViewTest(TestCase):

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='12345')
        self.client.login(username='testuser', password='12345')

    def test_manage_view(self):
        response = self.client.get(reverse('people:manage'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'manage.html')

    def test_add_agent_view(self):
        response = self.client.post(reverse('people:manage'), {'name': 'New Agent'})
        self.assertEqual(response.status_code, 302)  # Redirect after successful post
        self.assertTrue(Agent.objects.filter(name='New Agent').exists())

    def test_edit_agent_view(self):
        agent = Agent.objects.create(name='Original Agent')
        response = self.client.post(reverse('people:edit_agent', args=[agent.id]), {'name': 'Updated Agent'})
        self.assertEqual(response.status_code, 302)  # Redirect after successful post
        agent.refresh_from_db()
        self.assertEqual(agent.name, 'Updated Agent')

    def test_delete_agent_view(self):
        agent = Agent.objects.create(name='Delete Agent')
        response = self.client.post(reverse('people:delete_agent', args=[agent.id]))
        self.assertEqual(response.status_code, 302)  # Redirect after successful post
        self.assertFalse(Agent.objects.filter(name='Delete Agent').exists())