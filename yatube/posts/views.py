from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from .forms import CommentForm, PostForm
from .models import Follow, Group, Post, User
from .utils import pagination


def index(request):
    context = {
        'page_obj': pagination(request, Post.objects.all())
    }
    return render(request, 'posts/index.html', context)


def group_posts(request, slug):
    group = get_object_or_404(Group, slug=slug)
    context = {
        'group': group,
        'page_obj': pagination(request, Post.objects.filter(group=group))
    }
    return render(request, 'posts/group_list.html', context)


def profile(request, username):
    author = get_object_or_404(User, username=username)
    following = (request.user.is_authenticated) and (Follow.objects.filter(
        user__username=request.user, author=author).exists())
    context = {
        'page_obj': pagination(request, author.posts.all()),
        'author': author,
        'following': following
    }
    return render(request, 'posts/profile.html', context)


def post_detail(request, post_id):
    post = get_object_or_404(Post, pk=post_id)
    form = CommentForm(request.POST or None)
    comments = post.comments.all
    context = {
        'post': post,
        'form': form,
        'comments': comments
    }
    return render(request, 'posts/post_detail.html', context)


@login_required
def post_create(request):
    form = PostForm(request.POST or None,
                    files=request.FILES or None)
    if form.is_valid():
        post = form.save(commit=False)
        post.author = request.user
        post.save()
        return redirect('posts:profile', username=request.user)
    form = PostForm()
    context = {
        'form': form
    }
    return render(request, 'posts/create_post.html', context)


@login_required
def post_edit(request, post_id):
    post = get_object_or_404(Post, pk=post_id)
    if post.author != request.user:
        return redirect('posts:post_detail', post_id=post.id)
    form = PostForm(request.POST or None,
                    files=request.FILES or None,
                    instance=post)
    if form.is_valid():
        post = form.save(commit=False)
        post.author = request.user
        post.save()
        return redirect('posts:post_detail', post_id=post.id)
    form = PostForm()
    context = {
        'form': form,
        'is_edit': True
    }
    return render(request, 'posts/create_post.html', context)


@login_required
def add_comment(request, post_id):
    post = get_object_or_404(Post, pk=post_id)
    form = CommentForm(request.POST or None)
    if form.is_valid():
        comment = form.save(commit=False)
        comment.author = request.user
        comment.post = post
        comment.save()
    return redirect('posts:post_detail', post_id=post_id)


@login_required
def follow_index(request):
    follower = request.user
    context = {
        'page_obj': pagination(request, Post.objects.filter(
            author__following__user=follower)),
        'follower': follower
    }
    return render(request, 'posts/follow.html', context)


@login_required
def profile_follow(request, username):
    follower = request.user
    author = User.objects.get(username=username)
    if follower != author:
        Follow.objects.get_or_create(
            user=follower, author=author)
    context = {
        'page_obj': pagination(request, Post.objects.filter(author=author)),
        'author': author
    }
    return render(request, 'posts/profile.html', context)


@login_required
def profile_unfollow(request, username):
    follower = request.user
    author = User.objects.get(username=username)
    Follow.objects.filter(
        user=follower, author=author).delete()
    context = {
        'page_obj': pagination(request, Post.objects.filter(author=author)),
        'author': author
    }
    return render(request, 'posts/profile.html', context)
