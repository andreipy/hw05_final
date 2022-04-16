import shutil
import tempfile

from django import forms
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from ..models import Follow, Group, Post

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)

User = get_user_model()


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostViewTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )
        cls.uploaded = SimpleUploadedFile(
            name='small.gif',
            content=cls.small_gif,
            content_type='image/gif'
        )
        cls.user = User.objects.create_user(username='SomeUser',
                                            first_name='Имя',
                                            last_name='Фамилия')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-group-slug',
            description='Тестовое описание',
        )
        for cls.post in range(1, 14):
            cls.post = Post.objects.create(
                group=cls.group,
                text='Тестовый текст',
                author=cls.user,
                image=cls.uploaded
            )

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.guest_client = Client()
        self.user = User.objects.create_user(username='TestUser')
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)
        self.author_client = Client()
        self.author_client.force_login(PostViewTest.user)
        self.pages_with_paginator = [
            reverse('posts:index'),
            reverse('posts:group_list', kwargs=(
                {'slug': 'test-group-slug'})),
            reverse('posts:profile', kwargs=(
                {'username': 'SomeUser'}))
        ]
        self.form_fields = {
            'text': forms.fields.CharField,
            'group': forms.fields.ChoiceField,
        }

    def test_pages_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        templates_pages_names = {
            reverse('posts:index'): 'posts/index.html',
            reverse('posts:group_list', kwargs=(
                {'slug': 'test-group-slug'})): 'posts/group_list.html',
            reverse('posts:profile', kwargs=(
                {'username': 'SomeUser'})): 'posts/profile.html',
            reverse('posts:post_detail', kwargs=(
                    {'post_id': '1'})): 'posts/post_detail.html',
            reverse('posts:post_create'): 'posts/create_post.html',
            reverse('posts:post_edit', kwargs=(
                {'post_id': '1'})): 'posts/create_post.html'
        }
        for reverse_name, template in templates_pages_names.items():
            with self.subTest(reverse_name=reverse_name):
                response = self.author_client.get(reverse_name)
                self.assertTemplateUsed(response, template)

    def test_paginator_first_pages(self):
        """Проверка первой страницы шаблонов с пагинатором."""
        for page in self.pages_with_paginator:
            with self.subTest(page=page):
                response = self.author_client.get(page)
                self.assertEqual(len(response.context['page_obj']), 10)

    def test_paginator_second_pages(self):
        """Проверка второй страницы шаблонов с пагинатором."""
        for page in self.pages_with_paginator:
            with self.subTest(page=page):
                response = self.author_client.get(page + '?page=2')
                self.assertEqual(len(response.context['page_obj']), 3)

    def test_checking_group(self):
        """Проверка, что в шаблоне group_list посты с нужной группой."""
        another_group = Group.objects.create(
            title='Другая Тестовая группа',
            slug='test-group-slug-2'
        )
        response = self.author_client.get(self.pages_with_paginator[1])
        for post in response.context.get('page_obj').object_list:
            with self.subTest():
                self.assertIsInstance(post, Post)
                self.assertEqual(post.group, PostViewTest.group)
                self.assertNotEqual(post.group, another_group)

    def test_index_page_show_correct_context(self):
        """Шаблон index сформирован с правильным контекстом."""
        response = self.author_client.get(reverse('posts:index'))
        first_post = response.context['page_obj'][0]
        self.assertIsInstance(first_post, Post)
        self.assertTrue(first_post.image)

    def test_group_list_show_correct_context(self):
        """Шаблон group_list сформирован с правильным контекстом."""
        response = self.author_client.get(
            reverse('posts:group_list', kwargs={
                'slug': 'test-group-slug'}))
        first_post = response.context['page_obj'][0]
        test_group = response.context['group']
        self.assertIsInstance(first_post, Post)
        self.assertIsInstance(test_group, Group)
        self.assertTrue(first_post.image)

    def test_profile_show_correct_context(self):
        """Шаблон profile сформирован с правильным контекстом."""
        response = self.author_client.get(
            reverse('posts:profile', kwargs={
                'username': 'SomeUser'}))
        first_post = response.context['page_obj'][0]
        post_count = Post.objects.filter(
            author=response.context['author']).count()
        self.assertIsInstance(first_post, Post)
        self.assertEqual(post_count, 13)
        self.assertTrue(first_post.image)

    def test_post_detail_show_correct_context(self):
        """Шаблон post_detail сформирован с правильным контекстом."""
        response = self.author_client.get(
            reverse('posts:post_detail', kwargs={
                'post_id': '1'}))
        post = response.context['post']
        self.assertIsInstance(post, Post)
        self.assertTrue(post.image)

    def test_create_post_show_correct_context(self):
        """Шаблон create_post сформирован с правильным контекстом."""
        response = self.author_client.get(reverse('posts:post_create'))
        for value, expected in self.form_fields.items():
            with self.subTest(value=value):
                form_field = response.context.get('form').fields.get(value)
                self.assertIsInstance(form_field, expected)

    def test_post_edit_show_correct_context(self):
        """Шаблон create_post (is_edit == True)
        сформирован с правильным контекстом."""
        response = self.author_client.get(reverse('posts:post_edit', kwargs=(
            {'post_id': '1'})))
        if self.assertTrue(response.context['is_edit']):
            for value, expected in self.form_fields.items():
                with self.subTest(value=value):
                    form_field = response.context.get('form').fields.get(value)
                    self.assertIsInstance(form_field, expected)

    def test_cached_index(self):
        """Проверка работы кэша"""
        old_response = self.authorized_client.get(
            reverse('posts:index')
        )
        first_count = len(old_response.context['page_obj'])
        for post in range(1, 9):
            Post.objects.get(pk=post).delete()
        second_count = len(old_response.context['page_obj'])
        self.assertEqual(first_count, second_count)
        cache.clear()
        new_response = self.authorized_client.get(
            reverse('posts:index')
        )
        self.assertNotEqual(old_response, new_response)

    def test_following_for_authorized(self):
        """Авторизованный юзер может подписываться"""
        self.authorized_client.get(reverse('posts:profile_follow', kwargs={
            'username': 'SomeUser'}))
        self.assertTrue(
            Follow.objects.filter(user=self.user,
                                  author=PostViewTest.user).exists())

    def test_unfollowing_for_authorized(self):
        """Авторизованный юзер может отписываться"""
        self.authorized_client.get(reverse('posts:profile_unfollow', kwargs={
            'username': 'SomeUser'}))
        self.assertFalse(
            Follow.objects.filter(user=self.user,
                                  author=PostViewTest.user).exists())

    def test_author_posts_for_follow_feed(self):
        """Записи появляются в follow подписчиков; у неподписанных - нет"""
        Follow.objects.create(
            user=self.user, author=PostViewTest.user
        )
        response = self.authorized_client.get(reverse('posts:follow_index'))
        first_post_on_follow = response.context['page_obj'][0]
        self.assertEqual(first_post_on_follow.author, PostViewTest.user)
        not_follower = User.objects.create_user(username='NoFollow')
        not_follower_client = Client()
        not_follower_client.force_login(not_follower)
        response = not_follower_client.get(reverse('posts:follow_index'))
        self.assertEqual(len(response.context['page_obj']), 0)
