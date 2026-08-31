import uuid
from datetime import date, timedelta

from django.test import SimpleTestCase, TestCase
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from core.models import User
from people.models import Person, Tag, normalize_name


class NormalizeNameTests(SimpleTestCase):
    def test_lowercases(self):
        self.assertEqual(normalize_name('JOHN SMITH'), 'john smith')

    def test_strips_accents(self):
        self.assertEqual(normalize_name('José García'), 'jose garcia')

    def test_removes_punctuation(self):
        self.assertEqual(normalize_name("O'Brien-Jones Jr."), 'obrienjones jr')

    def test_collapses_whitespace(self):
        self.assertEqual(normalize_name('  Ana   María  '), 'ana maria')

    def test_empty_string(self):
        self.assertEqual(normalize_name(''), '')


class PersonModelTests(TestCase):
    def test_dob_populates_day_and_month_of_birth(self):
        person = Person.objects.create(name='Test Person', dob=date(1990, 7, 15))
        self.assertEqual(person.day_of_birth, 15)
        self.assertEqual(person.month_of_birth, 7)

    def test_missing_dob_leaves_day_and_month_of_birth_null(self):
        person = Person.objects.create(name='No Dob')
        self.assertIsNone(person.day_of_birth)
        self.assertIsNone(person.month_of_birth)

    def test_clearing_dob_clears_day_and_month_of_birth(self):
        person = Person.objects.create(name='Test Person', dob=date(1990, 7, 15))
        person.dob = None
        person.save()
        self.assertIsNone(person.day_of_birth)
        self.assertIsNone(person.month_of_birth)

    def test_normalized_name_is_derived_on_save(self):
        person = Person.objects.create(name="José O'Brien")
        self.assertEqual(person.normalized_name, 'jose obrien')

    def test_soft_delete_sets_deleted_at_but_keeps_the_row(self):
        person = Person.objects.create(name='Deleted Person')
        person.delete()
        self.assertIsNotNone(person.deleted_at)
        self.assertTrue(Person.objects.filter(pk=person.pk).exists())
        self.assertFalse(Person.objects.filter(pk=person.pk, deleted_at__isnull=True).exists())


class PersonAPITests(APITestCase):
    def setUp(self):
        self.staff_user = User.objects.create_user(email='staff@example.com', password='pw', is_staff=True)
        self.regular_user = User.objects.create_user(email='regular@example.com', password='pw')
        self.tag = Tag.objects.create(name='vip')

    def test_list_requires_authentication(self):
        response = self.client.get('/api/people/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_regular_user_cannot_create_person(self):
        self.client.force_authenticate(self.regular_user)
        response = self.client.post('/api/people/', {'name': 'New Person'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_staff_user_can_create_person(self):
        self.client.force_authenticate(self.staff_user)
        response = self.client.post(
            '/api/people/', {'name': 'New Person', 'tags': [str(self.tag.id)]}, format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['name'], 'New Person')
        self.assertEqual(response.data['normalized_name'], 'new person')

    def test_regular_user_can_update_and_delete_person(self):
        person = Person.objects.create(name='Existing Person')
        self.client.force_authenticate(self.regular_user)

        response = self.client.patch(f'/api/people/{person.id}/', {'name': 'Updated Name'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['normalized_name'], 'updated name')

        response = self.client.delete(f'/api/people/{person.id}/')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_retrieve_returns_computed_age(self):
        today = timezone.localdate()
        dob = date(today.year - 30, 1, 1)
        person = Person.objects.create(name='Birthday Person', dob=dob)

        self.client.force_authenticate(self.regular_user)
        response = self.client.get(f'/api/people/{person.id}/')
        self.assertEqual(response.data['age'], 30)

    def test_retrieve_returns_null_age_when_dob_missing(self):
        person = Person.objects.create(name='No Dob Person')
        self.client.force_authenticate(self.regular_user)
        response = self.client.get(f'/api/people/{person.id}/')
        self.assertIsNone(response.data['age'])

    def test_deleted_person_is_soft_deleted_and_excluded_from_api(self):
        person = Person.objects.create(name='To Delete')
        self.client.force_authenticate(self.regular_user)
        self.client.delete(f'/api/people/{person.id}/')

        person.refresh_from_db()
        self.assertIsNotNone(person.deleted_at)

        list_response = self.client.get('/api/people/')
        names = [p['name'] for p in list_response.data['results']]
        self.assertNotIn('To Delete', names)

        detail_response = self.client.get(f'/api/people/{person.id}/')
        self.assertEqual(detail_response.status_code, status.HTTP_404_NOT_FOUND)

    def test_cannot_assign_nonexistent_tag(self):
        self.client.force_authenticate(self.staff_user)
        response = self.client.post(
            '/api/people/', {'name': 'Tagged', 'tags': [str(uuid.uuid4())]}, format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('tags', response.data)

    def test_cannot_assign_soft_deleted_tag(self):
        deleted_tag = Tag.objects.create(name='obsolete')
        deleted_tag.delete()
        self.client.force_authenticate(self.staff_user)
        response = self.client.post(
            '/api/people/', {'name': 'Tagged', 'tags': [str(deleted_tag.id)]}, format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_search_by_single_tag(self):
        vip_person = Person.objects.create(name='VIP Person')
        vip_person.tags.set([self.tag])
        Person.objects.create(name='Other Person')

        self.client.force_authenticate(self.regular_user)
        response = self.client.get('/api/people/', {'tags': 'vip'})
        names = [p['name'] for p in response.data['results']]
        self.assertIn('VIP Person', names)
        self.assertNotIn('Other Person', names)

    def test_search_by_multiple_tags_is_or(self):
        donor_tag = Tag.objects.create(name='donor')
        alice = Person.objects.create(name='Alice')
        alice.tags.set([self.tag])
        bob = Person.objects.create(name='Bob')
        bob.tags.set([donor_tag])
        Person.objects.create(name='Cara')

        self.client.force_authenticate(self.regular_user)
        response = self.client.get('/api/people/', {'tags': 'vip,donor'})
        names = sorted(p['name'] for p in response.data['results'])
        self.assertEqual(names, ['Alice', 'Bob'])

    def test_list_is_ordered_by_name(self):
        Person.objects.create(name='Charlie')
        Person.objects.create(name='Alice')
        Person.objects.create(name='Bob')

        self.client.force_authenticate(self.regular_user)
        response = self.client.get('/api/people/')
        names = [p['name'] for p in response.data['results']]
        self.assertEqual(names, ['Alice', 'Bob', 'Charlie'])

    def test_list_returns_full_tag_details(self):
        vip_person = Person.objects.create(name='VIP Person')
        vip_person.tags.set([self.tag])

        self.client.force_authenticate(self.regular_user)
        response = self.client.get('/api/people/')
        person_data = next(p for p in response.data['results'] if p['name'] == 'VIP Person')
        self.assertEqual(person_data['tags'], [{
            'id': str(self.tag.id),
            'name': self.tag.name,
            'created_at': person_data['tags'][0]['created_at'],
            'updated_at': person_data['tags'][0]['updated_at'],
        }])

    def test_list_excludes_soft_deleted_tags_from_tag_details(self):
        deleted_tag = Tag.objects.create(name='obsolete')
        person = Person.objects.create(name='Tagged Person')
        person.tags.set([self.tag, deleted_tag])
        deleted_tag.delete()

        self.client.force_authenticate(self.regular_user)
        response = self.client.get('/api/people/')
        person_data = next(p for p in response.data['results'] if p['name'] == 'Tagged Person')
        tag_names = [t['name'] for t in person_data['tags']]
        self.assertEqual(tag_names, ['vip'])

    def test_list_pagination_page_and_size(self):
        for i in range(5):
            Person.objects.create(name=f'Person {i}')

        self.client.force_authenticate(self.regular_user)
        response = self.client.get('/api/people/', {'size': 2, 'page': 2})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 5)
        self.assertEqual(len(response.data['results']), 2)
        names = [p['name'] for p in response.data['results']]
        self.assertEqual(names, ['Person 2', 'Person 3'])

    def test_birthdays_requires_authentication(self):
        response = self.client.get('/api/people/birthdays/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_birthdays_returns_current_and_next_week(self):
        today = timezone.localdate()
        current_monday = today - timedelta(days=today.weekday())
        current_sunday = current_monday + timedelta(days=6)
        next_monday = current_monday + timedelta(days=7)
        outside_date = current_monday - timedelta(days=1)

        def dob_for(d):
            return date(2000, d.month, d.day)

        Person.objects.create(name='Current Birthday', dob=dob_for(current_sunday))
        Person.objects.create(name='Next Birthday', dob=dob_for(next_monday))
        Person.objects.create(name='Outside Birthday', dob=dob_for(outside_date))

        self.client.force_authenticate(self.regular_user)
        response = self.client.get('/api/people/birthdays/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        current_names = [p['name'] for p in response.data['current']]
        next_names = [p['name'] for p in response.data['next']]
        self.assertIn('Current Birthday', current_names)
        self.assertIn('Next Birthday', next_names)
        self.assertIn('age', response.data['current'][0])
        self.assertNotIn('Current Birthday', next_names)
        self.assertNotIn('Next Birthday', current_names)
        self.assertNotIn('Outside Birthday', current_names + next_names)

    def test_birthdays_excludes_deleted_people(self):
        today = timezone.localdate()
        current_monday = today - timedelta(days=today.weekday())
        deleted_person = Person.objects.create(name='Deleted Birthday', dob=date(2000, current_monday.month, current_monday.day))
        deleted_person.delete()

        self.client.force_authenticate(self.regular_user)
        response = self.client.get('/api/people/birthdays/')
        current_names = [p['name'] for p in response.data['current']]
        self.assertNotIn('Deleted Birthday', current_names)


class TagAPITests(APITestCase):
    def setUp(self):
        self.staff_user = User.objects.create_user(email='staff@example.com', password='pw', is_staff=True)
        self.regular_user = User.objects.create_user(email='regular@example.com', password='pw')

    def test_regular_user_cannot_create_tag(self):
        self.client.force_authenticate(self.regular_user)
        response = self.client.post('/api/people/tags/', {'name': 'vip'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_staff_user_can_create_tag(self):
        self.client.force_authenticate(self.staff_user)
        response = self.client.post('/api/people/tags/', {'name': 'vip'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_duplicate_tag_name_is_rejected(self):
        Tag.objects.create(name='vip')
        self.client.force_authenticate(self.staff_user)
        response = self.client.post('/api/people/tags/', {'name': 'vip'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_regular_user_can_list_tags(self):
        Tag.objects.create(name='vip')
        self.client.force_authenticate(self.regular_user)
        response = self.client.get('/api/people/tags/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_deleted_tag_excluded_from_list(self):
        tag = Tag.objects.create(name='obsolete')
        tag.delete()
        self.client.force_authenticate(self.regular_user)
        response = self.client.get('/api/people/tags/')
        names = [t['name'] for t in response.data]
        self.assertNotIn('obsolete', names)

    def test_tags_route_is_not_shadowed_by_person_detail_route(self):
        self.client.force_authenticate(self.regular_user)
        response = self.client.get('/api/people/tags/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.data, list)
