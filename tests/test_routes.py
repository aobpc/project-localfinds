import pytest
from src.localfinds.app import app, accounts, posts
from werkzeug.security import generate_password_hash, check_password_hash
from src.localfinds.models.accounts import (
    clear_accounts,
    store_account,
    get_all_accounts,
    update_account,
    delete_account,
)
from src.localfinds.models.posts import (
    clear_posts,
    store_post,
    get_all_posts,
    update_post,
    delete_post,
)
import time


@pytest.fixture
def client():
    app.config["TESTING"] = True
    app.config["WTF_CSRF_ENABLED"] = False
    with app.test_client() as client:
        # Clear databases before each test
        clear_accounts(accounts)
        clear_posts(posts)
        # Setup default account and post
        store_account(accounts, "admin", generate_password_hash("password"))
        store_post(
            posts, "Test Post", "Test content", "admin", "123 Main St", "tag1, tag2"
        )
        yield client


def login(client, username, password):
    return client.post(
        "/auth/login",
        data=dict(username=username, password=password),
        follow_redirects=True,
    )


def test_create_post_authorized(client):
    login(client, "admin", "password")
    time.sleep(1)
    response = client.post(
        "/posts/create",
        data={
            "subject": "New Post",
            "content": "Content here",
            "address": "456 Road St",
            "tags": "test",
        },
        follow_redirects=True,
    )
    assert b"New Post" in response.data
    assert get_all_posts(posts)[0]["subject"] == "New Post"
    assert get_all_posts(posts)[0]["content"] == "Content here"
    assert get_all_posts(posts)[0]["address"] == "456 Road St"
    assert get_all_posts(posts)[0]["tags"] == "test"
    assert len(get_all_posts(posts)) == 2


def test_create_post_unauthorized(client):
    response = client.post(
        "/posts/create",
        data={
            "subject": "New Post",
            "content": "Content here",
            "address": "456 Road St",
            "tags": "test",
        },
        follow_redirects=True,
    )
    assert response.status_code == 403
    assert len(get_all_posts(posts)) == 1


def test_home_page(client):
    response = client.get("/")
    assert response.status_code == 200
    assert b"Test Post" in response.data


def test_view_post(client):
    all_posts = get_all_posts(posts)
    post_id = all_posts[0]["id"]
    response = client.get(f"/posts/{post_id}")
    assert response.status_code == 200
    assert b"Test Post" in response.data


def test_search_posts(client):
    time.sleep(1)
    store_post(posts, "Another Post", "Different content", "admin", "456 Ave", "misc")

    response = client.post(
        "/posts/search", data={"search": "Another"}, follow_redirects=True
    )

    assert response.status_code == 200
    assert b"Another Post" in response.data
    assert b"Test Post" not in response.data


def test_search_posts_multiple_fields(client):
    response = client.post(
        "/posts/search", data={"search": "tag1"}, follow_redirects=True
    )
    assert b"Test Post" in response.data

    response = client.post(
        "/posts/search", data={"search": "123 Main"}, follow_redirects=True
    )
    assert b"Test Post" in response.data

    response = client.post(
        "/posts/search", data={"search": "admin"}, follow_redirects=True
    )
    assert b"Test Post" in response.data

    response = client.post(
        "/posts/search", data={"search": "content"}, follow_redirects=True
    )
    assert b"Test Post" in response.data


def test_search_posts_no_results(client):
    response = client.post(
        "/posts/search", data={"search": "nonexistent"}, follow_redirects=True
    )

    assert response.status_code == 200
    assert b"Test Post" not in response.data


def test_edit_post_unauthorized(client):
    all_posts = get_all_posts(posts)
    post_id = all_posts[0]["id"]

    response = client.get(f"/posts/{post_id}/edit")
    assert response.status_code == 403
    assert get_all_posts(posts)[0]["subject"] == "Test Post"
    assert get_all_posts(posts)[0]["content"] == "Test content"
    assert get_all_posts(posts)[0]["address"] == "123 Main St"
    assert get_all_posts(posts)[0]["tags"] == "tag1, tag2"
    assert len(get_all_posts(posts)) == 1


def test_edit_post_authorized(client):
    login(client, "admin", "password")
    all_posts = get_all_posts(posts)
    post_id = all_posts[0]["id"]

    response = client.post(
        f"/posts/{post_id}/edit",
        data={
            "subject": "Edited Post",
            "content": "Edited content",
            "address": "123 Main St",
            "tags": "welcome, intro",
        },
        follow_redirects=True,
    )

    assert b"Edited Post" in response.data
    assert get_all_posts(posts)[0]["subject"] == "Edited Post"
    assert get_all_posts(posts)[0]["content"] == "Edited content"
    assert get_all_posts(posts)[0]["address"] == "123 Main St"
    assert get_all_posts(posts)[0]["tags"] == "welcome, intro"
    assert len(get_all_posts(posts)) == 1


def test_remove_post_unauthorized(client):
    all_posts = get_all_posts(posts)
    post_id = all_posts[0]["id"]

    response = client.get(f"/posts/{post_id}/delete")
    assert response.status_code == 403
    assert len(get_all_posts(posts)) == 1


def test_remove_post_authorized(client):
    login(client, "admin", "password")

    all_posts = get_all_posts(posts)
    post_id = all_posts[0]["id"]

    response = client.get(f"/posts/{post_id}/delete", follow_redirects=True)
    assert b"Test Post" not in response.data
    assert len(get_all_posts(posts)) == 0


def test_create_account(client):
    response = client.post(
        "/accounts/create",
        data={"username": "alice", "password": "pass"},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"alice" in response.data
    assert len(get_all_accounts(accounts)) == 2
    assert get_all_accounts(accounts)[1]["username"] == "alice"


def test_create_account_duplicate_username(client):
    response = client.post(
        "/accounts/create",
        data={"username": "admin", "password": "pass"},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Username is taken!" in response.data
    assert len(get_all_accounts(accounts)) == 1


def test_create_account_username_too_long(client):
    response = client.post(
        "/accounts/create",
        data={"username": "thisusernameiswaytoolong", "password": "pass"},
        follow_redirects=True,
    )

    assert b"Username must not exceed 15 characters" in response.data
    assert len(get_all_accounts(accounts)) == 1


def test_view_account(client):
    response = client.get("/accounts/admin")
    assert response.status_code == 200
    assert b"admin" in response.data


def test_edit_account_unauthorized(client):
    time.sleep(1)
    store_account(accounts, "user", generate_password_hash("password"))
    response = client.get("/accounts/user/edit")
    assert response.status_code == 403
    assert get_all_accounts(accounts)[1]["username"] == "user"


def test_edit_account_admin(client):
    login(client, "admin", "password")
    response = client.post(
        "/accounts/admin/edit",
        data={"username": "admin2", "password": "newpass"},
        follow_redirects=True,
    )
    assert response.status_code == 403
    assert b"admin" in response.data
    assert get_all_accounts(accounts)[0]["username"] == "admin"
    assert get_all_posts(posts)[0]["author_id"] == "admin"


def test_edit_account_authorized(client):
    time.sleep(1)
    store_account(accounts, "user", generate_password_hash("password"))
    time.sleep(1)
    store_post(posts, "Test Post", "Test content", "user", "123 Main St", "tag1, tag2")
    login(client, "user", "password")
    response = client.post(
        "/accounts/user/edit",
        data={"username": "user2", "password": "newpass"},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"user2" in response.data
    assert get_all_accounts(accounts)[1]["username"] == "user2"
    assert check_password_hash(get_all_accounts(accounts)[1]["password"], "newpass")
    assert get_all_posts(posts)[0]["author_id"] == "user2"


def test_edit_account_authorized_add_bio(client):
    time.sleep(1)
    store_account(accounts, "user", generate_password_hash("password"))
    login(client, "user", "password")
    response = client.post(
        "/accounts/user/edit",
        data={"username": "user", "password": "password", "bio": "I love places."},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"I love places." in response.data
    assert get_all_accounts(accounts)[1]["username"] == "user"


def test_edit_account_duplicate_username(client):
    time.sleep(1)
    store_account(accounts, "alice", generate_password_hash("pass"))
    login(client, "alice", "pass")
    response = client.post(
        "/accounts/alice/edit",
        data={"username": "admin", "password": "newpass"},
        follow_redirects=True,
    )
    assert response.status_code == 400
    assert b"Username already taken" in response.data
    assert get_all_accounts(accounts)[1]["username"] == "alice"


def test_edit_account_username_too_long(client):
    time.sleep(1)
    store_account(accounts, "user", generate_password_hash("password"))
    login(client, "user", "password")
    response = client.post(
        "/accounts/user/edit",
        data={"username": "thisusernameiswaytoolong", "password": "newpass"},
        follow_redirects=True,
    )
    assert b"Username must not exceed 15 characters" in response.data
    assert get_all_accounts(accounts)[1]["username"] == "user"


def test_delete_account_unauthorized(client):
    time.sleep(1)
    store_account(accounts, "user", generate_password_hash("password"))
    response = client.get("/accounts/user/delete")
    assert response.status_code == 403
    assert len(get_all_accounts(accounts)) == 2


def test_delete_account_admin(client):
    login(client, "admin", "password")

    all_posts = get_all_posts(posts)
    post_id = all_posts[0]["id"]

    response = client.get(f"/posts/{post_id}/delete", follow_redirects=True)

    response = client.post("/accounts/admin/delete", follow_redirects=True)
    assert response.status_code == 403
    assert b"admin" in response.data
    assert len(get_all_accounts(accounts)) == 1


def test_delete_account_authorized(client):
    time.sleep(1)
    store_account(accounts, "user", generate_password_hash("password"))
    time.sleep(1)
    store_post(
        posts, "Test Post 2", "Test content", "user", "123 Main St", "tag1, tag2"
    )
    login(client, "user", "password")

    response = client.post("/accounts/user/delete", follow_redirects=True)
    assert response.status_code == 200
    assert b"user" not in response.data
    assert len(get_all_accounts(accounts)) == 1
    assert len(get_all_posts(posts)) == 1


def test_login(client):
    response = login(client, "admin", "password")
    assert response.status_code == 200
    with client.session_transaction() as sess:
        assert sess["username"] == "admin"


def test_logout(client):
    response = client.get("/auth/logout", follow_redirects=True)
    with client.session_transaction() as sess:
        assert "username" not in sess
