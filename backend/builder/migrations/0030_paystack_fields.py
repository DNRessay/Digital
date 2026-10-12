from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("builder", "0029_mcp_keys")]

    operations = [
        migrations.AddField(
            model_name="site",
            name="paystack_customer_code",
            field=models.CharField(blank=True, max_length=100),
        ),
        migrations.AddField(
            model_name="site",
            name="paystack_subscription_code",
            field=models.CharField(blank=True, max_length=100),
        ),
    ]
