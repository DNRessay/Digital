Title: Project: Templify, from HTML template to Django app
Date: 2026-09-28 10:04
Category: Projects
Tags: templify, django, python, developer tools
Slug: project-templify
Summary: Templify turns a static multi-page HTML template into a working Django app. It's how new templates reach the Vicinic editor.
Authors: Vicinic

![Templify: HTML template to Django app]({static}/images/projects/templify.webp)

There are thousands of beautiful HTML templates available, but they're just static files. To use one on a real platform you have to split out the shared header and footer, fix every asset link and rewire every page link by hand. Templify does that automatically.

## What it does

- **Finds the shared layout.** It compares every page in the template, pulls the repeated header, navigation and footer into one `base.html`, and gives each page only its own content.
- **Fixes asset links.** CSS, JavaScript, images and fonts are rewritten to Django `{% static %}` tags and copied into the app.
- **Rewires page links.** Links like `about.html` become proper `{% url %}` links, and the menu's "active" state becomes dynamic.
- **Converts contact forms.** Forms that posted to a PHP script get a matching Django view, so they work out of the box.

It isn't hard-coded to one template; it works on any multi-page template that follows the usual header, content and footer pattern.

## Where it runs

Templify is a Python command-line tool with its own tests. It's also available as a web app where you upload a template zip and get a Django app back, running on AWS Lambda with S3. Inside Vicinic it's how new templates get added to the editor's library.
