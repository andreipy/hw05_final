from django.contrib.auth import get_user_model
from django.test import TestCase

from ..models import Group, Post

User = get_user_model()


class PostModelTest(TestCase):

    def test_model_post_have_correct_object_names(self):
        """Проверяем, что у модели Post корректно работает __str__."""
        post_field_verboses = {
            'text': 'Текст',
            'created': 'Дата создания',
            'author': 'Имя автора',
            'group': 'Группа'
        }
        post_field_help = {
            'text': 'Введите текст поста',
            'group': 'Группа, к которой будет относиться пост'
        }
        for field, expected_value in post_field_verboses.items():
            with self.subTest(field=field):
                self.assertEqual(
                    Post._meta.get_field(field).verbose_name, expected_value)
        for field, expected_value in post_field_help.items():
            with self.subTest(field=field):
                self.assertEqual(
                    Post._meta.get_field(field).help_text, expected_value)

    def test_model_group_have_correct_object_names(self):
        """Проверяем, что у модели Group корректно работает __str__."""
        group_field_verboses = {
            'title': 'Название группы',
            'slug': 'Группа',
            'description': 'Описание группы',
        }
        for field, expected_value in group_field_verboses.items():
            with self.subTest(field=field):
                self.assertEqual(
                    Group._meta.get_field(field).verbose_name, expected_value)
