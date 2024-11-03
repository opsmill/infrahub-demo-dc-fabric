import re
import pytest
from playwright.sync_api import Page, expect, BrowserContext

@pytest.fixture
def admin_login(context: BrowserContext):
    page = context.new_page()
    page.goto('http://localhost:8000/login')
    expect(page.get_by_text("Log in to your account")).to_be_visible()
    page.get_by_label("Username").fill("admin")
    page.get_by_label("Password").fill("infrahub")
    page.get_by_role("button", name="Log in").click()
    expect(page.get_by_text("Proposed changes")).to_be_visible()

    return page

def test_homepage(page: Page):
    page.goto("http://localhost:8000/")
    expect(page.get_by_text("Proposed changes")).to_be_visible()
    page.screenshot(path="infrahub_homepage.png")

def test_add_repository(admin_login, context: BrowserContext):

    page = context.new_page()
    page.goto('http://localhost:8000/objects/CoreGenericRepository')
    expect(page.get_by_text("Add Git Repository")).to_be_visible()
    page.get_by_test_id("create-object-button").click()
    expect(page.get_by_text("Create Git Repository")).to_be_visible()
    page.get_by_label("Select an object type").click()
    page.get_by_role(role="option", name="Read-Only Repository").click()
    expect(page.get_by_text("Repository location")).to_be_visible()
    page.get_by_label("Repository location").fill("https://github.com/opsmill/infrahub-demo-dc-fabric.git")
    page.get_by_label("Name").fill("infrahub-demo-dc-fabric")
    page.screenshot(path="infrahub_repository_form.png")

    page.get_by_role("button", name="Save").click()
    expect(page.get_by_text("infrahub-demo-dc-fabric")).to_be_visible()
    page.screenshot(path="infrahub_repository_list.png")