# Generated by Django 5.1.5 on 2025-02-26 01:22

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('pos', '0006_rename_date_stockmovement_timestamp_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='Expense',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=255)),
                ('amount', models.DecimalField(decimal_places=2, max_digits=10)),
                ('category', models.CharField(choices=[('rent', 'Rent'), ('water', 'Water'), ('salary', 'Salary'), ('other', 'Other')], default='other', max_length=50)),
                ('date', models.DateField(auto_now_add=True)),
            ],
        ),
    ]
