from django.test import TestCase
from django.urls import reverse
from django.test import Client
from django.contrib.auth.models import User
from people.models import Agent, Driver
from people.forms import AgentForm

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
        response = self.client.post(reverse('people:manage'), {
            'agent_form': '1',
            'name': 'New Agent'
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Agent.objects.filter(name='New Agent').exists())

    def test_edit_agent_view(self):
        agent = Agent.objects.create(name='Original Agent')
        response = self.client.post(reverse('people:edit_agent', args=[agent.id]), {'name': 'Updated Agent'})
        self.assertEqual(response.status_code, 302)
        agent.refresh_from_db()
        self.assertEqual(agent.name, 'Updated Agent')

    def test_delete_agent_view(self):
        agent = Agent.objects.create(name='Delete Agent')
        response = self.client.post(reverse('people:delete_agent', args=[agent.id]))
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Agent.objects.filter(name='Delete Agent').exists())

class DriverViewTest(TestCase):

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='12345')
        self.client.login(username='testuser', password='12345')

    def test_manage_view(self):
        response = self.client.get(reverse('people:manage'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'manage.html')

    def test_add_driver_view(self):
        response = self.client.post(reverse('people:manage'), {
            'driver_form': '1',
            'name': 'New Driver'
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Driver.objects.filter(name='New Driver').exists())

    def test_edit_driver_view(self):
        driver = Driver.objects.create(name='Original Driver')
        response = self.client.post(reverse('people:edit_driver', args=[driver.id]), {'name': 'Updated Driver'})
        self.assertEqual(response.status_code, 302)
        driver.refresh_from_db()
        self.assertEqual(driver.name, 'Updated Driver')

    def test_delete_driver_view(self):
        driver = Driver.objects.create(name='Delete Driver')
        response = self.client.post(reverse('people:delete_driver', args=[driver.id]))
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Driver.objects.filter(name='Delete Driver').exists())