import shutil
import tempfile
from http import HTTPStatus

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from ..models import Comment, Group, Post


TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)

User = get_user_model()


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostFormTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='SomeUser')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-group-slug',
            description='Тестовое описание',
        )

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.authorized_client = Client()
        self.authorized_client.force_login(PostFormTest.user)
        self.post = Post.objects.create(author=PostFormTest.user,
                                        text='Некий текст')
        self.post_count = Post.objects.count()

    def test_guest_cannot_create_post(self):
        """Неавторизованный юзер не может создать запись"""
        form_data = {
            'text': 'Попытка написать текст',
            'group': PostFormTest.group.id
        }
        response = Client().post(
            reverse('posts:post_create'),
            data=form_data,
            follow=True
        )
        expected_redirect = (reverse('users:login')
                             + '?next='
                             + reverse('posts:post_create'))
        self.assertRedirects(response, expected_redirect)
        self.assertFalse(
            Post.objects.filter(
                text='Попытка написать текст',
                group=PostFormTest.group.id
            ).exists()
        )
        self.assertEqual(Post.objects.count(), self.post_count)

    def test_post_create_form(self):
        """Валидная форма создает запись"""
        small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )
        uploaded = SimpleUploadedFile(
            name='small.gif',
            content=small_gif,
            content_type='image/gif'
        )
        form_data = {
            'text': 'Новый тестовый текст',
            'group': PostFormTest.group.id,
            'image': uploaded
        }
        response = self.authorized_client.post(
            reverse('posts:post_create'),
            data=form_data,
            follow=True
        )
        expected_redirect = reverse('posts:profile', kwargs={
            'username': 'SomeUser'})
        new_post = Post.objects.first()
        self.assertEqual(new_post.text, 'Новый тестовый текст')
        self.assertEqual(new_post.group.title, 'Тестовая группа')
        self.assertRedirects(response, expected_redirect)
        self.assertEqual(Post.objects.count(), self.post_count + 1)
        self.assertTrue(
            Post.objects.filter(
                text='Новый тестовый текст',
                group=PostFormTest.group.id,
                image=new_post.image
            ).exists()
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_post_edit_form(self):
        """Валидная форма редактирует запись"""
        form_data = {
            'text': 'Изменённый текст',
            'group': PostFormTest.group.id
        }
        response = self.authorized_client.post(
            reverse('posts:post_edit', kwargs={
                'post_id': self.post.id}),
            data=form_data,
            follow=True
        )
        changed_post = Post.objects.first()
        expected_redirect = reverse('posts:post_detail', kwargs={
            'post_id': '1'})
        self.assertEqual(changed_post.text, 'Изменённый текст')
        self.assertRedirects(response, expected_redirect)
        self.assertEqual(Post.objects.count(), self.post_count)
        self.assertTrue(
            Post.objects.filter(
                text='Изменённый текст',
                group=PostFormTest.group.id
            ).exists()
        )

    def test_add_comment_form(self):
        """Проверка добавления комментариев разными пользователями"""
        form_data = {
            'text': 'Текст комментария',
            'author': PostFormTest.user,
            'post': self.post
        }
        Client().post(
            reverse('posts:add_comment', args={self.post.id}),
            data=form_data,
            follow=True
        )
        self.assertEqual(self.post.comments.count(), 0)
        self.assertFalse(
            Comment.objects.filter(
                text='Текст комментария',
                author=PostFormTest.user,
                post=self.post
            ).exists())
        self.authorized_client.post(
            reverse('posts:add_comment', args={self.post.id}),
            data=form_data,
            follow=True
        )
        self.assertEqual(self.post.comments.count(), 1)
        self.assertTrue(
            Comment.objects.filter(
                text='Текст комментария',
                author=PostFormTest.user,
                post=self.post
            ).exists())
