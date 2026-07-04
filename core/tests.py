from django.test import TestCase
from django.urls import reverse
from accounts.models import User, Delegate, Specialty
from core.models import PharmaceuticalCompany

class PortalSettingsTests(TestCase):
    def setUp(self):
        # Create user profiles and users
        self.company_user = User.objects.create_user(
            username='company_user', password='password123', type=User.Types.COMPANY, email='c@c.com', phone='111'
        )
        self.company_profile = PharmaceuticalCompany.objects.create(
            user=self.company_user,
            name="Test Pharma Co",
            contact_person="Alice",
            phone="111",
            email="c@c.com",
            address="Cairo, Egypt"
        )

        self.delegate_user = User.objects.create_user(
            username='delegate_user', password='password123', type=User.Types.DELEGATE, email='del@del.com', phone='222'
        )
        self.delegate_profile = Delegate.objects.create(
            user=self.delegate_user,
            name="Test Delegate",
            phone="222"
        )

        self.other_user = User.objects.create_user(
            username='other_user', password='password123', type=User.Types.DOCTOR, email='doc@doc.com', phone='333'
        )

    def test_company_portal_access_control(self):
        # Unauthenticated redirects to login
        response = self.client.get(reverse('custom_company_portal'))
        self.assertEqual(response.status_code, 302)

        # Unauthorized user redirects to home
        self.client.login(username='other_user', password='password123')
        response = self.client.get(reverse('custom_company_portal'))
        self.assertEqual(response.status_code, 302)
        self.client.logout()

        # Authorized user succeeds
        self.client.login(username='company_user', password='password123')
        response = self.client.get(reverse('custom_company_portal'))
        self.assertEqual(response.status_code, 200)

    def test_delegate_portal_access_control(self):
        # Unauthenticated redirects to login
        response = self.client.get(reverse('custom_delegate_portal'))
        self.assertEqual(response.status_code, 302)

        # Unauthorized user redirects to home
        self.client.login(username='other_user', password='password123')
        response = self.client.get(reverse('custom_delegate_portal'))
        self.assertEqual(response.status_code, 302)
        self.client.logout()

        # Authorized user succeeds
        self.client.login(username='delegate_user', password='password123')
        response = self.client.get(reverse('custom_delegate_portal'))
        self.assertEqual(response.status_code, 200)

    def test_company_settings_update_profile(self):
        self.client.login(username='company_user', password='password123')
        
        # Test GET settings page
        response = self.client.get(reverse('company_portal_settings'))
        self.assertEqual(response.status_code, 200)

        # Test POST update profile details
        response = self.client.post(reverse('company_portal_settings'), {
            'action': 'update_profile',
            'contact_person': 'Bob',
            'phone': '111444',
            'email': 'bob@c.com',
            'address': 'Giza, Egypt'
        })
        self.assertEqual(response.status_code, 302) # Redirects back to settings
        
        self.company_profile.refresh_from_db()
        self.company_user.refresh_from_db()
        self.assertEqual(self.company_profile.contact_person, 'Bob')
        self.assertEqual(self.company_profile.phone, '111444')
        self.assertEqual(self.company_profile.email, 'bob@c.com')
        self.assertEqual(self.company_profile.address, 'Giza, Egypt')
        self.assertEqual(self.company_user.phone, '111444')
        self.assertEqual(self.company_user.email, 'bob@c.com')

    def test_delegate_settings_update_profile(self):
        self.client.login(username='delegate_user', password='password123')
        
        # Test GET settings page
        response = self.client.get(reverse('delegate_portal_settings'))
        self.assertEqual(response.status_code, 200)

        # Test POST update profile details
        response = self.client.post(reverse('delegate_portal_settings'), {
            'action': 'update_profile',
            'name': 'Updated Delegate Name',
            'phone': '222555'
        })
        self.assertEqual(response.status_code, 302) # Redirects back to settings
        
        self.delegate_profile.refresh_from_db()
        self.delegate_user.refresh_from_db()
        self.assertEqual(self.delegate_profile.name, 'Updated Delegate Name')
        self.assertEqual(self.delegate_profile.phone, '222555')
        self.assertEqual(self.delegate_user.phone, '222555')

    def test_change_password(self):
        self.client.login(username='company_user', password='password123')
        
        # Test POST change password
        response = self.client.post(reverse('company_portal_settings'), {
            'action': 'change_password',
            'new_password': 'newpassword123',
            'confirm_password': 'newpassword123'
        })
        self.assertEqual(response.status_code, 302)

        # Verify password changed
        self.client.logout()
        login_success = self.client.login(username='company_user', password='newpassword123')
        self.assertTrue(login_success)
