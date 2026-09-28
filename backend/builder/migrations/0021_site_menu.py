from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("builder", "0020_blog_generation"),
    ]

    operations = [
        migrations.AddField(
            model_name="site",
            name="menu",
            field=models.JSONField(
                blank=True, null=True,
                help_text="Customised top menu (services/site_menu.py); empty = the template's own.",
            ),
        ),
        migrations.AddField(
            model_name="site",
            name="draft_menu",
            field=models.JSONField(
                blank=True, null=True,
                help_text='Unpublished editor change to menu; "default" means back to the template\'s menu.',
            ),
        ),
    ]
