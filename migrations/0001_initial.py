# Generated by Django 3.2.11 on 2022-08-18 22:25

from django.db import migrations, models
import django_payments.models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Customer',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('merchant_id', models.IntegerField(default=0)),
                ('unique_id', models.IntegerField()),
                ('customer_info', models.JSONField(default=dict)),
                ('flag', models.IntegerField(default=0)),
                ('flag2', models.IntegerField(default=0)),
            ],
            bases=(models.Model, django_payments.models.Bitmap),
        ),
        migrations.CreateModel(
            name='Merchant',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('unique_id', models.IntegerField()),
                ('provider', models.CharField(max_length=1000)),
                ('merchant_info', models.JSONField(default=dict)),
                ('flag', models.IntegerField(default=0)),
                ('flag2', models.IntegerField(default=0)),
            ],
            bases=(models.Model, django_payments.models.Bitmap),
        ),
        migrations.CreateModel(
            name='PaymentMethod',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('merchant_id', models.IntegerField(default=0)),
                ('unique_id', models.IntegerField()),
                ('payment_method_info', models.JSONField(default=dict)),
                ('flag', models.IntegerField(default=0)),
                ('flag2', models.IntegerField(default=0)),
            ],
            bases=(models.Model, django_payments.models.Bitmap),
        ),
    ]
